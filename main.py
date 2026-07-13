# -*- coding: utf-8 -*-
"""Application entry point."""

import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import win32_utils
from app_logging import log_event, setup_logging
from grid_window import GridWindow
from styles import STYLE
from version import __version__


def main():
    autofill = "--autofill" in sys.argv
    logger = setup_logging()
    log_event(
        logger,
        logging.INFO,
        "application_start",
        version=__version__,
        autofill=autofill,
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Window Workspace")
    app.setApplicationVersion(__version__)
    app.setStyleSheet(STYLE)

    window = GridWindow()
    window.show()
    win32_utils.register_own_hwnd(int(window.winId()))

    if autofill:
        QTimer.singleShot(300, window.scan_and_attach)

    exit_code = app.exec()
    log_event(
        logger,
        logging.INFO,
        "application_exit",
        exit_code=exit_code,
    )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
