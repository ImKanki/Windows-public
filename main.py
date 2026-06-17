# -*- coding: utf-8 -*-
"""入口：启动网格容器。

用法：
    python main.py            # 仅打开容器
    python main.py --autofill # 打开并自动填满默认网格
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from grid_window import GridWindow
from styles import STYLE


def main():
    autofill = "--autofill" in sys.argv

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    window = GridWindow()
    window.show()

    if autofill:
        QTimer.singleShot(300, window.fill_empty_cells)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
