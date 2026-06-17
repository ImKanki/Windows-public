# -*- coding: utf-8 -*-
"""SVG 图标加载并重新染色，找不到 svg 时回退到系统符号。"""
import os

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from config import ICON_DIR

# svg 缺失时的系统符号回退（Windows 自带字体可显示）
FALLBACK = {
    "drag": "≡", "close": "✕", "add": "＋", "file-add": "＋",
    "search": "⌕", "scanning": "⊙", "setting": "⚙", "layout": "▦",
    "refresh": "↻", "sign-out": "⏏", "warning": "⚠", "move": "✥",
}


def _svg_path(name):
    p = os.path.join(ICON_DIR, name + ".svg")
    return p if os.path.exists(p) else None


def make_pixmap(name, color="#cfcfe0", size=20):
    """读取 name.svg 重染成 color，返回 QPixmap；无 svg 时用回退符号；都没有返回 None。"""
    size = max(4, int(size))
    path = _svg_path(name)
    if path:
        renderer = QSvgRenderer(path)
        base = QPixmap(size, size)
        base.fill(Qt.GlobalColor.transparent)
        p = QPainter(base)
        renderer.render(p)
        p.end()

        if color is None:
            return base

        colored = QPixmap(size, size)
        colored.fill(Qt.GlobalColor.transparent)
        p = QPainter(colored)
        p.drawPixmap(0, 0, base)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(colored.rect(), QColor(color))
        p.end()
        return colored

    sym = FALLBACK.get(name, "")
    if not sym:
        return None
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    f = QFont()
    f.setPixelSize(int(size * 0.8))
    p.setFont(f)
    p.setPen(QColor(color or "#cfcfe0"))
    p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, sym)
    p.end()
    return pm


def make_icon(name, color="#cfcfe0", size=20):
    pm = make_pixmap(name, color, size)
    return QIcon(pm) if pm is not None else QIcon()


def char(name):
    """供纯文本场景使用的回退符号。"""
    return FALLBACK.get(name, "")
