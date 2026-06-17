"""图标字体加载与图标生成。

从 icon/1 目录下自动查找 .ttf 字体并加载，按名称映射到字符。
ICON_MAP 来源于项目提供的 iconfont 字符表。
"""
import glob
import os

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon", "1")

# 名称 -> unicode 码点（十六进制）
_RAW = {
    "fullscreen-shrink": 0xE6AC, "layers": 0xE6AD, "lock": 0xE6AE,
    "fullscreen-expand": 0xE6AF, "map": 0xE6B0, "meh": 0xE6B1, "menu": 0xE6B2,
    "loading": 0xE6B3, "help": 0xE6B4, "minus-circle": 0xE6B5, "modular": 0xE6B6,
    "notification": 0xE6B7, "mic": 0xE6B8, "more": 0xE6B9, "pad": 0xE6BA,
    "operation": 0xE6BB, "play": 0xE6BC, "print": 0xE6BD, "mobile-phone": 0xE6BE,
    "minus": 0xE6BF, "navigation": 0xE6C0, "pdf": 0xE6C1, "prompt": 0xE6C2,
    "move": 0xE6C3, "refresh": 0xE6C4, "run-up": 0xE6C5, "picture": 0xE6C6,
    "run-in": 0xE6C7, "pin": 0xE6C8, "save": 0xE6C9, "search": 0xE6CA,
    "share": 0xE6CB, "scanning": 0xE6CC, "security": 0xE6CD, "sign-out": 0xE6CE,
    "select": 0xE6CF, "stop": 0xE6D0, "success": 0xE6D1, "smile": 0xE6D2,
    "switch": 0xE6D3, "setting": 0xE6D4, "survey": 0xE6D5, "task": 0xE6D6,
    "skip": 0xE6D7, "text": 0xE6D8, "time": 0xE6D9, "telephone-out": 0xE6DA,
    "toggle-left": 0xE6DB, "toggle-right": 0xE6DC, "telephone": 0xE6DD,
    "top": 0xE6DE, "unlock": 0xE6DF, "user": 0xE6E0, "upload": 0xE6E1,
    "work": 0xE6E2, "training": 0xE6E3, "warning": 0xE6E4, "zoom-in": 0xE6E5,
    "zoom-out": 0xE6E6, "add-bold": 0xE6E7, "arrow-left-bold": 0xE6E8,
    "arrow-up-bold": 0xE6E9, "close-bold": 0xE6EA, "arrow-down-bold": 0xE6EB,
    "minus-bold": 0xE6EC, "arrow-right-bold": 0xE6ED, "select-bold": 0xE6EE,
    "arrow-up-filling": 0xE6EF, "arrow-down-filling": 0xE6F0,
    "arrow-left-filling": 0xE6F1, "arrow-right-filling": 0xE6F2,
    "caps-unlock-filling": 0xE6F3, "comment-filling": 0xE6F4,
    "check-item-filling": 0xE6F5, "clock-filling": 0xE6F6,
    "delete-filling": 0xE6F7, "decline-filling": 0xE6F8,
    "dynamic-filling": 0xE6F9, "intermediate-filling": 0xE6FA,
    "favorite-filling": 0xE6FB, "layout-filling": 0xE6FC,
    "help-filling": 0xE6FD, "history-filling": 0xE6FE, "filter-filling": 0xE6FF,
    "file-common-filling": 0xE700, "news-filling": 0xE701, "edit-filling": 0xE702,
    "fullscreen-expand-filling": 0xE703, "smile-filling": 0xE704,
    "rise-filling": 0xE705, "picture-filling": 0xE706,
    "notification-filling": 0xE707, "user-filling": 0xE708,
    "setting-filling": 0xE709, "switch-filling": 0xE70A, "work-filling": 0xE70B,
    "task-filling": 0xE70C, "success-filling": 0xE70D, "warning-filling": 0xE70E,
    "folder-filling": 0xE70F, "map-filling": 0xE710, "prompt-filling": 0xE711,
    "meh-filling": 0xE712, "cry-filling": 0xE713, "top-filling": 0xE714,
    "home-filling": 0xE715, "sorting": 0xE716, "column-3": 0xE663,
    "column-4": 0xE664, "add": 0xE665, "add-circle": 0xE666, "adjust": 0xE667,
    "arrow-up-circle": 0xE668, "arrow-right-circle": 0xE669, "arrow-down": 0xE66A,
    "ashbin": 0xE66B, "arrow-right": 0xE66C, "browse": 0xE66D, "bottom": 0xE66E,
    "back": 0xE66F, "bad": 0xE670, "arrow-double-left": 0xE671,
    "arrow-left-circle": 0xE672, "arrow-double-right": 0xE673, "caps-lock": 0xE674,
    "camera": 0xE675, "chart-bar": 0xE676, "attachment": 0xE677, "code": 0xE678,
    "close": 0xE679, "check-item": 0xE67A, "calendar": 0xE67B, "comment": 0xE67C,
    "column-vertical": 0xE67D, "column-horizontal": 0xE67E, "complete": 0xE67F,
    "chart-pie": 0xE680, "cry": 0xE681, "customer-service": 0xE682,
    "delete": 0xE683, "direction-down": 0xE684, "copy": 0xE685, "cut": 0xE686,
    "data-view": 0xE687, "direction-down-circle": 0xE688, "direction-right": 0xE689,
    "direction-up": 0xE68A, "discount": 0xE68B, "direction-left": 0xE68C,
    "download": 0xE68D, "electronics": 0xE68E, "drag": 0xE68F, "elipsis": 0xE690,
    "export": 0xE691, "explain": 0xE692, "edit": 0xE693, "eye-close": 0xE694,
    "email": 0xE695, "error": 0xE696, "favorite": 0xE697, "file-common": 0xE698,
    "file-delete": 0xE699, "file-add": 0xE69A, "film": 0xE69B, "fabulous": 0xE69C,
    "file": 0xE69D, "folder-close": 0xE69E, "filter": 0xE69F, "good": 0xE6A0,
    "hide": 0xE6A1, "home": 0xE6A2, "history": 0xE6A3, "file-open": 0xE6A4,
    "forward": 0xE6A5, "import": 0xE6A6, "image-text": 0xE6A7, "keyboard-26": 0xE6A8,
    "keyboard-9": 0xE6A9, "link": 0xE6AA, "layout": 0xE6AB,
}

# 名称 -> 字符
ICON_MAP = {name: chr(code) for name, code in _RAW.items()}

_family = None
_loaded = False


def load_font():
    """加载图标字体，返回字体族名（找不到返回 None）。"""
    global _family, _loaded
    if _loaded:
        return _family
    _loaded = True
    if not os.path.isdir(ICON_DIR):
        return None
    ttfs = glob.glob(os.path.join(ICON_DIR, "*.ttf"))
    ttfs += glob.glob(os.path.join(ICON_DIR, "*.TTF"))
    if not ttfs:
        return None
    fid = QFontDatabase.addApplicationFont(ttfs[0])
    families = QFontDatabase.applicationFontFamilies(fid)
    if families:
        _family = families[0]
    return _family


def icon_font(size=16):
    """返回指定像素大小的图标字体。"""
    fam = load_font()
    f = QFont(fam if fam else "")
    f.setPixelSize(size)
    return f


def char(name):
    """返回图标字符；找不到返回空串。"""
    return ICON_MAP.get(name, "")


def make_icon(name, color="#cccccc", size=20):
    """把图标字符渲染成 QIcon，用于按钮等。"""
    fam = load_font()
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    f = QFont(fam if fam else "")
    f.setPixelSize(int(size * 0.85))
    painter.setFont(f)
    painter.setPen(QColor(color))
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, char(name))
    painter.end()
    return QIcon(pm)
