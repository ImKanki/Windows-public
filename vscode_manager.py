"""VSCode 实例的启动与窗口发现。"""
import os
import shutil
import subprocess
import time

import win32_utils


def find_code_executable():
    """查找 code 可执行文件路径。"""
    path = shutil.which("code")
    if path:
        return path
    # 常见安装位置兜底
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def launch_new_vscode(folder=None, wait_timeout=12.0):
    """启动一个新的 VSCode 窗口，返回新出现的窗口 hwnd（失败返回 None）。

    通过启动前后窗口集合做差集来定位新窗口。
    """
    code_path = find_code_executable()
    if not code_path:
        raise FileNotFoundError("找不到 VSCode 的 code 可执行文件，请确认已安装并加入 PATH。")

    before = {hwnd for hwnd, _ in win32_utils.find_vscode_windows()}

    args = f'"{code_path}" --new-window'
    if folder:
        args += f' "{folder}"'

    subprocess.Popen(args, shell=True)

    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        time.sleep(0.4)
        current = {hwnd for hwnd, _ in win32_utils.find_vscode_windows()}
        new = current - before
        if new:
            # 取最新出现的一个
            return sorted(new)[-1]
    return None
