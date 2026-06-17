# -*- coding: utf-8 -*-
"""窗口选择对话框：列出当前所有可嵌入的窗口，供用户选择嵌入。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

import icons
import win32_utils


class WindowPicker(QDialog):
    """列出可嵌入窗口。multi=True 可多选，multi=False 单选。"""

    def __init__(self, exclude=(), multi=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择要嵌入的窗口")
        self.resize(520, 460)
        self._multi = multi
        self._exclude = {int(h) for h in exclude}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        tip = QLabel(
            "从当前打开的窗口中选择嵌入网格。"
            + ("可多选，确定后依次填入空槽。" if multi else "双击或选中后点嵌入。")
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#9aa3c0; font-size:12px;")
        root.addWidget(tip)

        self.list = QListWidget()
        self.list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
            if multi
            else QListWidget.SelectionMode.SingleSelection
        )
        self.list.itemDoubleClicked.connect(self._on_double)
        root.addWidget(self.list, 1)

        bottom = QHBoxLayout()
        btn_refresh = QPushButton(" 刷新")
        btn_refresh.setIcon(icons.make_icon("refresh"))
        btn_refresh.clicked.connect(self.refresh)
        bottom.addWidget(btn_refresh)
        bottom.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)
        btn_ok = QPushButton("嵌入")
        btn_ok.setObjectName("primary")
        btn_ok.clicked.connect(self.accept)
        bottom.addWidget(btn_ok)
        root.addLayout(bottom)

        self.refresh()

    def refresh(self):
        self.list.clear()
        found = False
        for hwnd, title in win32_utils.find_embeddable_windows():
            if int(hwnd) in self._exclude:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, hwnd)
            self.list.addItem(item)
            found = True
        if not found:
            placeholder = QListWidgetItem("（没有可嵌入的窗口）")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(placeholder)

    def _on_double(self, item):
        if item.data(Qt.ItemDataRole.UserRole):
            self.accept()

    def selected_hwnds(self):
        result = []
        for item in self.list.selectedItems():
            hwnd = item.data(Qt.ItemDataRole.UserRole)
            if hwnd:
                result.append(hwnd)
        return result
