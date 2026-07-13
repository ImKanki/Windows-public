# -*- coding: utf-8 -*-
"""独立启动器：以分离进程方式拉起容器，使其不受启动终端（如 VSCode 终端）关闭的影响。

用法：python launch.py
"""
import os
import subprocess
import sys

# Windows 进程创建标志
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "main.py")

    # 优先用 pythonw（无控制台窗口），没有则退回 python
    exe = sys.executable
    pythonw = exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw

    subprocess.Popen(
        [exe, target],
        cwd=here,
        creationflags=(
            DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        ),
        close_fds=True,
    )
    print("容器已作为独立进程启动，可以关闭此终端/VSCode。")


if __name__ == "__main__":
    main()
