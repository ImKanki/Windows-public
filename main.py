# -*- coding: utf-8 -*-
"""入口：启动通用窗口网格容器。

用法：
    python main.py            # 仅打开容器
    python main.py --autofill # 打开后自动扫描填充空槽
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import win32_utils

from grid_window import GridWindow
from styles import STYLE


def main():
    autofill = "--autofill" in sys.argv

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    window = GridWindow()
    window.show()
    win32_utils.register_own_hwnd(int(window.winId()))

    if autofill:
        QTimer.singleShot(300, window.scan_and_attach)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
