"""入口：启动网格容器。

用法：
    python main.py            # 仅打开容器，不自动启动 VSCode
    python main.py --autofill # 打开容器并自动启动 VSCode 填满默认网格
"""
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from grid_window import GridWindow


def apply_dark_palette(app):
    """应用级深色调色板，消除默认浅灰背景。"""
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#1e1e1e"))
    pal.setColor(QPalette.WindowText, QColor("#dddddd"))
    pal.setColor(QPalette.Base, QColor("#252526"))
    pal.setColor(QPalette.AlternateBase, QColor("#2d2d30"))
    pal.setColor(QPalette.Text, QColor("#dddddd"))
    pal.setColor(QPalette.Button, QColor("#3a3d41"))
    pal.setColor(QPalette.ButtonText, QColor("#eeeeee"))
    pal.setColor(QPalette.Highlight, QColor("#094771"))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ToolTipBase, QColor("#2d2d30"))
    pal.setColor(QPalette.ToolTipText, QColor("#dddddd"))
    app.setPalette(pal)


def main():
    autofill = "--autofill" in sys.argv

    app = QApplication(sys.argv)
    apply_dark_palette(app)

    window = GridWindow()
    window.show()

    if autofill:
        QTimer.singleShot(300, window.fill_empty_cells)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
