"""单个网格槽位：承载一个嵌入的 VSCode 窗口，支持拖拽换位与拖入高亮。"""
from PySide6.QtCore import Qt, QMimeData, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import icons
import win32_utils

HEADER_HEIGHT = 28


class HostWidget(QWidget):
    """嵌入窗口的承载区。自身尺寸一变就回调，确保嵌入窗口实时填满。"""

    def __init__(self, on_resize, parent=None):
        super().__init__(parent)
        self._on_resize = on_resize
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setStyleSheet("background: #252526;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_resize()


class DragHeader(QWidget):
    """槽位标题栏：左侧拖动图标 + 标题，右侧关闭按钮。按住可拖动换位。"""

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setFixedHeight(HEADER_HEIGHT)
        self.setStyleSheet("background: #2d2d30;")
        self._press = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 4, 0)
        lay.setSpacing(6)

        self.icon = QLabel(icons.char("drag"))
        self.icon.setFont(icons.icon_font(14))
        self.icon.setStyleSheet("color: #888;")
        lay.addWidget(self.icon)

        self.title = QLabel("（空）")
        self.title.setStyleSheet("color: #cccccc; font-size: 12px;")
        lay.addWidget(self.title, 1)

        self.btn_close = QToolButton()
        self.btn_close.setText(icons.char("close"))
        self.btn_close.setFont(icons.icon_font(13))
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("释放为独立窗口")
        self.btn_close.setStyleSheet(
            "QToolButton { color: #aaa; border: none; background: transparent; }"
            "QToolButton:hover { color: #fff; }"
        )
        lay.addWidget(self.btn_close)

        self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        if (event.position().toPoint() - self._press).manhattanLength() < 10:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"cell:{self.index}")
        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        pixmap.fill(QColor("#094771"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            pixmap.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + self.title.text()
        )
        painter.end()
        drag.setPixmap(pixmap)

        self._press = None
        drag.exec(Qt.MoveAction)


class EmbedCell(QFrame):
    requestSwap = Signal(int, int)   # (from_index, to_index)
    requestLaunch = Signal(int)      # 在该单元启动新 VSCode

    NORMAL_STYLE = "#embedCell { border: 1px solid #3c3c3c; background: #1e1e1e; }"
    HOVER_STYLE = "#embedCell { border: 2px solid #007acc; background: #133047; }"

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.child_hwnd = None
        self.original_style = None
        self.setAcceptDrops(True)
        self.setObjectName("embedCell")
        self.setStyleSheet(self.NORMAL_STYLE)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(120, 90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = DragHeader(index, self)
        self.header.btn_close.clicked.connect(self._on_close_clicked)
        layout.addWidget(self.header)

        self.host = HostWidget(self.reposition, self)
        layout.addWidget(self.host, 1)

        self.placeholder = QLabel(
            "把 VSCode 窗口拖到这里\n或双击启动新实例", self.host
        )
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet("color: #6a6a6a; font-size: 13px;")

        self._update_header()

    # ---- 标题 / 序号 ----
    def set_index(self, index):
        self.index = index
        self.header.index = index
        self._update_header()

    def _update_header(self):
        if self.child_hwnd is None:
            self.header.title.setText(f"槽位 {self.index + 1}  （空）")
        else:
            title = win32_utils.get_window_title(self.child_hwnd)
            self.header.title.setText(f"槽位 {self.index + 1}  {title}")

    def _on_close_clicked(self):
        self.detach()

    # ---- 嵌入 / 释放 / 换位 ----
    def attach(self, hwnd):
        if self.child_hwnd is not None:
            self.detach()
        self.child_hwnd = hwnd
        parent_hwnd = int(self.host.winId())
        self.original_style = win32_utils.embed_window(hwnd, parent_hwnd)
        self.placeholder.hide()
        self._update_header()
        self.reposition()
        QTimer.singleShot(50, self.reposition)

    def detach(self):
        if self.child_hwnd is not None:
            win32_utils.release_window(self.child_hwnd, self.original_style)
        self.child_hwnd = None
        self.original_style = None
        self.placeholder.show()
        self._update_header()

    def clear_slot(self):
        """仅清空槽位记录（窗口已被关闭的情况），不再恢复窗口。"""
        self.child_hwnd = None
        self.original_style = None
        self.placeholder.show()
        self._update_header()

    def take(self):
        info = (self.child_hwnd, self.original_style)
        self.child_hwnd = None
        self.original_style = None
        self.placeholder.show()
        self._update_header()
        return info

    def give(self, info):
        hwnd, original_style = info
        self.child_hwnd = hwnd
        self.original_style = original_style
        if hwnd is not None:
            parent_hwnd = int(self.host.winId())
            win32_utils.embed_window(hwnd, parent_hwnd)
            self.placeholder.hide()
            self.reposition()
            QTimer.singleShot(50, self.reposition)
        else:
            self.placeholder.show()
        self._update_header()

    def reposition(self):
        self.placeholder.resize(self.host.size())
        if self.child_hwnd is None:
            return
        win32_utils.resize_embedded(
            self.child_hwnd, 0, 0, self.host.width(), self.host.height()
        )

    def set_drop_highlight(self, on):
        self.setStyleSheet(self.HOVER_STYLE if on else self.NORMAL_STYLE)

    # ---- 事件 ----
    def mouseDoubleClickEvent(self, event):
        if self.child_hwnd is None:
            self.requestLaunch.emit(self.index)
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().text().startswith("cell:"):
            self.set_drop_highlight(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.set_drop_highlight(False)

    def dropEvent(self, event):
        self.set_drop_highlight(False)
        text = event.mimeData().text()
        if text.startswith("cell:"):
            from_index = int(text.split(":")[1])
            if from_index != self.index:
                self.requestSwap.emit(from_index, self.index)
            event.acceptProposedAction()
