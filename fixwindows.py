# -*- coding: utf-8 -*-
"""窗口修复工具：解决嵌入后无法输入、重开后窗口卡住等问题。"""
import ctypes

import win32api
import win32con
import win32gui
import win32process

GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_VISIBLE = 0x10000000

SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

_user32 = ctypes.windll.user32


def _thread_of(hwnd):
    try:
        return win32process.GetWindowThreadProcessId(hwnd)[0]
    except Exception:
        return 0


def attach_input(child_hwnd):
    """把嵌入窗口的输入队列连接到本线程，修复无法打字的问题。

    返回已连接的目标线程 id（之后用 detach_input 断开），失败返回 0。
    """
    try:
        target = _thread_of(child_hwnd)
        cur = win32api.GetCurrentThreadId()
        if target and target != cur:
            _user32.AttachThreadInput(cur, target, True)
            return target
    except Exception:
        pass
    return 0


def detach_input(target_thread):
    if not target_thread:
        return
    try:
        cur = win32api.GetCurrentThreadId()
        _user32.AttachThreadInput(cur, target_thread, False)
    except Exception:
        pass


def focus_child(child_hwnd):
    """把键盘焦点交给嵌入窗口。"""
    if not child_hwnd or not win32gui.IsWindow(child_hwnd):
        return
    target = _thread_of(child_hwnd)
    cur = win32api.GetCurrentThreadId()
    attached = False
    try:
        if target and target != cur:
            _user32.AttachThreadInput(cur, target, True)
            attached = True
        win32gui.SetFocus(child_hwnd)
    except Exception:
        pass
    finally:
        if attached:
            try:
                _user32.AttachThreadInput(cur, target, False)
            except Exception:
                pass


def fix_stuck_window(hwnd):
    """重开应用时，若窗口卡在子窗口样式/隐藏态，重置为正常的独立顶层窗口。"""
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    try:
        if win32gui.GetParent(hwnd):
            win32gui.SetParent(hwnd, 0)
        style = win32gui.GetWindowLong(hwnd, GWL_STYLE)
        style &= ~WS_CHILD
        style |= (WS_CAPTION | WS_THICKFRAME | WS_SYSMENU
                  | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_VISIBLE)
        win32gui.SetWindowLong(hwnd, GWL_STYLE, style)
        win32gui.SetWindowPos(
            hwnd, 0, 160, 160, 1000, 700,
            SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        )
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
        return True
    except Exception:
        return False
