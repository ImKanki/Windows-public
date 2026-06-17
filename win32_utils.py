"""Win32 窗口操作封装：查找 VSCode 窗口、嵌入/释放、定位、关闭、巡检。"""
import win32api
import win32con
import win32gui
import win32process

# 窗口样式常量
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_VISIBLE = 0x10000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

VSCODE_WINDOW_CLASS = "Chrome_WidgetWin_1"
VSCODE_PROCESS_NAME = "code.exe"


def get_process_name(pid):
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            pid,
        )
        path = win32process.GetModuleFileNameEx(handle, 0)
        win32api.CloseHandle(handle)
        return path.split("\\")[-1].lower()
    except Exception:
        return ""


def get_window_title(hwnd):
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""


def is_vscode_window(hwnd):
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    if not win32gui.IsWindowVisible(hwnd):
        return False
    try:
        cls = win32gui.GetClassName(hwnd)
    except Exception:
        return False
    if cls != VSCODE_WINDOW_CLASS:
        return False
    title = get_window_title(hwnd)
    if not title:
        return False
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return get_process_name(pid) == VSCODE_PROCESS_NAME


def find_vscode_windows():
    results = []

    def _enum(hwnd, _):
        if is_vscode_window(hwnd):
            results.append((hwnd, get_window_title(hwnd)))
        return True

    win32gui.EnumWindows(_enum, None)
    return results


def get_window_rect(hwnd):
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


def get_parent(hwnd):
    try:
        return win32gui.GetParent(hwnd)
    except Exception:
        return 0


def is_window(hwnd):
    try:
        return bool(hwnd) and win32gui.IsWindow(hwnd)
    except Exception:
        return False


def _apply_child_style(hwnd):
    """去掉标题栏/边框/最大化等，转为子窗口样式。"""
    style = win32gui.GetWindowLong(hwnd, GWL_STYLE)
    style &= ~WS_CAPTION
    style &= ~WS_THICKFRAME
    style &= ~WS_POPUP
    style &= ~WS_MAXIMIZEBOX
    style &= ~WS_MINIMIZEBOX
    style |= WS_CHILD
    win32gui.SetWindowLong(hwnd, GWL_STYLE, style)


def embed_window(child_hwnd, parent_hwnd):
    """把 child_hwnd 嵌入到 parent_hwnd。返回原始 style 以便恢复。"""
    original_style = win32gui.GetWindowLong(child_hwnd, GWL_STYLE)
    _apply_child_style(child_hwnd)
    win32gui.SetParent(child_hwnd, parent_hwnd)
    return original_style


def enforce_embed(child_hwnd, parent_hwnd, width, height):
    """巡检：确保窗口仍是该父容器的子窗口并填满。

    返回 True 表示窗口仍有效，False 表示窗口已不存在。
    """
    if not is_window(child_hwnd):
        return False
    try:
        if win32gui.GetParent(child_hwnd) != parent_hwnd:
            # 被最大化/还原冲出去了，重新吸附
            _apply_child_style(child_hwnd)
            win32gui.SetParent(child_hwnd, parent_hwnd)
            win32gui.MoveWindow(child_hwnd, 0, 0, max(1, width), max(1, height), True)
            return True
        # parent 正确：仅在尺寸不符时纠正，避免无谓重绘
        rect = win32gui.GetClientRect(child_hwnd)
        cur_w = rect[2] - rect[0]
        cur_h = rect[3] - rect[1]
        if abs(cur_w - width) > 2 or abs(cur_h - height) > 2:
            win32gui.MoveWindow(child_hwnd, 0, 0, max(1, width), max(1, height), True)
    except Exception:
        pass
    return True


def release_window(child_hwnd, original_style):
    if not is_window(child_hwnd):
        return
    try:
        win32gui.SetParent(child_hwnd, 0)
        if original_style is not None:
            win32gui.SetWindowLong(child_hwnd, GWL_STYLE, original_style)
        win32gui.SetWindowPos(
            child_hwnd,
            0,
            120,
            120,
            960,
            680,
            SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        )
        win32gui.ShowWindow(child_hwnd, win32con.SW_SHOW)
    except Exception:
        pass


def resize_embedded(child_hwnd, x, y, width, height):
    if not is_window(child_hwnd):
        return
    try:
        win32gui.MoveWindow(child_hwnd, x, y, max(1, width), max(1, height), True)
    except Exception:
        pass


def close_window(hwnd):
    if is_window(hwnd):
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            pass


def force_close_window(hwnd):
    """只强制关闭这一个窗口（不杀进程，避免连带关闭其它 VSCode 窗口）。"""
    if not is_window(hwnd):
        return
    try:
        win32gui.SetParent(hwnd, 0)
    except Exception:
        pass
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception:
        pass
