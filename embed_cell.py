# -*- coding: utf-8 -*-
"""Single workspace cell that hosts one external application window."""

from PySide6.QtCore import Qt, QMimeData, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import icons
import styles
import win32_utils
from config import font_size, icon_size
from window_manager import ManagedWindowBinding, WindowManager


class HostWidget(QWidget):
    """Native HWND host; resize and enforce share this widget's coordinates."""

    def __init__(self, on_resize, on_click, parent=None):
        super().__init__(parent)
        self._on_resize = on_resize
        self._on_click = on_click
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAutoFillBackground(True)
        self._bg = QColor(styles.HOST_BG)
        self.setStyleSheet(f"background:{styles.HOST_BG};")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._bg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_resize()

    def mousePressEvent(self, event):
        self._on_click()
        super().mousePressEvent(event)


class DragHeader(QWidget):
    """Cell header: drag to swap/release, right-click to release."""

    requestRelease = Signal(int)

    def __init__(self, index, cfg, parent=None):
        super().__init__(parent)
        self.index = index
        self.cfg = cfg
        self.active = False
        self.has_window = False
        self.setObjectName("dragHeader")
        self._press = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 0, 6, 0)
        layout.setSpacing(7)

        self.badge = QLabel(str(index + 1))
        self.badge.setObjectName("badge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.badge)

        self.drag_icon = QLabel()
        self.drag_icon.setObjectName("dragIcon")
        layout.addWidget(self.drag_icon)

        self.title = QLabel("（空）")
        self.title.setObjectName("cellTitle")
        layout.addWidget(self.title, 1)

        self.btn_close = QToolButton()
        self.btn_close.setObjectName("cellClose")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("释放为独立窗口")
        layout.addWidget(self.btn_close)

        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.apply_config()

    def apply_config(self):
        self.setFixedHeight(self.cfg["header_height"])
        badge_font = font_size(self.cfg, "badge")
        title_font = font_size(self.cfg, "cell_title")
        badge_size = max(14, badge_font + 8)
        self.badge.setFixedSize(badge_size, badge_size)

        drag_size = icon_size(self.cfg, "drag")
        close_size = icon_size(self.cfg, "close")
        pixmap = icons.make_pixmap("drag", "#7a87a8", drag_size)
        self.drag_icon.setPixmap(pixmap if pixmap is not None else QPixmap())
        self.btn_close.setIcon(
            icons.make_icon("close", "#cfcfe0", close_size)
        )
        self.btn_close.setIconSize(QSize(close_size, close_size))
        self.btn_close.setFixedSize(close_size + 8, close_size + 8)
        self._apply_qss(badge_font, title_font)

    def _apply_qss(self, badge_font, title_font):
        background = (
            styles.HEADER_ACTIVE if self.active else styles.HEADER_IDLE
        )
        self.setStyleSheet(
            f"""
            QWidget#dragHeader {{
                background:{background};
                border-top-left-radius:5px;
                border-top-right-radius:5px;
            }}
            QLabel#badge {{
                background:{styles.BADGE_BG};
                color:{styles.GOLD};
                border-radius:5px;
                font-size:{badge_font}px;
                font-weight:bold;
            }}
            QLabel#dragIcon {{
                background:transparent;
            }}
            QLabel#cellTitle {{
                background:transparent;
                color:#cfcfe0;
                font-size:{title_font}px;
            }}
            QToolButton#cellClose {{
                border:none;
                background:transparent;
                border-radius:4px;
            }}
            QToolButton#cellClose:hover {{
                background:#c4302b;
            }}
            """
        )

    def set_active(self, on):
        self.active = bool(on)
        self.apply_config()

    def set_has_window(self, on):
        self.has_window = bool(on)

    def set_number(self, number):
        self.badge.setText(str(number))

    def contextMenuEvent(self, event):
        if not self.has_window:
            return

        box = QMessageBox(self)
        box.setWindowTitle("弹出窗口")
        box.setText("是否将此窗口弹出为独立窗口？")
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        box.setEscapeButton(QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.requestRelease.emit(self.index)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        if (
            event.position().toPoint() - self._press
        ).manhattanLength() < 10:
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
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
            " " + self.title.text(),
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
        self.window_manager = WindowManager()
        self.binding: ManagedWindowBinding | None = None

        # Kept for compatibility with GridWindow/session code.
        self.child_hwnd = None
        self.original_style = None
        self._input_thread = 0

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
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setMinimumSize(46, 40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self.header = DragHeader(index, cfg, self)
        self.header.btn_close.clicked.connect(self._on_close_clicked)
        self.header.requestRelease.connect(self.requestRelease)
        layout.addWidget(self.header)

        self.host = HostWidget(self.reposition, self._focus_child, self)
        layout.addWidget(self.host, 1)

        self.placeholder = QLabel(
            "把窗口拖到这里\n或双击选择窗口嵌入",
            self.host,
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet(
            "color:#566080; font-size:13px;"
        )
        self._update_header()

    def apply_config(self):
        self.header.apply_config()

    def _sync_compatibility_fields(self):
        if self.binding is None:
            self.child_hwnd = None
            self.original_style = None
            self._input_thread = 0
        else:
            self.child_hwnd = self.binding.hwnd
            self.original_style = self.binding.original_style
            self._input_thread = self.binding.input_thread

    def _focus_child(self):
        self.window_manager.focus(self.binding)

    def set_index(self, index):
        self.index = index
        self.header.index = index
        self.header.set_number(index + 1)
        if self.binding is not None:
            self.binding.pane_index = index
        self._update_header()

    def _update_header(self):
        if self.child_hwnd is None:
            self.header.title.setText("（空）")
            self.header.set_active(False)
            self.header.set_has_window(False)
        else:
            self.header.title.setText(
                win32_utils.get_window_title(self.child_hwnd)
            )
            self.header.set_active(True)
            self.header.set_has_window(True)

    def _on_close_clicked(self):
        self.detach()

    def attach(self, hwnd):
        if self.binding is not None:
            self.detach()

        self.binding = self.window_manager.attach(
            hwnd,
            int(self.host.winId()),
            self.index,
        )
        self._sync_compatibility_fields()
        if self.binding is None:
            self.placeholder.show()
            self._update_header()
            return False

        self.placeholder.hide()
        self._update_header()
        self.reposition()
        QTimer.singleShot(50, self.reposition)
        QTimer.singleShot(80, self._focus_child)
        return True

    def detach(self):
        if self.binding is not None:
            self.window_manager.detach(self.binding)

        self.binding = None
        self._sync_compatibility_fields()
        self.placeholder.show()
        self._update_header()

    def clear_slot(self):
        if self.binding is not None:
            self.window_manager.forget(self.binding)

        self.binding = None
        self._sync_compatibility_fields()
        self.placeholder.show()
        self._update_header()

    def take(self):
        binding = self.window_manager.take(self.binding)
        self.binding = None
        self._sync_compatibility_fields()
        self.placeholder.show()
        self._update_header()
        return binding

    def give(self, binding):
        self.binding = self.window_manager.adopt(
            binding,
            int(self.host.winId()),
            self.index,
        )
        self._sync_compatibility_fields()

        if self.binding is None:
            self.placeholder.show()
        else:
            self.placeholder.hide()
            self.reposition()
            QTimer.singleShot(50, self.reposition)
            QTimer.singleShot(80, self._focus_child)

        self._update_header()

    def reposition(self):
        self.placeholder.resize(self.host.size())
        self.window_manager.resize(
            self.binding,
            self.host.width(),
            self.host.height(),
        )

    def enforce(self):
        if self.binding is None:
            return

        alive = self.window_manager.enforce(
            self.binding,
            int(self.host.winId()),
            self.host.width(),
            self.host.height(),
        )
        if not alive:
            self.binding = None
            self._sync_compatibility_fields()
            self.placeholder.show()
            self._update_header()
        else:
            self._sync_compatibility_fields()

    def set_drop_highlight(self, on):
        self.setStyleSheet(self._hover if on else self._normal)

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
            from_index = int(text.split(":", 1)[1])
            if from_index != self.index:
                self.requestSwap.emit(from_index, self.index)
            event.acceptProposedAction()
