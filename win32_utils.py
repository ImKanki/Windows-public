"""Win32 窗口操作封装：识别可嵌入窗口、嵌入/释放、定位、关闭、巡检。"""
import win32api
import win32con
import win32gui
import win32process

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

# 永不嵌入的窗口类名（系统外壳、输入法等）
_BLOCKED_CLASSES = {
    "Progman",                 # 桌面
    "WorkerW",
    "Shell_TrayWnd",           # 任务栏
    "Shell_SecondaryTrayWnd",
    "Windows.UI.Core.CoreWindow",
    "ApplicationFrameWindow",  # UWP 外壳（嵌入会异常）
    "ForegroundStaging",
    "MultitaskingViewFrame",
    "XamlExplorerHostIslandWindow",
}

# 由主程序在启动时登记自己的窗口句柄，避免把容器/面板嵌进自身
_own_hwnds = set()


def register_own_hwnd(hwnd):
    """登记本程序自己的窗口，扫描/拖拽时排除它们。"""
    try:
        _own_hwnds.add(int(hwnd))
    except Exception:
        pass


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


def is_window(hwnd):
    try:
        return bool(hwnd) and win32gui.IsWindow(hwnd)
    except Exception:
        return False


def get_parent(hwnd):
    try:
        return win32gui.GetParent(hwnd)
    except Exception:
        return 0


def is_embeddable_window(hwnd):
    """通用判断：是否是一个可以被嵌入的普通顶层应用窗口。"""
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    if not win32gui.IsWindowVisible(hwnd):
        return False
    if int(hwnd) in _own_hwnds:
        return False
    # 已经是别人的子窗口
    if win32gui.GetParent(hwnd):
        return False
    # 有归属窗口的多为对话框/弹窗
    try:
        if win32gui.GetWindow(hwnd, win32con.GW_OWNER):
            return False
    except Exception:
        pass

    try:
        cls = win32gui.GetClassName(hwnd)
    except Exception:
        return False
    if cls in _BLOCKED_CLASSES:
        return False

    title = get_window_title(hwnd)
    if not title:
        return False

    ex = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
    if ex & WS_EX_TOOLWINDOW:
        return False

    return True


def find_embeddable_windows():
    """枚举当前所有可嵌入的顶层窗口，返回 [(hwnd, title), ...]。"""
    results = []

    def _enum(hwnd, _):
        if is_embeddable_window(hwnd):
            results.append((hwnd, get_window_title(hwnd)))
        return True

    win32gui.EnumWindows(_enum, None)
    return results


# 兼容旧接口：原来调用 find_vscode_windows / is_vscode_window 的地方继续可用
def is_vscode_window(hwnd):
    return is_embeddable_window(hwnd)


def find_vscode_windows():
    return find_embeddable_windows()


def get_window_rect(hwnd):
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


def _apply_child_style(hwnd):
    style = win32gui.GetWindowLong(hwnd, GWL_STYLE)
    style &= ~WS_CAPTION
    style &= ~WS_THICKFRAME
    style &= ~WS_POPUP
    style &= ~WS_MAXIMIZEBOX
    style &= ~WS_MINIMIZEBOX
    style |= WS_CHILD
    win32gui.SetWindowLong(hwnd, GWL_STYLE, style)


def embed_window(child_hwnd, parent_hwnd):
    original_style = win32gui.GetWindowLong(child_hwnd, GWL_STYLE)
    _apply_child_style(child_hwnd)
    win32gui.SetParent(child_hwnd, parent_hwnd)
    return original_style


def enforce_embed(child_hwnd, parent_hwnd, width, height):
    if not is_window(child_hwnd):
        return False
    try:
        if win32gui.GetParent(child_hwnd) != parent_hwnd:
            _apply_child_style(child_hwnd)
            win32gui.SetParent(child_hwnd, parent_hwnd)
            win32gui.MoveWindow(child_hwnd, 0, 0, max(1, width), max(1, height), True)
            return True
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
