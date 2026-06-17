# -*- coding: utf-8 -*-
"""全局深色样式与配色常量，主程序和 debug 工具共用。"""

# 配色常量（供代码内拼接局部样式用）
APP_BG = "#1a1a2e"
PANEL_BG = "#16213e"
HOST_BG = "#0e1525"
CELL_BG = "#1a1a2e"
CELL_BORDER = "#2a3a6a"
HEADER_IDLE = "#16213e"
HEADER_ACTIVE = "#22305c"
BADGE_BG = "#2a3a6a"
ACCENT = "#7ee0c0"
GOLD = "#ffd166"
DROP_BG = "#16344a"

# 全局样式表
STYLE = """
QMainWindow, QWidget { background:#1a1a2e; color:#e8e8e8; }
QLabel { color:#cfcfe0; }
QToolTip { background:#16213e; color:#e8e8e8; border:1px solid #2a3a6a; }

QComboBox {
    background:#0e1525; color:#d0e0f0;
    border:1px solid #2a3a6a; border-radius:5px;
    padding:4px 10px; min-width:110px;
}
QComboBox:hover { border-color:#7ee0c0; }
QComboBox::drop-down { border:none; width:20px; }
QComboBox QAbstractItemView {
    background:#16213e; color:#e8e8e8; border:1px solid #2a3a6a;
    selection-background-color:#2a3a6a; outline:none; padding:2px;
}

QPushButton {
    background:#2a3a6a; color:#e8e8e8; border:none;
    padding:7px 14px; border-radius:5px; font-size:13px;
}
QPushButton:hover { background:#34457e; }
QPushButton:pressed { background:#22305c; }
QPushButton#primary { background:#1f6f5c; }
QPushButton#primary:hover { background:#2a8a72; }
QPushButton#iconBtn { background:transparent; padding:4px; border-radius:4px; }
QPushButton#iconBtn:hover { background:#2a3a6a; }

QSpinBox, QLineEdit {
    background:#0e1525; color:#d0e0f0;
    border:1px solid #2a3a6a; border-radius:4px; padding:3px;
}
QGroupBox {
    border:1px solid #2a3a6a; border-radius:6px;
    margin-top:10px; padding:8px;
}
QGroupBox::title {
    subcontrol-origin:margin; left:10px; padding:0 4px; color:#7ee0c0;
}
QPlainTextEdit {
    background:#0e1525; color:#d0e0f0; border:none;
    font-family:Consolas, monospace; font-size:13px;
}
QMenu { background:#16213e; color:#e8e8e8; border:1px solid #2a3a6a; }
QMenu::item { padding:6px 24px 6px 12px; }
QMenu::item:selected { background:#2a3a6a; }
QDockWidget { color:#cfcfe0; titlebar-close-icon:none; }
QDockWidget::title { background:#16213e; padding:6px 10px; }

/* VSCode 风格滚动条：细、无箭头、滑块半透明、hover 加深 */
QScrollBar:vertical { background:transparent; width:16px; margin:0; }
QScrollBar:horizontal { background:transparent; height:14px; margin:0; }
QScrollBar::handle:vertical {
    background:rgba(148,163,184,90); border:4px solid transparent;
    border-radius:8px; background-clip:padding; min-height:30px;
}
QScrollBar::handle:horizontal {
    background:rgba(148,163,184,90); border:4px solid transparent;
    border-radius:8px; background-clip:padding; min-width:30px;
}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover { background:rgba(148,163,184,153); }
QScrollBar::add-line, QScrollBar::sub-line {
    width:0; height:0; background:none; border:none;
}
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
"""
