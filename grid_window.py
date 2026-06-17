"""网格主窗口：布局、网格尺寸切换、启动 VSCode、拖拽换位/吸附、窗口管理。"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
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
import vscode_manager
import win32_utils
from drag_watcher import DragWatcher
from embed_cell import EmbedCell
from settings_dialog import SettingsDialog

# 预设网格：名称 -> (行, 列)
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
        self.setWindowTitle("VSCode 窗口网格容器")
        self.resize(1400, 900)
        self.cells = []
        self.rows = 0
        self.cols = 0

        central = QWidget()
        central.setStyleSheet("background: #1e1e1e;")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # 工具栏
        root.addWidget(self._build_toolbar())

        # 网格容器（占据剩余全部空间）
        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(4)
        self.grid.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.grid_container, 1)

        self.combo.setCurrentText("2 x 2 (4)")
        self.apply_grid("2 x 2 (4)")

        # 全局拖拽吸附
        self.watcher = DragWatcher(self)
        self.watcher.hover.connect(self._on_drag_hover)
        self.watcher.drop.connect(self._on_drag_drop)
        self.watcher.start()

    def _build_toolbar(self):
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet(
            "QLabel { color: #cccccc; }"
            "QComboBox { background: #3a3d41; color: #eee; border: 1px solid #555;"
            " border-radius: 3px; padding: 2px 6px; }"
            "QComboBox QAbstractItemView { background: #2d2d30; color: #eee;"
            " selection-background-color: #094771; }"
            "QPushButton { background: #3a3d41; color: #eee; border: 1px solid #555;"
            " border-radius: 3px; padding: 4px 10px; }"
            "QPushButton:hover { background: #4a4d51; }"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        layout.addWidget(QLabel("网格："))
        self.combo = QComboBox()
        self.combo.addItems(GRID_PRESETS.keys())
        self.combo.currentTextChanged.connect(self.apply_grid)
        layout.addWidget(self.combo)

        btn_fill = QPushButton(" 启动并填满空槽")
        btn_fill.setIcon(icons.make_icon("add"))
        btn_fill.clicked.connect(self.fill_empty_cells)
        layout.addWidget(btn_fill)

        btn_scan = QPushButton(" 扫描已有窗口")
        btn_scan.setIcon(icons.make_icon("scanning"))
        btn_scan.clicked.connect(self.scan_and_attach)
        layout.addWidget(btn_scan)

        btn_settings = QPushButton(" 设置")
        btn_settings.setIcon(icons.make_icon("setting"))
        btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(btn_settings)

        layout.addStretch(1)

        hint = QLabel("拖动 VSCode 标题栏可吸附入槽 · 拖动槽位标题可换位 · 双击空槽启动新实例")
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        return bar

    def apply_grid(self, preset_name):
        rows, cols = GRID_PRESETS[preset_name]
        new_count = rows * cols

        # 缩小网格时，超出部分的窗口释放回独立窗口
        for cell in self.cells[new_count:]:
            cell.detach()

        # 清空旧布局占位与拉伸
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
                cell = EmbedCell(i)
                cell.requestSwap.connect(self.swap_cells)
                cell.requestLaunch.connect(self.launch_into_cell)
            self.cells.append(cell)
            self.grid.addWidget(cell, i // cols, i % cols)

        for r in range(rows):
            self.grid.setRowStretch(r, 1)
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)

        # 布局生效后多打几拍，确保嵌入窗口填满新尺寸
        QTimer.singleShot(0, self._reposition_all)
        QTimer.singleShot(120, self._reposition_all)
        QTimer.singleShot(300, self._reposition_all)

    def _reposition_all(self):
        for cell in self.cells:
            cell.reposition()

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

    # ---- 窗口管理（供设置对话框调用）----
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

    def closeEvent(self, event):
        self.watcher.stop()
        for cell in self.cells:
            cell.detach()
        super().closeEvent(event)
