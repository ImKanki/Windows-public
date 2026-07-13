# -*- coding: utf-8 -*-
"""网格主窗口：嵌套分隔条容器，支持主分割方向切换、内层增量/复位联动、吸附折叠、隐藏栏、会话记忆。"""
import copy
import ctypes

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import fixwindows
import icons
import session
import win32_utils
from config import DEFAULT_CFG, color, font_size, icon_size
from drag_watcher import DragWatcher
from embed_cell import EmbedCell
from settings_dialog import SettingsDialog
from split_widget import SnapSplitter
from window_picker import WindowPicker

GRID_PRESETS = {
    "1 x 2": (1, 2),
    "2 x 2 (4)": (2, 2),
    "2 x 3 (6)": (2, 3),
    "3 x 3 (9)": (3, 3),
    "3 x 4 (12)": (3, 4),
    "4 x 4 (16)": (4, 4),
}
CUSTOM_LABEL = "自定义"
MAX_RC = 6


class GridWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = copy.deepcopy(DEFAULT_CFG)
        self.cells = []
        self.rows = 0
        self.cols = 0
        self.root_split = None
        self._splitters = []
        self._inner = []
        self._inner_last = {}
        self._sync_guard = False
        self._toolbar_hidden = True

        self.setWindowTitle(self.cfg["window_title"])
        self.resize(self.cfg["win_w"], self.cfg["win_h"])

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_toolbar())

        self.grid_container = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.grid_container, 1)

        start = self.cfg["default_grid"]
        if start not in GRID_PRESETS and start != CUSTOM_LABEL:
            start = "2 x 2 (4)"
        self.combo.blockSignals(True)
        self.combo.setCurrentText(start)
        self.combo.blockSignals(False)
        self.on_preset_changed(start)

        self.watcher = DragWatcher(self)
        self.watcher.hover.connect(self._on_drag_hover)
        self.watcher.drop.connect(self._on_drag_drop)
        self.watcher.timer.setInterval(self.cfg["watcher_interval"])
        self.watcher.start()

        self.enforce_timer = QTimer(self)
        self.enforce_timer.setInterval(self.cfg["enforce_interval"])
        self.enforce_timer.timeout.connect(self._enforce_all)
        self.enforce_timer.start()

        self.toolbar.setVisible(False)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("toggleBar")
        self.toggle_btn.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.toggle_btn.setFixedSize(48, 22)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_toolbar)
        self.toggle_btn.hide()
        self._update_toggle_icon()

        self.reveal_timer = QTimer(self)
        self.reveal_timer.setInterval(150)
        self.reveal_timer.timeout.connect(self._check_reveal)
        self.reveal_timer.start()

        self.save_timer = QTimer(self)
        self.save_timer.setInterval(3000)
        self.save_timer.timeout.connect(self._save_session)
        self.save_timer.start()

        self._dark_titlebar()
        win32_utils.register_own_hwnd(int(self.winId()))

        QTimer.singleShot(600, self.restore_session)

    def _dark_titlebar(self):
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass

    # ---- 可交互状态判断 ----
    def _visible_usable(self):
        """窗口可见且未最小化（不要求是激活窗口）。用于拖拽吸附门控。"""
        if not self.isVisible():
            return False
        if self.windowState() & Qt.WindowState.WindowMinimized:
            return False
        return True

    def _interactive(self):
        """更严格：可见、未最小化、且是当前激活窗口。用于浮出箭头。"""
        return self._visible_usable() and self.isActiveWindow()

    # ---- 工具栏 ----
    def _vsep(self):
        sep = QFrame()
        sep.setObjectName("tbSep")
        sep.setFixedWidth(1)
        sep.setFixedHeight(22)
        return sep

    def _build_toolbar(self):
        bar = QWidget()
        bar.setObjectName("toolbar")
        self.toolbar = bar
        self._seps = []

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 16, 8)
        layout.setSpacing(10)

        self.logo = QWidget()
        self.logo.setObjectName("logoBadge")
        logo_lay = QHBoxLayout(self.logo)
        logo_lay.setContentsMargins(10, 5, 12, 5)
        logo_lay.setSpacing(8)

        self.tb_app_icon = QLabel()
        self.tb_app_icon.setObjectName("logoIcon")
        logo_lay.addWidget(self.tb_app_icon)

        self.tb_title = QLabel("窗口网格")
        self.tb_title.setObjectName("logoText")
        logo_lay.addWidget(self.tb_title)

        layout.addWidget(self.logo)

        layout.addSpacing(4)
        sep1 = self._vsep()
        self._seps.append(sep1)
        layout.addWidget(sep1)

        self.tb_grid_label = QLabel("网格布局")
        self.tb_grid_label.setObjectName("fieldLabel")
        layout.addWidget(self.tb_grid_label)

        self.combo = QComboBox()
        self.combo.addItems(list(GRID_PRESETS.keys()) + [CUSTOM_LABEL])
        self.combo.currentTextChanged.connect(self.on_preset_changed)
        layout.addWidget(self.combo)

        self.custom_widget = QWidget()
        cw = QHBoxLayout(self.custom_widget)
        cw.setContentsMargins(0, 0, 0, 0)
        cw.setSpacing(6)
        lbl_r = QLabel("行")
        lbl_r.setObjectName("fieldLabel")
        cw.addWidget(lbl_r)
        self.row_spin = QSpinBox()
        self.row_spin.setRange(1, MAX_RC)
        self.row_spin.setValue(self.cfg.get("custom_rows", 2))
        cw.addWidget(self.row_spin)
        lbl_c = QLabel("列")
        lbl_c.setObjectName("fieldLabel")
        cw.addWidget(lbl_c)
        self.col_spin = QSpinBox()
        self.col_spin.setRange(1, MAX_RC)
        self.col_spin.setValue(self.cfg.get("custom_cols", 3))
        cw.addWidget(self.col_spin)
        self.row_spin.valueChanged.connect(self._on_custom_changed)
        self.col_spin.valueChanged.connect(self._on_custom_changed)
        self.custom_widget.setVisible(False)
        layout.addWidget(self.custom_widget)

        layout.addSpacing(4)
        sep2 = self._vsep()
        self._seps.append(sep2)
        layout.addWidget(sep2)
        layout.addSpacing(4)

        self.btn_fill = QPushButton("  嵌入窗口")
        self.btn_fill.setObjectName("primary")
        self.btn_fill.clicked.connect(self.pick_and_fill)
        layout.addWidget(self.btn_fill)

        self.btn_scan = QPushButton("  扫描填充")
        self.btn_scan.clicked.connect(self.scan_and_attach)
        layout.addWidget(self.btn_scan)

        self.btn_settings = QPushButton("  设置")
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        layout.addStretch(1)

        self.tb_hint = QLabel(
            "拖窗口标题栏入槽　·　双击空槽选择窗口　·　右键标题栏可弹出　·"
            "　拖分隔条到边吸附折叠"
        )
        self.tb_hint.setObjectName("hintLabel")
        layout.addWidget(self.tb_hint)

        self._apply_toolbar_config()
        return bar

    def _apply_toolbar_config(self):
        self.toolbar.setFixedHeight(self.cfg["toolbar_height"])

        af = font_size(self.cfg, "app_title")
        bf = font_size(self.cfg, "button")
        hf = font_size(self.cfg, "hint")

        tb_bg = color(self.cfg, "toolbar_bg", "#16213e")
        tb_border = color(self.cfg, "toolbar_border", "#243056")
        self.toolbar.setStyleSheet(
            f"QWidget#toolbar {{ background:{tb_bg};"
            f" border:1px solid {tb_border}; border-radius:10px; }}"
        )

        for sep in self._seps:
            sep.setStyleSheet(f"background:{tb_border};")

        grad_a = color(self.cfg, "logo_grad_start", "#1f6f5c")
        grad_b = color(self.cfg, "logo_grad_end", "#2a8a72")
        logo_text = color(self.cfg, "logo_text", "#ffffff")
        self.logo.setStyleSheet(
            "QWidget#logoBadge {"
            f" background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f" stop:0 {grad_a}, stop:1 {grad_b});"
            " border-radius:8px; }"
            " QLabel#logoIcon { background:transparent; }"
            f" QLabel#logoText {{ background:transparent; color:{logo_text};"
            f" font-size:{af}px; font-weight:bold; }}"
        )
        self.tb_grid_label.setStyleSheet(
            f"QLabel#fieldLabel {{ color:#8a93b8; font-size:{bf}px;"
            " background:transparent; }"
        )
        self.tb_hint.setStyleSheet(
            f"QLabel#hintLabel {{ color:#5a6488; font-size:{hf}px;"
            " background:transparent; }"
        )

        btn_bg = color(self.cfg, "btn_bg", "#2a3a6a")
        btn_hover = color(self.cfg, "btn_hover", "#34457e")
        pri_bg = color(self.cfg, "btn_primary", "#1f6f5c")
        pri_hover = color(self.cfg, "btn_primary_hover", "#2a8a72")
        normal_qss = (
            f"QPushButton {{ background:{btn_bg}; color:#e8e8e8; border:none;"
            f" padding:7px 14px; border-radius:5px; font-size:{bf}px; }}"
            f"QPushButton:hover {{ background:{btn_hover}; }}"
        )
        primary_qss = (
            f"QPushButton {{ background:{pri_bg}; color:#ffffff; border:none;"
            f" padding:7px 14px; border-radius:5px; font-size:{bf}px; }}"
            f"QPushButton:hover {{ background:{pri_hover}; }}"
        )
        self.btn_scan.setStyleSheet(normal_qss)
        self.btn_settings.setStyleSheet(normal_qss)
        self.btn_fill.setStyleSheet(primary_qss)

        ai = icon_size(self.cfg, "app_icon")
        ti = icon_size(self.cfg, "toolbar")
        keep = color(self.cfg, "logo_icon_keep", False)
        logo_icon_color = None if keep else color(self.cfg, "logo_icon", "#ffffff")
        pm = icons.make_pixmap("layout", logo_icon_color, ai)
        if pm is not None:
            self.tb_app_icon.setPixmap(pm)

        btn_icon = color(self.cfg, "btn_icon", "#cfd6ea")
        pri_icon = color(self.cfg, "btn_primary_icon", "#eafff7")
        for btn, name, col in (
            (self.btn_fill, "add", pri_icon),
            (self.btn_scan, "search", btn_icon),
            (self.btn_settings, "setting", btn_icon),
        ):
            btn.setIcon(icons.make_icon(name, col, ti))
            btn.setIconSize(QSize(ti, ti))

    # ---- 隐藏栏 / 悬停浮出 ----
    def _update_toggle_icon(self):
        name = "down" if self._toolbar_hidden else "upward"
        self.toggle_btn.setIcon(icons.make_icon(name, "#cfd6ea", 16))
        self.toggle_btn.setIconSize(QSize(16, 16))

    def _toggle_toolbar(self):
        self._toolbar_hidden = not self._toolbar_hidden
        self.toolbar.setVisible(not self._toolbar_hidden)
        self._update_toggle_icon()
        QTimer.singleShot(0, self._reposition_all)

    def _place_toggle(self):
        central = self.centralWidget()
        if central is None:
            return
        tl = central.mapToGlobal(central.rect().topLeft())
        x = tl.x() + central.width() // 2 - self.toggle_btn.width() // 2
        y = tl.y() + 2
        self.toggle_btn.move(x, y)

    def _check_reveal(self):
        central = self.centralWidget()
        if central is None or not self._interactive():
            self.toggle_btn.hide()
            return
        tl = central.mapToGlobal(central.rect().topLeft())
        pos = QCursor.pos()
        cx = tl.x() + central.width() // 2
        in_zone = abs(pos.x() - cx) <= 110 and tl.y() <= pos.y() <= tl.y() + 40
        over_btn = (
            self.toggle_btn.isVisible()
            and self.toggle_btn.geometry().contains(pos)
        )
        if in_zone or over_btn:
            self._place_toggle()
            self.toggle_btn.show()
            self.toggle_btn.raise_()
        else:
            self.toggle_btn.hide()

    # ---- 配置刷新（debug / 设置 调用）----
    def apply_config(self):
        self.setWindowTitle(self.cfg["window_title"])
        self._apply_toolbar_config()
        for cell in self.cells:
            cell.apply_config()
        self._apply_collapse_threshold()
        self.enforce_timer.setInterval(self.cfg["enforce_interval"])
        self.watcher.timer.setInterval(self.cfg["watcher_interval"])

    def rebuild_layout(self):
        """主分割方向改变后，用当前行列重建结构。"""
        if self.rows and self.cols:
            self.apply_layout(self.rows, self.cols)

    # ---- 布局：预设 / 自定义 ----
    def on_preset_changed(self, name):
        if name == CUSTOM_LABEL:
            self.custom_widget.setVisible(True)
            self.cfg["default_grid"] = CUSTOM_LABEL
            r = self.cfg.get("custom_rows", 2)
            c = self.cfg.get("custom_cols", 3)
            self.apply_layout(r, c)
        else:
            self.custom_widget.setVisible(False)
            self.cfg["default_grid"] = name
            rows, cols = GRID_PRESETS[name]
            self.apply_layout(rows, cols)

    def _on_custom_changed(self):
        r = self.row_spin.value()
        c = self.col_spin.value()
        self.cfg["custom_rows"] = r
        self.cfg["custom_cols"] = c
        if self.combo.currentText() == CUSTOM_LABEL:
            self.apply_layout(r, c)

    def apply_layout(self, rows, cols):
        rows = max(1, min(MAX_RC, rows))
        cols = max(1, min(MAX_RC, cols))
        new_count = rows * cols
        old_cells = self.cells

        for cell in old_cells[new_count:]:
            cell.detach()

        cells = []
        for i in range(new_count):
            if i < len(old_cells):
                cell = old_cells[i]
                cell.set_index(i)
            else:
                cell = EmbedCell(i, self.cfg)
                cell.requestSwap.connect(self.swap_cells)
                cell.requestLaunch.connect(self.pick_into_cell)
                cell.requestRelease.connect(self.release_cell)
            cells.append(cell)

        removed = old_cells[new_count:]
        self.cells = cells
        self.rows = rows
        self.cols = cols
        self._rebuild_splitters(rows, cols, removed)

    def _rebuild_splitters(self, rows, cols, removed=()):
        for cell in self.cells:
            cell.setParent(None)
        if self.root_split is not None:
            self.root_split.setParent(None)
            self.root_split.deleteLater()
        for cell in removed:
            cell.setParent(None)
            cell.deleteLater()

        th = self.cfg.get("collapse_threshold", 160)
        primary = self.cfg.get("split_primary", "rows")
        self._splitters = []
        self._inner = []
        self._inner_last = {}

        if primary == "cols":
            # 外层水平分列（列联动贯穿），内层每列垂直分行（行可独立）
            outer = SnapSplitter(Qt.Orientation.Horizontal, th, self._reposition_all)
            outer.setObjectName("gridSplit")
            for c in range(cols):
                inner = SnapSplitter(
                    Qt.Orientation.Vertical, th, self._reposition_all
                )
                inner.splitterMoved.connect(
                    lambda pos, idx, s=inner: self._on_inner_moved(s)
                )
                self._inner.append(inner)
                for r in range(rows):
                    inner.addWidget(self.cells[r * cols + c])
                inner.setSizes([10000] * rows)
                outer.addWidget(inner)
            outer.setSizes([10000] * cols)
        else:
            # 外层垂直分行（行联动贯穿），内层每行水平分列（列可独立）
            outer = SnapSplitter(Qt.Orientation.Vertical, th, self._reposition_all)
            outer.setObjectName("gridSplit")
            for r in range(rows):
                inner = SnapSplitter(
                    Qt.Orientation.Horizontal, th, self._reposition_all
                )
                inner.splitterMoved.connect(
                    lambda pos, idx, s=inner: self._on_inner_moved(s)
                )
                self._inner.append(inner)
                for c in range(cols):
                    inner.addWidget(self.cells[r * cols + c])
                inner.setSizes([10000] * cols)
                outer.addWidget(inner)
            outer.setSizes([10000] * rows)

        self._splitters = [outer] + self._inner
        self.root_split = outer
        self.grid_layout.addWidget(outer)
        self._apply_resize_enabled()
        QTimer.singleShot(0, self._reposition_all)
        QTimer.singleShot(0, self._sync_splitters)
        QTimer.singleShot(0, self._refresh_inner_snapshots)
        QTimer.singleShot(150, self._reposition_all)
        QTimer.singleShot(150, self._refresh_inner_snapshots)
        QTimer.singleShot(350, self._reposition_all)

    def _on_inner_moved(self, source):
        """内层联动：把源分隔条的移动同步到其他内层分隔条（增量或复位）。"""
        if self._sync_guard:
            self._inner_last[source] = source.sizes()
            return
        if not self.cfg.get("sync_inner", False):
            self._inner_last[source] = source.sizes()
            self._reposition_all()
            return

        cur = source.sizes()
        prev = self._inner_last.get(source)
        mode = self.cfg.get("sync_mode", "delta")

        self._sync_guard = True
        try:
            for other in self._inner:
                if other is source or other.count() != len(cur):
                    continue
                if mode == "reset" or not prev or len(prev) != len(cur):
                    other.set_sizes_synced(cur)
                else:
                    os = other.sizes()
                    new = [
                        max(0, os[i] + (cur[i] - prev[i]))
                        for i in range(len(cur))
                    ]
                    other.set_sizes_synced(new)
                self._inner_last[other] = other.sizes()
        finally:
            self._sync_guard = False

        self._inner_last[source] = cur
        self._reposition_all()

    def _refresh_inner_snapshots(self):
        for s in self._inner:
            self._inner_last[s] = s.sizes()

    def _sync_splitters(self):
        for split in self._splitters:
            split.sync_last()

    def _apply_collapse_threshold(self):
        th = self.cfg.get("collapse_threshold", 160)
        for split in self._splitters:
            split.set_threshold(th)

    def _apply_resize_enabled(self):
        enabled = self.cfg.get("resize_enabled", True)
        for split in self._splitters:
            split.setHandleWidth(6 if enabled else 2)
            for i in range(1, split.count()):
                handle = split.handle(i)
                if handle is None:
                    continue
                handle.setEnabled(enabled)
                if enabled:
                    if split.orientation() == Qt.Orientation.Horizontal:
                        handle.setCursor(Qt.CursorShape.SizeHorCursor)
                    else:
                        handle.setCursor(Qt.CursorShape.SizeVerCursor)
                else:
                    handle.setCursor(Qt.CursorShape.ArrowCursor)

    def _reposition_all(self):
        for cell in self.cells:
            cell.reposition()

    def _enforce_all(self):
        for cell in self.cells:
            cell.enforce()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口尺寸变化会改变各分隔条内部尺寸，刷新快照避免下次增量同步算错
        if self._inner:
            self._refresh_inner_snapshots()

    # ---- 拖拽吸附回调 ----
    def _on_drag_hover(self, index):
        if not self._visible_usable():
            for cell in self.cells:
                cell.set_drop_highlight(False)
            return
        for cell in self.cells:
            cell.set_drop_highlight(cell.index == index)

    def _on_drag_drop(self, hwnd, index):
        for cell in self.cells:
            cell.set_drop_highlight(False)
        if not self._visible_usable():
            return
        if 0 <= index < len(self.cells):
            self.cells[index].attach(hwnd)
            self._save_session()

    # ---- 换位 ----
    def swap_cells(self, from_index, to_index):
        if from_index >= len(self.cells) or to_index >= len(self.cells):
            return
        a = self.cells[from_index]
        b = self.cells[to_index]
        info_a = a.take()
        info_b = b.take()
        a.give(info_b)
        b.give(info_a)
        self._save_session()

    # ---- 选择嵌入 ----
    def _embedded_hwnds(self):
        return {c.child_hwnd for c in self.cells if c.child_hwnd}

    def pick_into_cell(self, index):
        if index >= len(self.cells):
            return
        cell = self.cells[index]
        if cell.child_hwnd is not None:
            return
        dlg = WindowPicker(exclude=self._embedded_hwnds(), multi=False, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            hwnds = dlg.selected_hwnds()
            if hwnds:
                cell.attach(hwnds[0])
                self._save_session()

    def pick_and_fill(self):
        empty = [c for c in self.cells if c.child_hwnd is None]
        if not empty:
            QMessageBox.information(self, "提示", "当前没有空槽可以填充。")
            return
        dlg = WindowPicker(exclude=self._embedded_hwnds(), multi=True, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            hwnds = dlg.selected_hwnds()
            for cell in empty:
                if not hwnds:
                    break
                cell.attach(hwnds.pop(0))
            self._save_session()

    def scan_and_attach(self):
        embedded = self._embedded_hwnds()
        available = [
            hwnd for hwnd, _ in win32_utils.find_embeddable_windows()
            if hwnd not in embedded
        ]
        if not available:
            QMessageBox.information(self, "扫描结果", "没有发现可嵌入的窗口。")
            return
        for cell in self.cells:
            if not available:
                break
            if cell.child_hwnd is None:
                cell.attach(available.pop(0))
        self._save_session()

    # ---- 会话记忆 ----
    def _save_session(self):
        session.save_session(self.cells)

    def restore_session(self):
        data = session.load_session()
        slots = data.get("slots", [])
        if not slots:
            return
        used = set()
        candidates = win32_utils.find_embeddable_windows()
        for slot in slots:
            idx = slot.get("index", -1)
            if not (0 <= idx < len(self.cells)):
                continue
            if self.cells[idx].child_hwnd is not None:
                continue
            want_exe = (slot.get("exe") or "").lower()
            want_title = slot.get("title") or ""
            if not want_exe:
                continue
            best = None
            for hwnd, title in candidates:
                if hwnd in used:
                    continue
                ex = (win32_utils.get_window_exe(hwnd) or "").lower()
                if ex == want_exe:
                    if title == want_title:
                        best = hwnd
                        break
                    if best is None:
                        best = hwnd
            if best:
                used.add(best)
                fixwindows.fix_stuck_window(best)
                self.cells[idx].attach(best)
        self._save_session()

    # ---- 窗口管理 ----
    def release_cell(self, index):
        if 0 <= index < len(self.cells):
            self.cells[index].detach()
            self._save_session()

    def close_cell(self, index):
        if 0 <= index < len(self.cells):
            cell = self.cells[index]
            if cell.child_hwnd:
                win32_utils.close_window(cell.child_hwnd)
                cell.clear_slot()
                self._save_session()

    def force_close_cell(self, index):
        if 0 <= index < len(self.cells):
            cell = self.cells[index]
            if cell.child_hwnd:
                win32_utils.force_close_window(cell.child_hwnd)
                cell.clear_slot()
                self._save_session()

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    # ---- debug 用统计 ----
    def usage_stats(self):
        embedded = [c for c in self.cells if c.child_hwnd]
        lines = [
            f"网格: {self.rows} x {self.cols}（共 {len(self.cells)} 格）",
            f"已嵌入窗口: {len(embedded)}",
            "-" * 30,
        ]
        for c in self.cells:
            if c.child_hwnd:
                lines.append(
                    f"[{c.index + 1}] {win32_utils.get_window_title(c.child_hwnd)}"
                )
            else:
                lines.append(f"[{c.index + 1}] （空）")
        return "\n".join(lines)

    def closeEvent(self, event):
        self._save_session()
        self.reveal_timer.stop()
        self.save_timer.stop()
        self.enforce_timer.stop()
        self.watcher.stop()
        self.toggle_btn.close()
        for cell in self.cells:
            cell.detach()
        QApplication.processEvents()
        super().closeEvent(event)
