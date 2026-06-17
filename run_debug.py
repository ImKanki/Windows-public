# -*- coding: utf-8 -*-
"""诊断启动器：捕获原生崩溃和 Qt 警告，全部写到 crash_log.txt。

用法：python run_debug.py，复现问题后把 crash_log.txt 发出来。
"""
import datetime
import faulthandler
import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "crash_log.txt")

log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)


def stamp(msg):
    t = datetime.datetime.now().strftime("%H:%M:%S")
    log_file.write(f"[{t}] {msg}\n")
    log_file.flush()


stamp("=" * 50)
stamp("启动诊断会话")

faulthandler.enable(file=log_file, all_threads=True)


def excepthook(exc_type, exc_value, exc_tb):
    stamp("Python 未捕获异常：")
    traceback.print_exception(exc_type, exc_value, exc_tb, file=log_file)
    log_file.flush()
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = excepthook

from PySide6.QtCore import QtMsgType, qInstallMessageHandler


def qt_message_handler(mode, context, message):
    label = {
        QtMsgType.QtDebugMsg: "QtDebug",
        QtMsgType.QtInfoMsg: "QtInfo",
        QtMsgType.QtWarningMsg: "QtWarning",
        QtMsgType.QtCriticalMsg: "QtCritical",
        QtMsgType.QtFatalMsg: "QtFatal",
    }.get(mode, "Qt")
    stamp(f"{label}: {message}")


qInstallMessageHandler(qt_message_handler)

stamp("即将启动应用")
try:
    import debug
    debug.main()
except SystemExit:
    stamp("应用正常退出")
except BaseException:
    stamp("main() 抛出异常：")
    traceback.print_exc(file=log_file)
    log_file.flush()
    raise
finally:
    stamp("会话结束")
    log_file.flush()
