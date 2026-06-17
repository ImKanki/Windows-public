"""Win32 窗口操作封装：查找 VSCode 窗口、嵌入/释放、定位、关闭。"""
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

# VSCode 主窗口的类名
VSCODE_WINDOW_CLASS = "Chrome_WidgetWin_1"
VSCODE_PROCESS_NAME = "code.exe"


def get_process_name(pid):
    """根据 pid 获取进程可执行文件名（小写 basename）。"""
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
    """判断一个顶层窗口是否是 VSCode 主窗口。"""
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
    """枚举系统中所有 VSCode 主窗口，返回 [(hwnd, title), ...]。"""
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


def embed_window(child_hwnd, parent_hwnd):
    """把 child_hwnd 嵌入到 parent_hwnd。返回原始 style 以便恢复。"""
    original_style = win32gui.GetWindowLong(child_hwnd, GWL_STYLE)

    new_style = original_style
    new_style &= ~WS_CAPTION
    new_style &= ~WS_THICKFRAME
    new_style &= ~WS_POPUP
    new_style |= WS_CHILD
    win32gui.SetWindowLong(child_hwnd, GWL_STYLE, new_style)

    win32gui.SetParent(child_hwnd, parent_hwnd)
    return original_style


def release_window(child_hwnd, original_style):
    """把窗口从父容器释放回桌面，恢复为独立窗口。"""
    if not child_hwnd or not win32gui.IsWindow(child_hwnd):
        return
    try:
        win32gui.SetParent(child_hwnd, 0)
        if original_style is not None:
            win32gui.SetWindowLong(child_hwnd, GWL_STYLE, original_style)
        win32gui.SetWindowPos(
            child_hwnd,
            0,
            100,
            100,
            900,
            650,
            SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        )
        win32gui.ShowWindow(child_hwnd, win32con.SW_SHOW)
    except Exception:
        pass


def resize_embedded(child_hwnd, x, y, width, height):
    """调整已嵌入窗口在父容器内的位置和大小。"""
    if not child_hwnd or not win32gui.IsWindow(child_hwnd):
        return
    try:
        win32gui.MoveWindow(child_hwnd, x, y, max(1, width), max(1, height), True)
    except Exception:
        pass


def close_window(hwnd):
    """向窗口发送关闭消息（正常关闭，VSCode 可能弹出未保存提示）。"""
    if hwnd and win32gui.IsWindow(hwnd):
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            pass


def force_close_window(hwnd):
    """只强制关闭这一个窗口（不杀进程）。

    VSCode 多个窗口共用同一个主进程，杀进程会连带关闭全部窗口，
    因此这里只对目标窗口连发 WM_CLOSE，强制它单独关闭。
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return
    try:
        # 先脱离父容器，避免容器侧残留
        win32gui.SetParent(hwnd, 0)
    except Exception:
        pass
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        # 再补发一次，应对第一次被未保存提示拦截后的状态
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    except Exception:
        pass
