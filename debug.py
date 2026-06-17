# -*- coding: utf-8 -*-
"""调试工具：停靠面板实时调字体/图标/尺寸/颜色/行为，并把配置保存回 config.py。"""
import json
import re
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import config
import win32_utils
from grid_window import GRID_PRESETS, GridWindow
from styles import STYLE

FONT_LABELS = {
    "app_title": "工具栏标题",
    "button": "按钮 / 下拉文字",
    "cell_title": "槽位标题",
    "hint": "提示文字",
    "badge": "序号徽标",
}

ICON_LABELS = {
    "toolbar": "工具栏按钮图标",
    "app_icon": "工具栏标题图标",
    "close": "槽位关闭按钮",
    "drag": "槽位拖动手柄",
}

# 颜色项：key -> 显示名
COLOR_LABELS = {
    "logo_grad_start": "Logo 矩形·渐变起",
    "logo_grad_end": "Logo 矩形·渐变止",
    "logo_text": "Logo 文字",
    "logo_icon": "Logo 图标",
    "toolbar_bg": "工具栏背景",
    "toolbar_border": "工具栏边框 / 分隔线",
    "btn_bg": "普通按钮背景",
    "btn_hover": "普通按钮悬停",
    "btn_primary": "主按钮背景",
    "btn_primary_hover": "主按钮悬停",
    "btn_icon": "普通按钮图标",
    "btn_primary_icon": "主按钮图标",
}


class ColorButton(QPushButton):
    """显示当前颜色的小方块按钮，点击弹取色盘。"""

    def __init__(self, value, on_pick):
        super().__init__()
        self._value = value
        self._on_pick = on_pick
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self):
        # 用文字显示色值，背景填该色，自动选黑/白前景
        c = QColor(self._value)
        fg = "#000000" if c.lightnessF() > 0.6 else "#ffffff"
        self.setText(self._value)
        self.setStyleSheet(
            f"QPushButton {{ background:{self._value}; color:{fg};"
            " border:1px solid #243056; border-radius:4px; font-size:12px; }}"
        )

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._value), self, "选择颜色")
        if c.isValid():
            self._value = c.name()
            self._refresh()
            self._on_pick(self._value)


class DebugPanel(QDockWidget):
    def __init__(self, win):
        super().__init__("调试工具")
        self.win = win
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        cfg = win.cfg

        # ---- 名称 ----
        name_box = QGroupBox("名称")
        nf = QFormLayout(name_box)
        self.title_edit = QLineEdit(cfg["window_title"])
        self.title_edit.textChanged.connect(self._set_title)
        nf.addRow("窗口标题", self.title_edit)
        layout.addWidget(name_box)

        # ---- 界面尺寸 ----
        size_box = QGroupBox("界面尺寸")
        sf = QFormLayout(size_box)
        self.w_spin = self._spin(600, 4000, cfg["win_w"])
        self.h_spin = self._spin(400, 3000, cfg["win_h"])
        self.w_spin.valueChanged.connect(
            lambda v: self._set_size(v, self.h_spin.value()))
        self.h_spin.valueChanged.connect(
            lambda v: self._set_size(self.w_spin.value(), v))
        self.toolbar_spin = self._spin(36, 120, cfg["toolbar_height"])
        self.toolbar_spin.valueChanged.connect(self._set_toolbar_h)
        self.header_spin = self._spin(20, 60, cfg["header_height"])
        self.header_spin.valueChanged.connect(self._set_header_h)
        sf.addRow("窗口宽", self.w_spin)
        sf.addRow("窗口高", self.h_spin)
        sf.addRow("工具栏高度", self.toolbar_spin)
        sf.addRow("槽位标题高度", self.header_spin)
        layout.addWidget(size_box)

        # ---- 颜色 ----
        color_box = QGroupBox("颜色（Logo 矩形 / 按钮 / 工具栏）")
        cf = QFormLayout(color_box)
        colors = cfg.setdefault("colors", {})
        for key, label in COLOR_LABELS.items():
            btn = ColorButton(
                colors.get(key, "#ffffff"),
                lambda v, k=key: self._set_color(k, v),
            )
            cf.addRow(label, btn)
        self.logo_keep_chk = QCheckBox("Logo 图标保留 SVG 原色（忽略上面的颜色）")
        self.logo_keep_chk.setChecked(bool(colors.get("logo_icon_keep", False)))
        self.logo_keep_chk.toggled.connect(self._set_logo_keep)
        cf.addRow(self.logo_keep_chk)
        layout.addWidget(color_box)

        # ---- 行为 ----
        beh_box = QGroupBox("行为")
        bf = QFormLayout(beh_box)
        self.grid_combo = QComboBox()
        self.grid_combo.addItems(GRID_PRESETS.keys())
        self.grid_combo.setCurrentText(cfg["default_grid"])
        self.grid_combo.currentTextChanged.connect(self._set_grid)
        self.enforce_spin = self._spin(80, 1000, cfg["enforce_interval"])
        self.enforce_spin.valueChanged.connect(self._set_enforce)
        self.watcher_spin = self._spin(30, 500, cfg["watcher_interval"])
        self.watcher_spin.valueChanged.connect(self._set_watcher)
        bf.addRow("默认网格", self.grid_combo)
        bf.addRow("巡检间隔(ms)", self.enforce_spin)
        bf.addRow("拖拽检测间隔(ms)", self.watcher_spin)
        layout.addWidget(beh_box)

        # ---- 字体 ----
        font_box = QGroupBox("字体（总大小 + 偏移）")
        ff = QFormLayout(font_box)
        self.font_base_spin = self._spin(6, 40, cfg["font_base"])
        self.font_base_spin.valueChanged.connect(self._set_font_base)
        ff.addRow("字体总大小", self.font_base_spin)
        for key, label in FONT_LABELS.items():
            spin = self._spin(-20, 40, cfg["font_offsets"].get(key, 0))
            spin.valueChanged.connect(lambda v, k=key: self._set_font_offset(k, v))
            ff.addRow("偏移·" + label, spin)
        layout.addWidget(font_box)

        # ---- 图标 ----
        icon_box = QGroupBox("图标（总大小 + 偏移）")
        icf = QFormLayout(icon_box)
        self.icon_base_spin = self._spin(8, 64, cfg["icon_base"])
        self.icon_base_spin.valueChanged.connect(self._set_icon_base)
        icf.addRow("图标总大小", self.icon_base_spin)
        for key, label in ICON_LABELS.items():
            spin = self._spin(-20, 40, cfg["icon_offsets"].get(key, 0))
            spin.valueChanged.connect(lambda v, k=key: self._set_icon_offset(k, v))
            icf.addRow("偏移·" + label, spin)
        layout.addWidget(icon_box)

        # ---- 窗口使用情况 ----
        usage_box = QGroupBox("窗口使用情况")
        uv = QVBoxLayout(usage_box)
        refresh_btn = QPushButton("刷新统计")
        self.usage_text = QPlainTextEdit()
        self.usage_text.setReadOnly(True)
        self.usage_text.setMinimumHeight(160)
        refresh_btn.clicked.connect(self._refresh_usage)
        uv.addWidget(refresh_btn)
        uv.addWidget(self.usage_text)
        layout.addWidget(usage_box)

        # ---- 保存配置 ----
        save_btn = QPushButton("保存配置到 config.py")
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)
        self.status = QLabel("")
        self.status.setStyleSheet("color:#7ee0c0;")
        layout.addWidget(self.status)

        layout.addStretch()
        scroll.setWidget(inner)
        self.setWidget(scroll)

        self._refresh_usage()

    def _spin(self, lo, hi, val):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    # ---- 实时改 cfg 并刷新 ----
    def _set_title(self, t):
        self.win.cfg["window_title"] = t
        self.win.apply_config()

    def _set_size(self, w, h):
        self.win.cfg["win_w"], self.win.cfg["win_h"] = w, h
        self.win.resize(w, h)

    def _set_toolbar_h(self, n):
        self.win.cfg["toolbar_height"] = n
        self.win.apply_config()

    def _set_header_h(self, n):
        self.win.cfg["header_height"] = n
        self.win.apply_config()

    def _set_color(self, key, value):
        self.win.cfg.setdefault("colors", {})[key] = value
        self.win.apply_config()

    def _set_logo_keep(self, on):
        self.win.cfg.setdefault("colors", {})["logo_icon_keep"] = bool(on)
        self.win.apply_config()

    def _set_grid(self, name):
        self.win.cfg["default_grid"] = name
        self.win.combo.setCurrentText(name)

    def _set_enforce(self, n):
        self.win.cfg["enforce_interval"] = n
        self.win.apply_config()

    def _set_watcher(self, n):
        self.win.cfg["watcher_interval"] = n
        self.win.apply_config()

    def _set_font_base(self, n):
        self.win.cfg["font_base"] = n
        self.win.apply_config()

    def _set_icon_base(self, n):
        self.win.cfg["icon_base"] = n
        self.win.apply_config()

    def _set_font_offset(self, key, n):
        self.win.cfg["font_offsets"][key] = n
        self.win.apply_config()

    def _set_icon_offset(self, key, n):
        self.win.cfg["icon_offsets"][key] = n
        self.win.apply_config()

    def _refresh_usage(self):
        self.usage_text.setPlainText(self.win.usage_stats())

    def _save_config(self):
        path = config.__file__
        body = json.dumps(self.win.cfg, indent=4, ensure_ascii=False)
        new_block = (
            "# === CONFIG START (debug 工具会覆盖这一段，请勿手改) ===\n"
            "DEFAULT_CFG = " + body + "\n"
            "# === CONFIG END ==="
        )
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            pattern = r"# === CONFIG START.*?# === CONFIG END ==="
            if not re.search(pattern, text, flags=re.DOTALL):
                QMessageBox.warning(self, "失败", "找不到配置标记区块")
                return
            new_text = re.sub(pattern, lambda m: new_block, text, flags=re.DOTALL)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            self.status.setText("已保存到 config.py，下次启动生效")
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    win = GridWindow()
    panel = DebugPanel(win)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, panel)
    win.resize(win.cfg["win_w"] + 360, win.cfg["win_h"])
    win.show()
    win32_utils.register_own_hwnd(int(win.winId()))
    win32_utils.register_own_hwnd(int(panel.winId()))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
