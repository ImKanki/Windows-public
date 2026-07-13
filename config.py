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
    "window_title": "Workspace · Window Grid",
    "win_w": 1440,
    "win_h": 920,
    "default_grid": "2 x 2 (4)",
    "toolbar_height": 58,
    "status_height": 30,
    "header_height": 38,
    "workspace_margin": 12,
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
        "app_title": 3,
        "button": 0,
        "cell_title": 0,
        "hint": -1,
        "badge": -2,
    },
    "icon_offsets": {
        "toolbar": 0,
        "app_icon": 4,
        "close": 0,
        "drag": 0,
    },
    "colors": {
        # 保留旧键，避免 debug 工具或外部配置读取失败。
        "logo_grad_start": "#4C8DFF",
        "logo_grad_end": "#4C8DFF",
        "logo_text": "#F4F7FB",
        "logo_icon": "#F4F7FB",
        "logo_icon_keep": False,
        "toolbar_bg": "#11141B",
        "toolbar_border": "#252A35",
        "btn_bg": "#1A1F29",
        "btn_hover": "#252B37",
        "btn_primary": "#4C8DFF",
        "btn_primary_hover": "#67A0FF",
        "btn_icon": "#AAB3C2",
        "btn_primary_icon": "#FFFFFF",
        # 新界面语义色。
        "app_bg": "#0B0D12",
        "surface": "#11141B",
        "surface_2": "#171B24",
        "border": "#272C37",
        "text": "#F1F3F7",
        "muted": "#9AA3B2",
        "accent": "#4C8DFF",
        "success": "#38B978",
        "danger": "#E45A64",
    },
}
# === CONFIG END ===
