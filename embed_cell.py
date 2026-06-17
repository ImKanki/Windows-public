# -*- coding: utf-8 -*-
"""单个网格槽位：承载嵌入的外部窗口，支持拖出释放、拖入换位、巡检。"""
from PySide6.QtCore import Qt, QMimeData, QSize, QTimer, Signal
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
import styles
import win32_utils
from config import font_size, icon_size


class HostWidget(QWidget):
    """嵌入窗口的承载区。尺寸一变就回调，确保嵌入窗口实时填满。"""

    def __init__(self, on_resize, parent=None):
        super().__init__(parent)
        self._on_resize = on_resize
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setStyleSheet(f"background:{styles.HOST_BG};")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_resize()


class DragHeader(QWidget):
    """槽位标题栏：序号徽标 + 拖动图标 + 标题，右侧关闭按钮。

    拖到另一个槽位松手 -> 换位；拖到容器外松手 -> 释放为独立窗口。
    """

    requestRelease = Signal(int)

    def __init__(self, index, cfg, parent=None):
        super().__init__(parent)
        self.index = index
        self.cfg = cfg
        self.active = False
        self.has_window = False
        self.setObjectName("dragHeader")
        self._press = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(7, 0, 6, 0)
        lay.setSpacing(7)

        self.badge = QLabel(str(index + 1))
        self.badge.setObjectName("badge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.badge)

        self.drag_icon = QLabel()
        self.drag_icon.setObjectName("dragIcon")
        lay.addWidget(self.drag_icon)

        self.title = QLabel("（空）")
        self.title.setObjectName("cellTitle")
        lay.addWidget(self.title, 1)

        self.btn_close = QToolButton()
        self.btn_close.setObjectName("cellClose")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("释放为独立窗口")
        lay.addWidget(self.btn_close)

        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.apply_config()

    def apply_config(self):
        self.setFixedHeight(self.cfg["header_height"])
        bf = font_size(self.cfg, "badge")
        tf = font_size(self.cfg, "cell_title")
        bs = max(14, bf + 8)
        self.badge.setFixedSize(bs, bs)

        di = icon_size(self.cfg, "drag")
        ci = icon_size(self.cfg, "close")
        pm = icons.make_pixmap("drag", "#7a87a8", di)
        self.drag_icon.setPixmap(pm if pm is not None else QPixmap())
        self.btn_close.setIcon(icons.make_icon("close", "#cfcfe0", ci))
        self.btn_close.setIconSize(QSize(ci, ci))
        self.btn_close.setFixedSize(ci + 8, ci + 8)
        self._apply_qss(bf, tf)

    def _apply_qss(self, bf, tf):
        bg = styles.HEADER_ACTIVE if self.active else styles.HEADER_IDLE
        self.setStyleSheet(
            f"""
            QWidget#dragHeader {{ background:{bg};
                border-top-left-radius:5px; border-top-right-radius:5px; }}
            QLabel#badge {{ background:{styles.BADGE_BG}; color:{styles.GOLD};
                border-radius:5px; font-size:{bf}px; font-weight:bold; }}
            QLabel#dragIcon {{ background:transparent; }}
            QLabel#cellTitle {{ background:transparent; color:#cfcfe0;
                font-size:{tf}px; }}
            QToolButton#cellClose {{ border:none; background:transparent;
                border-radius:4px; }}
            QToolButton#cellClose:hover {{ background:#c4302b; }}
            """
        )

    def set_active(self, on):
        self.active = on
        self.apply_config()

    def set_has_window(self, on):
        self.has_window = on

    def set_number(self, n):
        self.badge.setText(str(n))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        if (event.position().toPoint() - self._press).manhattanLength() < 10:
            return
        if not self.has_window:
            self._press = None
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"cell:{self.index}")
        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        pixmap.fill(QColor(styles.ACCENT))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#0e1525"))
        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "   " + self.title.text(),
        )
        painter.end()
        drag.setPixmap(pixmap)

        self._press = None
        result = drag.exec(Qt.DropAction.MoveAction)
        if result == Qt.DropAction.IgnoreAction:
            self.requestRelease.emit(self.index)


class EmbedCell(QFrame):
    requestSwap = Signal(int, int)
    requestLaunch = Signal(int)
    requestRelease = Signal(int)

    def __init__(self, index, cfg, parent=None):
        super().__init__(parent)
        self.index = index
        self.cfg = cfg
        self.child_hwnd = None
        self.original_style = None
        self.setAcceptDrops(True)
        self.setObjectName("embedCell")
        self._normal = (
            f"#embedCell {{ border:1px solid {styles.CELL_BORDER};"
            f" border-radius:6px; background:{styles.CELL_BG}; }}"
        )
        self._hover = (
            f"#embedCell {{ border:2px solid {styles.ACCENT};"
            f" border-radius:6px; background:{styles.DROP_BG}; }}"
        )
        self.setStyleSheet(self._normal)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(140, 100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self.header = DragHeader(index, cfg, self)
        self.header.btn_close.clicked.connect(self._on_close_clicked)
        self.header.requestRelease.connect(self.requestRelease)
        layout.addWidget(self.header)

        self.host = HostWidget(self.reposition, self)
        layout.addWidget(self.host, 1)

        self.placeholder = QLabel("把外部窗口拖到这里\n或双击选择窗口", self.host)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color:#566080; font-size:13px;")

        self._update_header()

    # ---- 配置 ----
    def apply_config(self):
        self.header.apply_config()

    # ---- 标题 / 序号 ----
    def set_index(self, index):
        self.index = index
        self.header.index = index
        self.header.set_number(index + 1)
        self._update_header()

    def _update_header(self):
        if self.child_hwnd is None:
            self.header.title.setText("（空）")
            self.header.set_active(False)
            self.header.set_has_window(False)
        else:
            self.header.title.setText(win32_utils.get_window_title(self.child_hwnd))
            self.header.set_active(True)
            self.header.set_has_window(True)

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

    def enforce(self):
        if self.child_hwnd is None:
            return
        parent_hwnd = int(self.host.winId())
        alive = win32_utils.enforce_embed(
            self.child_hwnd, parent_hwnd, self.host.width(), self.host.height()
        )
        if not alive:
            self.clear_slot()

    def set_drop_highlight(self, on):
        self.setStyleSheet(self._hover if on else self._normal)

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
