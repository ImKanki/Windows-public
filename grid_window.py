# -*- coding: utf-8 -*-
"""网格主窗口：布局、网格切换、启动 VSCode、拖拽换位/吸附/释放、巡检、窗口管理。"""
import copy
import ctypes

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import icons
import styles
import vscode_manager
import win32_utils
from config import DEFAULT_CFG, color, font_size, icon_size
from drag_watcher import DragWatcher
from embed_cell import EmbedCell
from settings_dialog import SettingsDialog

GRID_PRESETS = {
    "1 x 2": (1, 2),
    "2 x 2 (4)": (2, 2),
    "2 x 3 (6)": (2, 3),
    "3 x 3 (9)": (3, 3),
    "3 x 4 (12)": (3, 4),
    "4 x 4 (16)": (4, 4),
}
MAX_CELLS = 16


class GridWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = copy.deepcopy(DEFAULT_CFG)
        self.cells = []
        self.rows = 0
        self.cols = 0

        self.setWindowTitle(self.cfg["window_title"])
        self.resize(self.cfg["win_w"], self.cfg["win_h"])

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_toolbar())

        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(6)
        self.grid.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.grid_container, 1)

        start = self.cfg["default_grid"]
        if start not in GRID_PRESETS:
            start = "2 x 2 (4)"
        self.combo.setCurrentText(start)
        self.apply_grid(start)

        self.watcher = DragWatcher(self)
        self.watcher.hover.connect(self._on_drag_hover)
        self.watcher.drop.connect(self._on_drag_drop)
        self.watcher.timer.setInterval(self.cfg["watcher_interval"])
        self.watcher.start()

        self.enforce_timer = QTimer(self)
        self.enforce_timer.setInterval(self.cfg["enforce_interval"])
        self.enforce_timer.timeout.connect(self._enforce_all)
        self.enforce_timer.start()

        self._dark_titlebar()

    def _dark_titlebar(self):
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass

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

        # Logo 徽章：图标 + 标题包进一个整体
        self.logo = QWidget()
        self.logo.setObjectName("logoBadge")
        logo_lay = QHBoxLayout(self.logo)
        logo_lay.setContentsMargins(10, 5, 12, 5)
        logo_lay.setSpacing(8)

        self.tb_app_icon = QLabel()
        self.tb_app_icon.setObjectName("logoIcon")
        logo_lay.addWidget(self.tb_app_icon)

        self.tb_title = QLabel("VSCode 网格")
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
        self.combo.addItems(GRID_PRESETS.keys())
        self.combo.currentTextChanged.connect(self.apply_grid)
        layout.addWidget(self.combo)

        layout.addSpacing(4)
        sep2 = self._vsep()
        self._seps.append(sep2)
        layout.addWidget(sep2)
        layout.addSpacing(4)

        self.btn_fill = QPushButton("  填满空槽")
        self.btn_fill.setObjectName("primary")
        self.btn_fill.clicked.connect(self.fill_empty_cells)
        layout.addWidget(self.btn_fill)

        self.btn_scan = QPushButton("  扫描窗口")
        self.btn_scan.clicked.connect(self.scan_and_attach)
        layout.addWidget(self.btn_scan)

        self.btn_settings = QPushButton("  设置")
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        layout.addStretch(1)

        self.tb_hint = QLabel(
            "拖标题栏到外部松手＝释放　·　拖到其它槽＝换位　·　双击空槽新建"
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
        # 图标 label 背景透明，透出 logo 矩形底色，跟随渐变一起变
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

        # 按钮配色
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

        # 图标
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

    # ---- 配置刷新（debug 调用）----
    def apply_config(self):
        self.setWindowTitle(self.cfg["window_title"])
        self._apply_toolbar_config()
        for cell in self.cells:
            cell.apply_config()
        self.enforce_timer.setInterval(self.cfg["enforce_interval"])
        self.watcher.timer.setInterval(self.cfg["watcher_interval"])

    # ---- 网格 ----
    def apply_grid(self, preset_name):
        rows, cols = GRID_PRESETS[preset_name]
        new_count = rows * cols

        for cell in self.cells[new_count:]:
            cell.detach()

        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        for r in range(self.grid.rowCount()):
            self.grid.setRowStretch(r, 0)
        for c in range(self.grid.columnCount()):
            self.grid.setColumnStretch(c, 0)

        old_cells = self.cells
        self.cells = []
        self.rows = rows
        self.cols = cols

        for i in range(new_count):
            if i < len(old_cells):
                cell = old_cells[i]
                cell.set_index(i)
            else:
                cell = EmbedCell(i, self.cfg)
                cell.requestSwap.connect(self.swap_cells)
                cell.requestLaunch.connect(self.launch_into_cell)
                cell.requestRelease.connect(self.release_cell)
            self.cells.append(cell)
            self.grid.addWidget(cell, i // cols, i % cols)

        for r in range(rows):
            self.grid.setRowStretch(r, 1)
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)

        QTimer.singleShot(0, self._reposition_all)
        QTimer.singleShot(120, self._reposition_all)
        QTimer.singleShot(300, self._reposition_all)

    def _reposition_all(self):
        for cell in self.cells:
            cell.reposition()

    def _enforce_all(self):
        for cell in self.cells:
            cell.enforce()

    # ---- 拖拽吸附回调 ----
    def _on_drag_hover(self, index):
        for cell in self.cells:
            cell.set_drop_highlight(cell.index == index)

    def _on_drag_drop(self, hwnd, index):
        for cell in self.cells:
            cell.set_drop_highlight(False)
        if 0 <= index < len(self.cells):
            self.cells[index].attach(hwnd)

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

    # ---- 启动 / 扫描 ----
    def launch_into_cell(self, index):
        if index >= len(self.cells):
            return
        cell = self.cells[index]
        if cell.child_hwnd is not None:
            return
        try:
            hwnd = vscode_manager.launch_new_vscode()
        except FileNotFoundError as e:
            QMessageBox.warning(self, "启动失败", str(e))
            return
        if hwnd:
            cell.attach(hwnd)
        else:
            QMessageBox.warning(self, "启动超时", "等待 VSCode 窗口出现超时，请重试。")

    def fill_empty_cells(self):
        empty = [c for c in self.cells if c.child_hwnd is None]
        if not empty:
            return
        for cell in empty:
            try:
                hwnd = vscode_manager.launch_new_vscode()
            except FileNotFoundError as e:
                QMessageBox.warning(self, "启动失败", str(e))
                return
            if hwnd:
                cell.attach(hwnd)

    def scan_and_attach(self):
        embedded = {c.child_hwnd for c in self.cells if c.child_hwnd}
        available = [
            hwnd for hwnd, _ in win32_utils.find_vscode_windows()
            if hwnd not in embedded
        ]
        if not available:
            QMessageBox.information(self, "扫描结果", "没有发现可嵌入的独立 VSCode 窗口。")
            return
        for cell in self.cells:
            if not available:
                break
            if cell.child_hwnd is None:
                cell.attach(available.pop(0))

    # ---- 窗口管理 ----
    def release_cell(self, index):
        if 0 <= index < len(self.cells):
            self.cells[index].detach()

    def close_cell(self, index):
        if 0 <= index < len(self.cells):
            cell = self.cells[index]
            if cell.child_hwnd:
                win32_utils.close_window(cell.child_hwnd)
                cell.clear_slot()

    def force_close_cell(self, index):
        if 0 <= index < len(self.cells):
            cell = self.cells[index]
            if cell.child_hwnd:
                win32_utils.force_close_window(cell.child_hwnd)
                cell.clear_slot()

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
        self.enforce_timer.stop()
        self.watcher.stop()
        for cell in self.cells:
            cell.detach()
        super().closeEvent(event)
