"""入口：启动网格容器。

用法：
    python main.py            # 仅打开容器，不自动启动 VSCode
    python main.py --autofill # 打开容器并自动启动 VSCode 填满默认网格
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from grid_window import GridWindow


def main():
    autofill = "--autofill" in sys.argv

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = GridWindow()
    window.show()

    if autofill:
        QTimer.singleShot(300, window.fill_empty_cells)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
