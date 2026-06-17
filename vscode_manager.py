# -*- coding: utf-8 -*-
"""VSCode 启动管理：用独立 user-data-dir 启动真正互不干扰的多实例，并等待其窗口出现。"""
import os
import shutil
import subprocess
import tempfile
import time
import uuid

import win32_utils

# 为每个实例分配独立数据目录的根位置
_PROFILE_ROOT = os.path.join(tempfile.gettempdir(), "vscode_grid_profiles")

# 常见的 VSCode 可执行文件位置
_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft VS Code\Code.exe"),
]

_created_profiles = []


def find_code_executable():
    """定位 Code.exe：先查常见路径，再查 PATH。找不到抛 FileNotFoundError。"""
    for path in _CANDIDATES:
        if path and os.path.exists(path):
            return path
    which = shutil.which("code")
    if which:
        # code 通常是 .cmd 包装，对应同目录的 Code.exe
        base = os.path.dirname(which)
        exe = os.path.join(base, "Code.exe")
        if os.path.exists(exe):
            return exe
        return which
    raise FileNotFoundError(
        "未找到 VSCode 可执行文件。请确认已安装 VSCode，"
        "或把 Code.exe 所在目录加入 PATH。"
    )


def _new_profile_dir():
    """为新实例创建独立的 user-data 与 extensions 目录。"""
    token = uuid.uuid4().hex[:8]
    base = os.path.join(_PROFILE_ROOT, token)
    user_dir = os.path.join(base, "user-data")
    ext_dir = os.path.join(base, "extensions")
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(ext_dir, exist_ok=True)
    _created_profiles.append(base)
    return user_dir, ext_dir


def launch_new_vscode(timeout=12.0):
    """启动一个全新的、独立的 VSCode 窗口，返回其 hwnd；超时返回 None。

    用独立 user-data-dir / extensions-dir 绕过单实例机制，确保每次都是新窗口。
    """
    exe = find_code_executable()
    user_dir, ext_dir = _new_profile_dir()

    # 记录启动前已有的 VSCode 窗口，便于识别新窗口
    before = {hwnd for hwnd, _ in win32_utils.find_vscode_windows()}

    args = [
        exe,
        "--new-window",
        f"--user-data-dir={user_dir}",
        f"--extensions-dir={ext_dir}",
        "--disable-workspace-trust",
    ]
    # 不阻塞、不继承控制台
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
    subprocess.Popen(args, creationflags=creationflags)

    # 轮询等待新窗口出现
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.25)
        current = win32_utils.find_vscode_windows()
        for hwnd, _ in current:
            if hwnd not in before:
                # 再等一拍让窗口完成初始化
                time.sleep(0.3)
                return hwnd
    return None


def cleanup_profiles():
    """退出时清理本次会话创建的临时数据目录（可在主程序 closeEvent 调用）。"""
    for base in _created_profiles:
        try:
            shutil.rmtree(base, ignore_errors=True)
        except Exception:
            pass
    _created_profiles.clear()
