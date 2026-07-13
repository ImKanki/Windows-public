# -*- coding: utf-8 -*-
"""记住每个槽位嵌入的应用，下次打开容器时尽量恢复到原来的窗口。"""
import json
import os

import win32_utils
from config import BASE_DIR

STATE_PATH = os.path.join(BASE_DIR, "session.json")


def save_session(cells):
    data = {"slots": []}
    for cell in cells:
        if cell.child_hwnd:
            data["slots"].append({
                "index": cell.index,
                "exe": win32_utils.get_window_exe(cell.child_hwnd),
                "title": win32_utils.get_window_title(cell.child_hwnd),
            })
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_session():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"slots": []}
