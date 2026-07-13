# -*- coding: utf-8 -*-
"""A modern workspace cell hosting one external application window."""

from PySide6.QtCore import QMimeData, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
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


def _refresh_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class HostWidget(QWidget):
    """Native HWND host. All sizing continues to use this single coordinate source."""

    def __init__(self, on_resize, on_click, parent=None):
        super().__init__(parent)
        self._on_resize = on_resize
        self._on_click = on_click
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(True)
        self._background = QColor(styles.HOST_BG)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._background)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_resize()

    def mousePressEvent(self, event):
        self._on_click()
        super().mousePressEvent(event)


class EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        layout.addStretch(1)

        self.icon = QLabel("+")
        self.icon.setObjectName("emptyIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon)

        title = QLabel("添加应用窗口")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("拖入窗口标题栏，或双击选择")
        hint.setObjectName("emptyHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch(1)


class DragHeader(QWidget):
    """Cell title bar with drag-to-swap and a compact action menu."""

    requestRelease = Signal(int)
    requestClose = Signal(int)
    requestForceClose = Signal(int)

    def __init__(self, index, cfg, parent=None):
        super().__init__(parent)
        self.index = index
        self.cfg = cfg
        self.active = False
        self.has_window = False
        self._press = None
        self.setObjectName("dragHeader")
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 0, 7, 0)
        layout.setSpacing(8)

        self.badge = QLabel(str(index + 1))
        self.badge.setObjectName("windowBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.badge)

        self.window_icon = QLabel()
        self.window_icon.setObjectName("windowGlyph")
        self.window_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.window_icon)

        self.title = QLabel("空窗口")
        self.title.setObjectName("windowTitle")
        self.title.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.title, 1)

        self.state_dot = QLabel("●")
        self.state_dot.setObjectName("windowState")
        self.state_dot.setToolTip("窗口已连接")
        layout.addWidget(self.state_dot)

        self.btn_more = QToolButton()
        self.btn_more.setObjectName("cellMenuButton")
        self.btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_more.setToolTip("窗口操作")
        self.btn_more.clicked.connect(self._show_menu)
        layout.addWidget(self.btn_more)

        self.apply_config()
        self.set_has_window(False)

    def apply_config(self):
        self.setFixedHeight(self.cfg["header_height"])

        badge_font = font_size(self.cfg, "badge")
        badge_size = max(16, badge_font + 9)
        self.badge.setFixedSize(badge_size, badge_size)

        icon_px = max(15, icon_size(self.cfg, "drag"))
        pixmap = icons.make_pixmap("window", "#7F8998", icon_px)
        self.window_icon.setPixmap(
            pixmap if pixmap is not None else QPixmap()
        )
        self.window_icon.setFixedSize(icon_px, icon_px)

        self.btn_more.setIcon(
            icons.make_icon("more", "#AAB3C2", 18)
        )
        self.btn_more.setIconSize(QSize(18, 18))

    def set_active(self, on):
        self.active = bool(on)
        self.setProperty("active", self.active)
        _refresh_style(self)

    def set_has_window(self, on):
        self.has_window = bool(on)
        self.btn_more.setVisible(self.has_window)
        self.state_dot.setVisible(self.has_window)

    def set_number(self, number):
        self.badge.setText(str(number))

    def _show_menu(self):
        if not self.has_window:
            return

        menu = QMenu(self)

        release_action = QAction(
            icons.make_icon("sign-out", "#AAB3C2", 16),
            "释放为独立窗口",
            menu,
        )
        release_action.triggered.connect(
            lambda: self.requestRelease.emit(self.index)
        )
        menu.addAction(release_action)

        menu.addSeparator()

        close_action = QAction(
            icons.make_icon("close", "#AAB3C2", 16),
            "正常关闭窗口",
            menu,
        )
        close_action.triggered.connect(
            lambda: self.requestClose.emit(self.index)
        )
        menu.addAction(close_action)

        force_action = QAction(
            icons.make_icon("warning", styles.DANGER, 16),
            "强制关闭窗口",
            menu,
        )
        force_action.triggered.connect(
            lambda: self.requestForceClose.emit(self.index)
        )
        menu.addAction(force_action)

        menu.exec(
            self.btn_more.mapToGlobal(
                self.btn_more.rect().bottomRight()
            )
        )

    def contextMenuEvent(self, event):
        self._show_menu()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is None:
            return

        distance = (
            event.position().toPoint() - self._press
        ).manhattanLength()
        if distance < 10:
            return

        if not self.has_window:
            self._press = None
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"cell:{self.index}")
        drag.setMimeData(mime)

        pixmap = QPixmap(max(240, self.width()), self.height())
        pixmap.fill(QColor(styles.SURFACE_2))
        painter = QPainter(pixmap)
        painter.setPen(QColor(styles.TEXT))
        painter.drawText(
            pixmap.rect().adjusted(12, 0, -12, 0),
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
            self.title.text(),
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
    requestClose = Signal(int)
    requestForceClose = Signal(int)

    def __init__(self, index, cfg, parent=None):
        super().__init__(parent)
        self.index = index
        self.cfg = cfg
        self.window_manager = WindowManager()
        self.binding: ManagedWindowBinding | None = None

        # Compatibility fields used by GridWindow/session.
        self.child_hwnd = None
        self.original_style = None
        self._input_thread = 0

        self.setAcceptDrops(True)
        self.setObjectName("embedCell")
        self.setProperty("occupied", False)
        self.setProperty("dropActive", False)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setMinimumSize(72, 60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        self.header = DragHeader(index, cfg, self)
        self.header.requestRelease.connect(self.requestRelease)
        self.header.requestClose.connect(self.requestClose)
        self.header.requestForceClose.connect(self.requestForceClose)
        layout.addWidget(self.header)

        self.host = HostWidget(
            self.reposition,
            self._focus_child,
            self,
        )
        layout.addWidget(self.host, 1)

        self.placeholder = EmptyState(self.host)
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

    def _refresh_cell_state(self):
        occupied = self.child_hwnd is not None
        self.setProperty("occupied", occupied)
        _refresh_style(self)

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
            self.header.title.setText("空窗口")
            self.header.set_active(False)
            self.header.set_has_window(False)
        else:
            title = win32_utils.get_window_title(self.child_hwnd)
            self.header.title.setText(title or "应用窗口")
            self.header.set_active(True)
            self.header.set_has_window(True)
        self._refresh_cell_state()

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
        self.placeholder.setGeometry(self.host.rect())
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
        self.setProperty("dropActive", bool(on))
        _refresh_style(self)

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
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.set_drop_highlight(False)
        text = event.mimeData().text()
        if text.startswith("cell:"):
            from_index = int(text.split(":", 1)[1])
            if from_index != self.index:
                self.requestSwap.emit(from_index, self.index)
            event.acceptProposedAction()
