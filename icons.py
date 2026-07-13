# -*- coding: utf-8 -*-
"""SVG icon loading and neutral monochrome fallbacks."""

import os

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from config import ICON_DIR


FALLBACK = {
    "drag": "⋮⋮",
    "close": "×",
    "add": "+",
    "file-add": "+",
    "search": "⌕",
    "scanning": "◎",
    "setting": "⚙",
    "layout": "▦",
    "refresh": "↻",
    "sign-out": "↗",
    "warning": "!",
    "move": "↕",
    "more": "•••",
    "window": "▣",
    "trash": "×",
    "power": "⏻",
    "info": "i",
    "monitor": "▤",
    "sliders": "☷",
    "help": "?",
    "check": "✓",
    "down": "⌄",
    "upward": "⌃",
}


def _svg_path(name):
    path = os.path.join(ICON_DIR, name + ".svg")
    return path if os.path.exists(path) else None


def make_pixmap(name, color="#aab3c2", size=20):
    """Return a recolored SVG pixmap, or a restrained text fallback."""
    size = max(4, int(size))
    path = _svg_path(name)

    if path:
        renderer = QSvgRenderer(path)
        base = QPixmap(size, size)
        base.fill(Qt.GlobalColor.transparent)

        painter = QPainter(base)
        renderer.render(painter)
        painter.end()

        if color is None:
            return base

        colored = QPixmap(size, size)
        colored.fill(Qt.GlobalColor.transparent)
        painter = QPainter(colored)
        painter.drawPixmap(0, 0, base)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceIn
        )
        painter.fillRect(colored.rect(), QColor(color))
        painter.end()
        return colored

    symbol = FALLBACK.get(name, "")
    if not symbol:
        return None

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)

    font = QFont("Segoe UI Symbol")
    font.setPixelSize(max(8, int(size * 0.72)))
    font.setWeight(QFont.Weight.Medium)
    painter.setFont(font)
    painter.setPen(QColor(color or "#aab3c2"))
    painter.drawText(
        QRect(0, 0, size, size),
        Qt.AlignmentFlag.AlignCenter,
        symbol,
    )
    painter.end()
    return pixmap


def make_icon(name, color="#aab3c2", size=20):
    pixmap = make_pixmap(name, color, size)
    return QIcon(pixmap) if pixmap is not None else QIcon()


def char(name):
    return FALLBACK.get(name, "")
