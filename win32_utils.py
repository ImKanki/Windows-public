"""Win32 窗口操作封装：识别可嵌入窗口、嵌入/释放、定位、关闭、巡检、取进程路径。"""
import atexit
import ctypes

import win32api
import win32con
import win32gui
import win32process

RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_FRAME = 0x0400
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100
RDW_ERASENOW = 0x0200

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
WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_NOCOPYBITS = 0x0100
SWP_NOSENDCHANGING = 0x0400

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

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

# 当前所有嵌入中的窗口： child_hwnd -> original_style
_embedded = {}


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


def get_window_pid(hwnd):
    try:
        return win32process.GetWindowThreadProcessId(hwnd)[1]
    except Exception:
        return 0


def _query_full_path(handle):
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_ulong(1024)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(
            int(handle), 0, buf, ctypes.byref(size)
        ):
            return buf.value
    except Exception:
        pass
    return ""


def get_window_exe(hwnd):
    """返回窗口所属进程的可执行文件完整路径，失败返回空串。"""
    pid = get_window_pid(hwnd)
    if not pid:
        return ""
    try:
        h = win32api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        try:
            path = win32process.GetModuleFileNameEx(h, 0)
        except Exception:
            path = _query_full_path(h)
        win32api.CloseHandle(h)
        return path or ""
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


# 兼容旧接口
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
    # 裁剪自身子控件与同级，减少重绘时的相互覆盖残留
    style |= WS_CLIPCHILDREN | WS_CLIPSIBLINGS
    win32gui.SetWindowLong(hwnd, GWL_STYLE, style)


def embed_window(child_hwnd, parent_hwnd):
    original_style = win32gui.GetWindowLong(child_hwnd, GWL_STYLE)
    _apply_child_style(child_hwnd)
    win32gui.SetParent(child_hwnd, parent_hwnd)
    _embedded[int(child_hwnd)] = original_style
    return original_style


def enforce_embed(child_hwnd, parent_hwnd, width, height):
    if not is_window(child_hwnd):
        return False
    try:
        if win32gui.GetParent(child_hwnd) != parent_hwnd:
            _apply_child_style(child_hwnd)
            win32gui.SetParent(child_hwnd, parent_hwnd)
            resize_embedded(child_hwnd, 0, 0, width, height)
            return True
        rect = win32gui.GetClientRect(child_hwnd)
        cur_w = rect[2] - rect[0]
        cur_h = rect[3] - rect[1]
        if abs(cur_w - width) > 2 or abs(cur_h - height) > 2:
            resize_embedded(child_hwnd, 0, 0, width, height)
    except Exception:
        pass
    return True


def release_window(child_hwnd, original_style):
    _embedded.pop(int(child_hwnd), None)
    if not is_window(child_hwnd):
        return
    try:
        # 1. 脱离父窗口回到桌面
        win32gui.SetParent(child_hwnd, 0)

        # 2. 恢复窗口样式：优先用捕获的原样式，并强制可见
        if original_style is not None:
            win32gui.SetWindowLong(
                child_hwnd, GWL_STYLE, original_style | WS_VISIBLE
            )
        else:
            style = win32gui.GetWindowLong(child_hwnd, GWL_STYLE)
            style &= ~WS_CHILD
            style |= (WS_CAPTION | WS_THICKFRAME | WS_SYSMENU
                      | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_VISIBLE)
            win32gui.SetWindowLong(child_hwnd, GWL_STYLE, style)

        # 3. 移回可见区域 + 应用样式变更（FRAMECHANGED 让边框生效）
        win32gui.SetWindowPos(
            child_hwnd, 0, 160, 160, 1000, 700,
            SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        )

        # 4. 还原显示状态（Electron 窗口常停在隐藏/最小化态）
        win32gui.ShowWindow(child_hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(child_hwnd, win32con.SW_SHOWNORMAL)

        # 5. 强制重绘，逼 Electron/Chromium 重新计算布局
        try:
            win32gui.RedrawWindow(
                child_hwnd, None, None,
                RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN,
            )
        except Exception:
            pass

        # 6. 置前，确保用户能看到
        try:
            win32gui.SetForegroundWindow(child_hwnd)
        except Exception:
            pass
    except Exception:
        pass


def resize_embedded(child_hwnd, x, y, width, height):
    """重定位嵌入窗口。关键：SWP_NOCOPYBITS 禁止复制旧位图，消除拖拽残留。"""
    if not is_window(child_hwnd):
        return
    try:
        win32gui.SetWindowPos(
            child_hwnd, 0, x, y, max(1, width), max(1, height),
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOCOPYBITS | SWP_NOSENDCHANGING,
        )
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


def release_all():
    """退出兜底：把所有还嵌着的窗口弹回桌面，避免随父窗口一起被销毁。"""
    for hwnd, style in list(_embedded.items()):
        release_window(hwnd, style)
    _embedded.clear()


atexit.register(release_all)
