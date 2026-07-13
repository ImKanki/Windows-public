# -*- coding: utf-8 -*-
"""Modern settings and embedded-window management dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import icons
import styles
import win32_utils
from version import __version__


class SettingsCard(QFrame):
    def __init__(self, title, description="", parent=None):
        super().__init__(parent)
        self.setObjectName("settingsCard")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 15, 16, 16)
        root.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        root.addWidget(title_label)

        if description:
            description_label = QLabel(description)
            description_label.setObjectName("cardDescription")
            description_label.setWordWrap(True)
            root.addWidget(description_label)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        root.addLayout(self.body)


def _setting_row(title, description, control):
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 2, 0, 2)
    layout.setSpacing(16)

    text_host = QWidget()
    text_layout = QVBoxLayout(text_host)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(3)

    title_label = QLabel(title)
    title_label.setStyleSheet(
        "color:#E2E6ED; font-weight:550;"
    )
    text_layout.addWidget(title_label)

    description_label = QLabel(description)
    description_label.setWordWrap(True)
    description_label.setStyleSheet(
        "color:#778190; font-size:11px;"
    )
    text_layout.addWidget(description_label)

    layout.addWidget(text_host, 1)
    layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
    return row


class SettingsDialog(QDialog):
    PAGE_INFO = [
        ("工作区", "布局方向、尺寸调整和分隔条行为"),
        ("窗口行为", "联动规则和窗口管理方式"),
        ("已嵌入窗口", "释放、关闭或强制关闭当前窗口"),
        ("关于", "版本与项目说明"),
    ]

    def __init__(self, grid_window):
        super().__init__(grid_window)
        self.gw = grid_window
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Workspace 设置")
        self.resize(860, 610)
        self.setMinimumSize(760, 540)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)

        self.nav.setCurrentRow(0)
        self.refresh()

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(196)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 14, 16)
        layout.setSpacing(10)

        title = QLabel("设置")
        title.setObjectName("settingsTitle")
        layout.addWidget(title)

        subtitle = QLabel("Workspace preferences")
        subtitle.setObjectName("settingsSubtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        for page_title, _ in self.PAGE_INFO:
            item = QListWidgetItem(page_title)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._change_page)
        layout.addWidget(self.nav, 1)

        version = QLabel(f"Version {__version__}")
        version.setObjectName("settingsSubtitle")
        layout.addWidget(version)

        return sidebar

    def _build_content(self):
        content = QFrame()
        content.setObjectName("settingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 22, 26, 18)
        layout.setSpacing(14)

        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        layout.addWidget(self.page_title)

        self.page_description = QLabel()
        self.page_description.setObjectName("pageDescription")
        layout.addWidget(self.page_description)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._workspace_page())
        self.stack.addWidget(self._behavior_page())
        self.stack.addWidget(self._windows_page())
        self.stack.addWidget(self._about_page())
        layout.addWidget(self.stack, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        close_button = QPushButton("完成")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

        return content

    def _page_scroll(self, content_widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidget(content_widget)
        return scroll

    def _workspace_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 4, 4)
        layout.setSpacing(12)

        layout_card = SettingsCard(
            "布局结构",
            "选择主分割方向。该选项会重新构建当前网格，但不会关闭已嵌入窗口。",
        )

        self.primary_combo = QComboBox()
        self.primary_combo.setMinimumWidth(260)
        self.primary_combo.addItem(
            "先分行 · 每行可独立调整列宽",
            "rows",
        )
        self.primary_combo.addItem(
            "先分列 · 每列可独立调整行高",
            "cols",
        )
        current = self.gw.cfg.get("split_primary", "rows")
        self.primary_combo.setCurrentIndex(
            1 if current == "cols" else 0
        )
        self.primary_combo.currentIndexChanged.connect(
            self._change_primary
        )
        layout_card.body.addWidget(
            _setting_row(
                "主分割方向",
                "决定哪一个方向贯穿整个工作区。",
                self.primary_combo,
            )
        )
        layout.addWidget(layout_card)

        resize_card = SettingsCard(
            "尺寸调整",
            "控制工作区内分隔条是否允许拖动。",
        )
        self.resize_chk = QCheckBox()
        self.resize_chk.setChecked(
            self.gw.cfg.get("resize_enabled", True)
        )
        self.resize_chk.toggled.connect(self._toggle_resize)
        resize_card.body.addWidget(
            _setting_row(
                "允许调整窗口大小",
                "关闭后仍保留当前比例，但分隔条不再响应拖动。",
                self.resize_chk,
            )
        )
        layout.addWidget(resize_card)
        layout.addStretch(1)
        return self._page_scroll(page)

    def _behavior_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 4, 4)
        layout.setSpacing(12)

        sync_card = SettingsCard(
            "分隔条联动",
            "让各行或各列中的独立分隔条保持同步。",
        )

        self.sync_chk = QCheckBox()
        self.sync_chk.setChecked(
            self.gw.cfg.get("sync_inner", False)
        )
        self.sync_chk.toggled.connect(self._toggle_sync)
        sync_card.body.addWidget(
            _setting_row(
                "启用独立方向联动",
                "拖动一组边界时，其他同方向边界一起响应。",
                self.sync_chk,
            )
        )

        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(260)
        self.mode_combo.addItem(
            "增量 · 保留各组原有比例",
            "delta",
        )
        self.mode_combo.addItem(
            "对齐 · 统一到相同位置",
            "reset",
        )
        self.mode_combo.setCurrentIndex(
            1
            if self.gw.cfg.get("sync_mode", "delta") == "reset"
            else 0
        )
        self.mode_combo.currentIndexChanged.connect(
            self._change_mode
        )
        sync_card.body.addWidget(
            _setting_row(
                "联动方式",
                "增量只同步移动距离；对齐会让各组位置完全一致。",
                self.mode_combo,
            )
        )
        layout.addWidget(sync_card)

        explanation = SettingsCard(
            "使用建议",
            "需要左右区域各自独立时选择“先分行”；需要上下区域各自独立时选择“先分列”。"
            " 将分隔条拖到边缘时，面板仍会按照当前吸附阈值折叠。",
        )
        layout.addWidget(explanation)
        layout.addStretch(1)

        self._update_sync_state()
        return self._page_scroll(page)

    def _windows_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 4, 4)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        info = QLabel("仅显示当前仍然连接的窗口")
        info.setObjectName("cardDescription")
        toolbar.addWidget(info)
        toolbar.addStretch(1)

        refresh_button = QPushButton("刷新")
        refresh_button.setObjectName("textButton")
        refresh_button.setIcon(
            icons.make_icon("refresh", "#AAB3C2", 16)
        )
        refresh_button.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_button)
        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)

        scroll.setWidget(self.list_host)
        layout.addWidget(scroll, 1)
        return page

    def _about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 4, 4)
        layout.setSpacing(12)

        card = SettingsCard(
            "Workspace",
            "将多个开发应用固定在一个可调工作区内。",
        )

        hero = QHBoxLayout()
        mark = QLabel("W")
        mark.setObjectName("aboutMark")
        mark.setFixedSize(48, 48)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero.addWidget(mark)

        text = QVBoxLayout()
        product = QLabel("Window Grid Workspace")
        product.setStyleSheet(
            "color:#F3F5F8; font-size:16px; font-weight:650;"
        )
        text.addWidget(product)
        version = QLabel(f"Version {__version__}")
        version.setObjectName("cardDescription")
        text.addWidget(version)
        hero.addLayout(text, 1)

        card.body.addLayout(hero)

        note = QLabel(
            "本版本专注于主界面、窗口卡片和设置面板的视觉重构。"
            " 外部窗口的嵌入、缩放、会话和坐标逻辑保持原有实现。"
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "color:#8C95A4; line-height:1.45;"
        )
        card.body.addWidget(note)

        layout.addWidget(card)
        layout.addStretch(1)
        return self._page_scroll(page)

    def _change_page(self, index):
        if not 0 <= index < len(self.PAGE_INFO):
            return
        title, description = self.PAGE_INFO[index]
        self.page_title.setText(title)
        self.page_description.setText(description)
        self.stack.setCurrentIndex(index)
        if index == 2:
            self.refresh()

    def _update_sync_state(self):
        if not hasattr(self, "sync_chk"):
            return
        self.mode_combo.setEnabled(self.sync_chk.isChecked())

    def _toggle_resize(self, on):
        self.gw.cfg["resize_enabled"] = bool(on)
        self.gw._apply_resize_enabled()

    def _change_primary(self, _index):
        self.gw.cfg["split_primary"] = (
            self.primary_combo.currentData()
        )
        self.gw.rebuild_layout()

    def _toggle_sync(self, on):
        self.gw.cfg["sync_inner"] = bool(on)
        self._update_sync_state()

    def _change_mode(self, _index):
        self.gw.cfg["sync_mode"] = self.mode_combo.currentData()

    def refresh(self):
        if not hasattr(self, "list_layout"):
            return

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        embedded = [
            cell for cell in self.gw.cells if cell.child_hwnd
        ]

        if not embedded:
            empty = SettingsCard(
                "没有已嵌入窗口",
                "从主界面选择“添加窗口”，或把应用标题栏拖入空窗口。",
            )
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch(1)
            return

        for cell in embedded:
            row = QFrame()
            row.setObjectName("windowRow")

            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 10, 10)
            layout.setSpacing(10)

            number = QLabel(str(cell.index + 1))
            number.setObjectName("windowBadge")
            number.setFixedSize(24, 24)
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(number)

            text_host = QWidget()
            text_layout = QVBoxLayout(text_host)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)

            title = QLabel(
                win32_utils.get_window_title(cell.child_hwnd)
                or "应用窗口"
            )
            title.setStyleSheet(
                "color:#E1E5EC; font-weight:550;"
            )
            text_layout.addWidget(title)

            path = win32_utils.get_window_exe(cell.child_hwnd) or ""
            path_label = QLabel(path)
            path_label.setObjectName("cardDescription")
            path_label.setToolTip(path)
            text_layout.addWidget(path_label)

            layout.addWidget(text_host, 1)

            release_button = QPushButton("释放")
            release_button.setObjectName("textButton")
            release_button.clicked.connect(
                lambda _, i=cell.index: self._do(i, "release")
            )
            layout.addWidget(release_button)

            close_button = QPushButton("关闭")
            close_button.setObjectName("textButton")
            close_button.clicked.connect(
                lambda _, i=cell.index: self._do(i, "close")
            )
            layout.addWidget(close_button)

            force_button = QPushButton("强制关闭")
            force_button.setObjectName("dangerButton")
            force_button.clicked.connect(
                lambda _, i=cell.index: self._do(i, "force")
            )
            layout.addWidget(force_button)

            self.list_layout.addWidget(row)

        self.list_layout.addStretch(1)

    def _do(self, index, action):
        if action == "release":
            self.gw.release_cell(index)
        elif action == "close":
            self.gw.close_cell(index)
        elif action == "force":
            result = QMessageBox.question(
                self,
                "确认强制关闭",
                "未保存内容可能丢失。确定强制关闭这个窗口吗？",
            )
            if result != QMessageBox.StandardButton.Yes:
                return
            self.gw.force_close_cell(index)

        self.refresh()
