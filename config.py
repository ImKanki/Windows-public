# -*- coding: utf-8 -*-
import os
import sys


def _resource_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _data_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


RESOURCE_DIR = _resource_dir()
BASE_DIR = _data_dir()

ICON_DIR = os.path.join(RESOURCE_DIR, "icon", "1")
LOG_DIR = os.path.join(BASE_DIR, "logs")


def font_size(cfg, key):
    return max(6, cfg["font_base"] + cfg["font_offsets"].get(key, 0))


def icon_size(cfg, key):
    return max(8, cfg["icon_base"] + cfg["icon_offsets"].get(key, 0))


def color(cfg, key, default="#ffffff"):
    return cfg.get("colors", {}).get(key, default)


# === CONFIG START (debug 工具会覆盖这一段，请勿手改) ===
DEFAULT_CFG = {
    "window_title": "VSCode 窗口网格容器",
    "win_w": 1440,
    "win_h": 920,
    "default_grid": "2 x 2 (4)",
    "toolbar_height": 60,
    "header_height": 30,
    "enforce_interval": 250,
    "watcher_interval": 70,
    "resize_enabled": True,
    "split_primary": "rows",
    "sync_inner": False,
    "sync_mode": "delta",
    "collapse_threshold": 160,
    "custom_rows": 2,
    "custom_cols": 3,
    "font_base": 12,
    "icon_base": 18,
    "font_offsets": {
        "app_title": 2,
        "button": 0,
        "cell_title": 0,
        "hint": -1,
        "badge": -1
    },
    "icon_offsets": {
        "toolbar": 0,
        "app_icon": 4,
        "close": 1,
        "drag": 1
    },
    "colors": {
        "logo_grad_start": "#1f6f5c",
        "logo_grad_end": "#2a8a72",
        "logo_text": "#ffffff",
        "logo_icon": "#ffffff",
        "logo_icon_keep": False,
        "toolbar_bg": "#16213e",
        "toolbar_border": "#243056",
        "btn_bg": "#2a3a6a",
        "btn_hover": "#34457e",
        "btn_primary": "#1f6f5c",
        "btn_primary_hover": "#2a8a72",
        "btn_icon": "#cfd6ea",
        "btn_primary_icon": "#eafff7"
    }
}
# === CONFIG END ===
