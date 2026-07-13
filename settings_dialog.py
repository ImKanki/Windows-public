# -*- coding: utf-8 -*-
"""设置 / 窗口管理对话框：分割方向、联动方式、调整开关 + 按序号管理已嵌入窗口。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
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
        self.resize(560, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ---- 拖拽 / 分割 ----
        split_box = QGroupBox("拖拽 / 分割")
        sf = QFormLayout(split_box)

        self.resize_chk = QCheckBox("允许拖拽分隔条调整窗口大小")
        self.resize_chk.setChecked(self.gw.cfg.get("resize_enabled", True))
        self.resize_chk.toggled.connect(self._toggle_resize)
        sf.addRow(self.resize_chk)

        self.primary_combo = QComboBox()
        self.primary_combo.addItem("先分行（左右每行可独立调整）", "rows")
        self.primary_combo.addItem("先分列（上下每列可独立调整）", "cols")
        cur = self.gw.cfg.get("split_primary", "rows")
        self.primary_combo.setCurrentIndex(1 if cur == "cols" else 0)
        self.primary_combo.currentIndexChanged.connect(self._change_primary)
        sf.addRow("主分割方向", self.primary_combo)

        self.sync_chk = QCheckBox()
        self.sync_chk.setChecked(self.gw.cfg.get("sync_inner", False))
        self.sync_chk.toggled.connect(self._toggle_sync)
        sf.addRow("独立方向联动", self.sync_chk)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("增量（其他同向移动相同距离，不复位）", "delta")
        self.mode_combo.addItem("复位（其他对齐到相同位置）", "reset")
        self.mode_combo.setCurrentIndex(
            1 if self.gw.cfg.get("sync_mode", "delta") == "reset" else 0
        )
        self.mode_combo.currentIndexChanged.connect(self._change_mode)
        sf.addRow("联动方式", self.mode_combo)

        root.addWidget(split_box)
        self._update_sync_label()

        tip = QLabel(
            "说明：嵌套分隔条只能让一个方向“每行/每列独立”，另一个方向是贯穿联动。\n"
            "想上下独立就选“先分列”，想左右独立就选“先分行”。\n"
            "对独立的那个方向可开启联动，并选增量或复位。\n\n"
            "下面按序号管理已嵌入窗口：释放=变回独立窗口，关闭=正常关闭，"
            "强制关闭=只强行关这一个。"
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

    def _update_sync_label(self):
        primary = self.gw.cfg.get("split_primary", "rows")
        # 独立方向是内层：rows→列(左右)，cols→行(上下)
        if primary == "cols":
            self.sync_chk.setText("上下联动（拖一列的行边界，其他列跟随）")
        else:
            self.sync_chk.setText("左右联动（拖一行的列边界，其他行跟随）")
        self.mode_combo.setEnabled(self.sync_chk.isChecked())

    def _toggle_resize(self, on):
        self.gw.cfg["resize_enabled"] = bool(on)
        self.gw._apply_resize_enabled()

    def _change_primary(self, _idx):
        self.gw.cfg["split_primary"] = self.primary_combo.currentData()
        self._update_sync_label()
        self.gw.rebuild_layout()

    def _toggle_sync(self, on):
        self.gw.cfg["sync_inner"] = bool(on)
        self.mode_combo.setEnabled(on)

    def _change_mode(self, _idx):
        self.gw.cfg["sync_mode"] = self.mode_combo.currentData()

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
