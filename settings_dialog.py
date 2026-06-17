# -*- coding: utf-8 -*-
"""设置 / 窗口管理对话框：按序号列出已嵌入窗口，处理卡死窗口。继承全局 STYLE。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import icons
import styles
import win32_utils


class SettingsDialog(QDialog):
    def __init__(self, grid_window):
        super().__init__(grid_window)
        self.gw = grid_window
        self.setWindowTitle("设置 / 窗口管理")
        self.resize(540, 440)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        tip = QLabel(
            "按序号列出已嵌入的窗口。某个窗口卡死时，点对应行的按钮：\n"
            "释放 = 变回独立窗口    关闭 = 正常关闭    强制关闭 = 只强行关这一个\n"
            "注意：某些应用多窗口共用一个进程，不能用杀进程方式只结束单个窗口。"
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#9aa3c0; font-size:12px;")
        root.addWidget(tip)

        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 4, 0, 0)
        self.list_layout.setSpacing(6)
        root.addWidget(self.list_host)

        root.addStretch(1)

        bottom = QHBoxLayout()
        btn_refresh = QPushButton(" 刷新")
        btn_refresh.setIcon(icons.make_icon("refresh"))
        btn_refresh.clicked.connect(self.refresh)
        bottom.addWidget(btn_refresh)
        bottom.addStretch(1)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self.refresh()

    def refresh(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        embedded = [c for c in self.gw.cells if c.child_hwnd]
        if not embedded:
            empty = QLabel("当前没有已嵌入的窗口。")
            empty.setStyleSheet("color:#6f7aa0;")
            self.list_layout.addWidget(empty)
            return

        for cell in embedded:
            row = QWidget()
            row.setStyleSheet("background:#16213e; border-radius:5px;")
            h = QHBoxLayout(row)
            h.setContentsMargins(8, 6, 8, 6)
            h.setSpacing(8)

            num = QLabel(str(cell.index + 1))
            num.setFixedSize(22, 22)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet(
                f"color:{styles.GOLD}; background:{styles.BADGE_BG};"
                " border-radius:11px; font-weight:bold;"
            )
            h.addWidget(num)

            title = QLabel(win32_utils.get_window_title(cell.child_hwnd))
            title.setStyleSheet("color:#cfcfe0;")
            h.addWidget(title, 1)

            b_rel = QPushButton(" 释放")
            b_rel.setIcon(icons.make_icon("sign-out"))
            b_rel.clicked.connect(lambda _, i=cell.index: self._do(i, "release"))
            h.addWidget(b_rel)

            b_close = QPushButton(" 关闭")
            b_close.setIcon(icons.make_icon("close"))
            b_close.clicked.connect(lambda _, i=cell.index: self._do(i, "close"))
            h.addWidget(b_close)

            b_force = QPushButton(" 强制关闭")
            b_force.setIcon(icons.make_icon("warning", "#e0833f"))
            b_force.clicked.connect(lambda _, i=cell.index: self._do(i, "force"))
            h.addWidget(b_force)

            self.list_layout.addWidget(row)

    def _do(self, index, action):
        if action == "release":
            self.gw.release_cell(index)
        elif action == "close":
            self.gw.close_cell(index)
        elif action == "force":
            r = QMessageBox.question(
                self,
                "确认强制关闭",
                "将强行关闭这一个窗口，未保存内容可能丢失。是否继续？",
            )
            if r != QMessageBox.StandardButton.Yes:
                return
            self.gw.force_close_cell(index)
        self.refresh()
