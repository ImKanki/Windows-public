# -*- coding: utf-8 -*-
"""Main adjustable workspace window with a modern, always-visible command bar."""

import copy
import ctypes

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolButton,
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
from version import __version__
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

        self.setWindowTitle(self.cfg["window_title"])
        self.resize(self.cfg["win_w"], self.cfg["win_h"])
        self.setMinimumSize(900, 620)

        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        self.workspace_body = QWidget()
        self.workspace_body.setObjectName("workspaceBody")
        workspace_layout = QVBoxLayout(self.workspace_body)
        margin = int(self.cfg.get("workspace_margin", 12))
        workspace_layout.setContentsMargins(
            margin,
            margin,
            margin,
            max(8, margin - 2),
        )
        workspace_layout.setSpacing(0)

        self.grid_container = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.addWidget(self.grid_container, 1)
        root.addWidget(self.workspace_body, 1)

        root.addWidget(self._build_status_bar())

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

        self.save_timer = QTimer(self)
        self.save_timer.setInterval(3000)
        self.save_timer.timeout.connect(self._save_session)
        self.save_timer.start()

        self._dark_titlebar()
        win32_utils.register_own_hwnd(int(self.winId()))
        self._update_status()

        QTimer.singleShot(600, self.restore_session)

    def _dark_titlebar(self):
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                20,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
        except Exception:
            pass

    def _visible_usable(self):
        if not self.isVisible():
            return False
        if self.windowState() & Qt.WindowState.WindowMinimized:
            return False
        return True

    # ---------- Command bar ----------

    def _build_toolbar(self):
        bar = QWidget()
        bar.setObjectName("appBar")
        self.toolbar = bar

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 7, 14, 7)
        layout.setSpacing(10)

        brand = QWidget()
        brand.setObjectName("brandBlock")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)

        self.brand_mark = QLabel("W")
        self.brand_mark.setObjectName("brandMark")
        self.brand_mark.setFixedSize(32, 32)
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(self.brand_mark)

        title_stack = QVBoxLayout()
        title_stack.setContentsMargins(0, 0, 0, 0)
        title_stack.setSpacing(0)

        self.tb_title = QLabel("Workspace")
        self.tb_title.setObjectName("brandTitle")
        title_stack.addWidget(self.tb_title)

        caption = QLabel("Window grid")
        caption.setObjectName("brandCaption")
        title_stack.addWidget(caption)

        brand_layout.addLayout(title_stack)
        layout.addWidget(brand)
        layout.addSpacing(12)

        layout_label = QLabel("布局")
        layout_label.setObjectName("fieldLabel")
        layout.addWidget(layout_label)

        self.combo = QComboBox()
        self.combo.setMinimumWidth(126)
        self.combo.addItems(
            list(GRID_PRESETS.keys()) + [CUSTOM_LABEL]
        )
        self.combo.currentTextChanged.connect(
            self.on_preset_changed
        )
        layout.addWidget(self.combo)

        self.custom_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(6)

        self.row_spin = QSpinBox()
        self.row_spin.setRange(1, MAX_RC)
        self.row_spin.setValue(
            self.cfg.get("custom_rows", 2)
        )
        self.row_spin.setPrefix("行 ")
        self.row_spin.setFixedWidth(72)
        custom_layout.addWidget(self.row_spin)

        self.col_spin = QSpinBox()
        self.col_spin.setRange(1, MAX_RC)
        self.col_spin.setValue(
            self.cfg.get("custom_cols", 3)
        )
        self.col_spin.setPrefix("列 ")
        self.col_spin.setFixedWidth(72)
        custom_layout.addWidget(self.col_spin)

        self.row_spin.valueChanged.connect(
            self._on_custom_changed
        )
        self.col_spin.valueChanged.connect(
            self._on_custom_changed
        )
        self.custom_widget.setVisible(False)
        layout.addWidget(self.custom_widget)

        layout.addStretch(1)

        version_label = QLabel(f"v{__version__}")
        version_label.setObjectName("versionPill")
        layout.addWidget(version_label)

        self.btn_fill = QPushButton("添加窗口")
        self.btn_fill.setObjectName("primaryButton")
        self.btn_fill.clicked.connect(self.pick_and_fill)
        layout.addWidget(self.btn_fill)

        self.btn_scan = QToolButton()
        self.btn_scan.setToolTip("扫描并填充可用窗口")
        self.btn_scan.clicked.connect(self.scan_and_attach)
        layout.addWidget(self.btn_scan)

        self.btn_settings = QToolButton()
        self.btn_settings.setToolTip("设置")
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        self._apply_toolbar_config()
        return bar

    def _apply_toolbar_config(self):
        self.toolbar.setFixedHeight(self.cfg["toolbar_height"])

        toolbar_icon_size = icon_size(self.cfg, "toolbar")
        primary_icon_color = color(
            self.cfg,
            "btn_primary_icon",
            "#FFFFFF",
        )
        normal_icon_color = color(
            self.cfg,
            "btn_icon",
            "#AAB3C2",
        )

        self.btn_fill.setIcon(
            icons.make_icon(
                "add",
                primary_icon_color,
                toolbar_icon_size,
            )
        )
        self.btn_fill.setIconSize(
            QSize(toolbar_icon_size, toolbar_icon_size)
        )

        self.btn_scan.setIcon(
            icons.make_icon(
                "search",
                normal_icon_color,
                toolbar_icon_size,
            )
        )
        self.btn_scan.setIconSize(
            QSize(toolbar_icon_size, toolbar_icon_size)
        )

        self.btn_settings.setIcon(
            icons.make_icon(
                "setting",
                normal_icon_color,
                toolbar_icon_size,
            )
        )
        self.btn_settings.setIconSize(
            QSize(toolbar_icon_size, toolbar_icon_size)
        )

    def _build_status_bar(self):
        bar = QWidget()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(self.cfg.get("status_height", 30))

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        self.status_summary = QLabel()
        self.status_summary.setObjectName("statusSummary")
        layout.addWidget(self.status_summary)

        layout.addStretch(1)

        hint = QLabel(
            "拖入标题栏 · 双击空窗口 · 拖动顶部可交换 · ⋯ 管理窗口"
        )
        hint.setObjectName("statusHint")
        layout.addWidget(hint)

        return bar

    def _update_status(self):
        if not hasattr(self, "status_summary"):
            return
        connected = sum(
            1 for cell in self.cells if cell.child_hwnd
        )
        self.status_summary.setText(
            f"{self.rows} × {self.cols}  ·  "
            f"{connected}/{len(self.cells)} 个窗口已连接"
        )

    # ---------- Configuration ----------

    def apply_config(self):
        self.setWindowTitle(self.cfg["window_title"])
        self._apply_toolbar_config()

        margin = int(self.cfg.get("workspace_margin", 12))
        layout = self.workspace_body.layout()
        layout.setContentsMargins(
            margin,
            margin,
            margin,
            max(8, margin - 2),
        )

        for cell in self.cells:
            cell.apply_config()

        self._apply_collapse_threshold()
        self.enforce_timer.setInterval(
            self.cfg["enforce_interval"]
        )
        self.watcher.timer.setInterval(
            self.cfg["watcher_interval"]
        )

    def rebuild_layout(self):
        if self.rows and self.cols:
            self.apply_layout(self.rows, self.cols)

    # ---------- Grid layout ----------

    def on_preset_changed(self, name):
        if name == CUSTOM_LABEL:
            self.custom_widget.setVisible(True)
            self.cfg["default_grid"] = CUSTOM_LABEL
            rows = self.cfg.get("custom_rows", 2)
            cols = self.cfg.get("custom_cols", 3)
            self.apply_layout(rows, cols)
            return

        self.custom_widget.setVisible(False)
        self.cfg["default_grid"] = name
        rows, cols = GRID_PRESETS[name]
        self.apply_layout(rows, cols)

    def _on_custom_changed(self):
        rows = self.row_spin.value()
        cols = self.col_spin.value()
        self.cfg["custom_rows"] = rows
        self.cfg["custom_cols"] = cols

        if self.combo.currentText() == CUSTOM_LABEL:
            self.apply_layout(rows, cols)

    def apply_layout(self, rows, cols):
        rows = max(1, min(MAX_RC, rows))
        cols = max(1, min(MAX_RC, cols))
        new_count = rows * cols

        old_cells = self.cells
        for cell in old_cells[new_count:]:
            cell.detach()

        cells = []
        for index in range(new_count):
            if index < len(old_cells):
                cell = old_cells[index]
                cell.set_index(index)
            else:
                cell = EmbedCell(index, self.cfg)
                cell.requestSwap.connect(self.swap_cells)
                cell.requestLaunch.connect(self.pick_into_cell)
                cell.requestRelease.connect(self.release_cell)
                cell.requestClose.connect(self.close_cell)
                cell.requestForceClose.connect(
                    self.confirm_force_close_cell
                )
            cells.append(cell)

        removed = old_cells[new_count:]
        self.cells = cells
        self.rows = rows
        self.cols = cols

        self._rebuild_splitters(rows, cols, removed)
        self._update_status()

    def _rebuild_splitters(self, rows, cols, removed=()):
        for cell in self.cells:
            cell.setParent(None)

        if self.root_split is not None:
            self.root_split.setParent(None)
            self.root_split.deleteLater()

        for cell in removed:
            cell.setParent(None)
            cell.deleteLater()

        threshold = self.cfg.get("collapse_threshold", 160)
        primary = self.cfg.get("split_primary", "rows")

        self._splitters = []
        self._inner = []
        self._inner_last = {}

        if primary == "cols":
            outer = SnapSplitter(
                Qt.Orientation.Horizontal,
                threshold,
                self._reposition_all,
            )
            outer.setObjectName("workspaceSplit")

            for column in range(cols):
                inner = SnapSplitter(
                    Qt.Orientation.Vertical,
                    threshold,
                    self._reposition_all,
                )
                inner.splitterMoved.connect(
                    lambda pos, idx, split=inner:
                    self._on_inner_moved(split)
                )
                self._inner.append(inner)

                for row in range(rows):
                    inner.addWidget(
                        self.cells[row * cols + column]
                    )
                inner.setSizes([10000] * rows)
                outer.addWidget(inner)

            outer.setSizes([10000] * cols)

        else:
            outer = SnapSplitter(
                Qt.Orientation.Vertical,
                threshold,
                self._reposition_all,
            )
            outer.setObjectName("workspaceSplit")

            for row in range(rows):
                inner = SnapSplitter(
                    Qt.Orientation.Horizontal,
                    threshold,
                    self._reposition_all,
                )
                inner.splitterMoved.connect(
                    lambda pos, idx, split=inner:
                    self._on_inner_moved(split)
                )
                self._inner.append(inner)

                for column in range(cols):
                    inner.addWidget(
                        self.cells[row * cols + column]
                    )
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
        if self._sync_guard:
            self._inner_last[source] = source.sizes()
            return

        if not self.cfg.get("sync_inner", False):
            self._inner_last[source] = source.sizes()
            self._reposition_all()
            return

        current = source.sizes()
        previous = self._inner_last.get(source)
        mode = self.cfg.get("sync_mode", "delta")

        self._sync_guard = True
        try:
            for other in self._inner:
                if other is source or other.count() != len(current):
                    continue

                if (
                    mode == "reset"
                    or not previous
                    or len(previous) != len(current)
                ):
                    other.set_sizes_synced(current)
                else:
                    other_sizes = other.sizes()
                    new_sizes = [
                        max(
                            0,
                            other_sizes[index]
                            + current[index]
                            - previous[index],
                        )
                        for index in range(len(current))
                    ]
                    other.set_sizes_synced(new_sizes)

                self._inner_last[other] = other.sizes()
        finally:
            self._sync_guard = False

        self._inner_last[source] = current
        self._reposition_all()

    def _refresh_inner_snapshots(self):
        for splitter in self._inner:
            self._inner_last[splitter] = splitter.sizes()

    def _sync_splitters(self):
        for splitter in self._splitters:
            splitter.sync_last()

    def _apply_collapse_threshold(self):
        threshold = self.cfg.get("collapse_threshold", 160)
        for splitter in self._splitters:
            splitter.set_threshold(threshold)

    def _apply_resize_enabled(self):
        enabled = self.cfg.get("resize_enabled", True)

        for splitter in self._splitters:
            splitter.setHandleWidth(7 if enabled else 2)

            for index in range(1, splitter.count()):
                handle = splitter.handle(index)
                if handle is None:
                    continue

                handle.setEnabled(enabled)
                if not enabled:
                    handle.setCursor(Qt.CursorShape.ArrowCursor)
                elif (
                    splitter.orientation()
                    == Qt.Orientation.Horizontal
                ):
                    handle.setCursor(
                        Qt.CursorShape.SizeHorCursor
                    )
                else:
                    handle.setCursor(
                        Qt.CursorShape.SizeVerCursor
                    )

    def _reposition_all(self):
        for cell in self.cells:
            cell.reposition()

    def _enforce_all(self):
        for cell in self.cells:
            cell.enforce()
        self._update_status()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._inner:
            self._refresh_inner_snapshots()

    # ---------- Drag and drop ----------

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
            self._update_status()

    # ---------- Cell operations ----------

    def swap_cells(self, from_index, to_index):
        if (
            from_index >= len(self.cells)
            or to_index >= len(self.cells)
        ):
            return

        source = self.cells[from_index]
        target = self.cells[to_index]

        source_binding = source.take()
        target_binding = target.take()
        source.give(target_binding)
        target.give(source_binding)

        self._save_session()
        self._update_status()

    def _embedded_hwnds(self):
        return {
            cell.child_hwnd
            for cell in self.cells
            if cell.child_hwnd
        }

    def pick_into_cell(self, index):
        if index >= len(self.cells):
            return

        cell = self.cells[index]
        if cell.child_hwnd is not None:
            return

        dialog = WindowPicker(
            exclude=self._embedded_hwnds(),
            multi=False,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.selected_hwnds()
            if selected:
                cell.attach(selected[0])
                self._save_session()
                self._update_status()

    def pick_and_fill(self):
        empty = [
            cell
            for cell in self.cells
            if cell.child_hwnd is None
        ]
        if not empty:
            QMessageBox.information(
                self,
                "没有空窗口",
                "当前工作区没有可用的空窗口。",
            )
            return

        dialog = WindowPicker(
            exclude=self._embedded_hwnds(),
            multi=True,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.selected_hwnds()
            for cell in empty:
                if not selected:
                    break
                cell.attach(selected.pop(0))

            self._save_session()
            self._update_status()

    def scan_and_attach(self):
        embedded = self._embedded_hwnds()
        available = [
            hwnd
            for hwnd, _ in win32_utils.find_embeddable_windows()
            if hwnd not in embedded
        ]

        if not available:
            QMessageBox.information(
                self,
                "扫描完成",
                "没有发现可添加的应用窗口。",
            )
            return

        for cell in self.cells:
            if not available:
                break
            if cell.child_hwnd is None:
                cell.attach(available.pop(0))

        self._save_session()
        self._update_status()

    # ---------- Session ----------

    def _save_session(self):
        session.save_session(self.cells)

    def restore_session(self):
        data = session.load_session()
        slots = data.get("slots", [])
        if not slots:
            self._update_status()
            return

        used = set()
        candidates = win32_utils.find_embeddable_windows()

        for slot in slots:
            index = slot.get("index", -1)
            if not 0 <= index < len(self.cells):
                continue
            if self.cells[index].child_hwnd is not None:
                continue

            expected_exe = (slot.get("exe") or "").lower()
            expected_title = slot.get("title") or ""
            if not expected_exe:
                continue

            best = None
            for hwnd, title in candidates:
                if hwnd in used:
                    continue

                actual_exe = (
                    win32_utils.get_window_exe(hwnd) or ""
                ).lower()
                if actual_exe != expected_exe:
                    continue

                if title == expected_title:
                    best = hwnd
                    break

                if best is None:
                    best = hwnd

            if best:
                used.add(best)
                fixwindows.fix_stuck_window(best)
                self.cells[index].attach(best)

        self._save_session()
        self._update_status()

    # ---------- Window lifecycle ----------

    def release_cell(self, index):
        if 0 <= index < len(self.cells):
            self.cells[index].detach()
            self._save_session()
            self._update_status()

    def close_cell(self, index):
        if 0 <= index < len(self.cells):
            cell = self.cells[index]
            if cell.child_hwnd:
                win32_utils.close_window(cell.child_hwnd)
            cell.clear_slot()
            self._save_session()
            self._update_status()

    def confirm_force_close_cell(self, index):
        if not 0 <= index < len(self.cells):
            return

        result = QMessageBox.question(
            self,
            "确认强制关闭",
            "未保存内容可能丢失。确定强制关闭这个窗口吗？",
        )
        if result == QMessageBox.StandardButton.Yes:
            self.force_close_cell(index)

    def force_close_cell(self, index):
        if 0 <= index < len(self.cells):
            cell = self.cells[index]
            if cell.child_hwnd:
                win32_utils.force_close_window(
                    cell.child_hwnd
                )
            cell.clear_slot()
            self._save_session()
            self._update_status()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()
        self._update_status()

    def usage_stats(self):
        embedded = [
            cell for cell in self.cells if cell.child_hwnd
        ]
        lines = [
            f"版本: {__version__}",
            f"网格: {self.rows} x {self.cols}"
            f"（共 {len(self.cells)} 格）",
            f"已嵌入窗口: {len(embedded)}",
            "-" * 30,
        ]
        for cell in self.cells:
            if cell.child_hwnd:
                lines.append(
                    f"[{cell.index + 1}] "
                    f"{win32_utils.get_window_title(cell.child_hwnd)}"
                )
            else:
                lines.append(
                    f"[{cell.index + 1}] （空）"
                )
        return "\n".join(lines)

    def closeEvent(self, event):
        self._save_session()
        self.save_timer.stop()
        self.enforce_timer.stop()
        self.watcher.stop()

        for cell in self.cells:
            cell.detach()

        QApplication.processEvents()
        super().closeEvent(event)
