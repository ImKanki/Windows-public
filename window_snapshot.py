# -*- coding: utf-8 -*-
"""Capture and restore the exact pre-embed state of a Win32 window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import win32con
    import win32gui
    import win32process
except ImportError:
    win32con = None
    win32gui = None
    win32process = None

GWL_STYLE = -16
GWL_EXSTYLE = -20


def _safe(callable_, default):
    try:
        return callable_()
    except Exception:
        return default


def _placement_to_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, (list, tuple)) or len(value) != 5:
        return {}
    flags, show_cmd, min_pos, max_pos, normal_rect = value
    return {
        "flags": int(flags),
        "show_cmd": int(show_cmd),
        "min_pos": list(min_pos),
        "max_pos": list(max_pos),
        "normal_rect": list(normal_rect),
    }


def _placement_from_dict(value: Any):
    if not isinstance(value, dict):
        return None
    try:
        return (
            int(value.get("flags", 0)),
            int(value.get("show_cmd", 1)),
            tuple(int(x) for x in value.get("min_pos", (0, 0))),
            tuple(int(x) for x in value.get("max_pos", (0, 0))),
            tuple(int(x) for x in value.get("normal_rect", (0, 0, 800, 600))),
        )
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class WindowIdentity:
    pid: int
    thread_id: int
    exe: str
    title: str
    class_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "thread_id": self.thread_id,
            "exe": self.exe,
            "title": self.title,
            "class_name": self.class_name,
        }


@dataclass
class WindowSnapshot:
    identity: WindowIdentity
    parent: int
    owner: int
    style: int
    exstyle: int
    rect: tuple[int, int, int, int]
    placement: dict[str, Any]

    @classmethod
    def capture(cls, hwnd: int, exe: str = "") -> "WindowSnapshot":
        if win32gui is None or win32process is None:
            raise RuntimeError("WindowSnapshot requires pywin32 on Windows")

        thread_id, pid = _safe(
            lambda: win32process.GetWindowThreadProcessId(hwnd),
            (0, 0),
        )
        identity = WindowIdentity(
            pid=int(pid),
            thread_id=int(thread_id),
            exe=exe,
            title=_safe(lambda: win32gui.GetWindowText(hwnd), ""),
            class_name=_safe(lambda: win32gui.GetClassName(hwnd), ""),
        )
        return cls(
            identity=identity,
            parent=int(_safe(lambda: win32gui.GetParent(hwnd), 0) or 0),
            owner=int(
                _safe(
                    lambda: win32gui.GetWindow(hwnd, win32con.GW_OWNER),
                    0,
                )
                or 0
            ),
            style=int(_safe(lambda: win32gui.GetWindowLong(hwnd, GWL_STYLE), 0)),
            exstyle=int(
                _safe(lambda: win32gui.GetWindowLong(hwnd, GWL_EXSTYLE), 0)
            ),
            rect=tuple(
                int(x)
                for x in _safe(
                    lambda: win32gui.GetWindowRect(hwnd),
                    (0, 0, 800, 600),
                )
            ),
            placement=_placement_to_dict(
                _safe(lambda: win32gui.GetWindowPlacement(hwnd), ())
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity.to_dict(),
            "parent": self.parent,
            "owner": self.owner,
            "style": self.style,
            "exstyle": self.exstyle,
            "rect": list(self.rect),
            "placement": self.placement,
        }

    def restore(self, hwnd: int) -> bool:
        if win32gui is None or win32con is None:
            return False
        if not _safe(lambda: win32gui.IsWindow(hwnd), False):
            return False

        try:
            win32gui.SetParent(hwnd, self.parent)
            win32gui.SetWindowLong(hwnd, GWL_STYLE, self.style)
            win32gui.SetWindowLong(hwnd, GWL_EXSTYLE, self.exstyle)

            placement = _placement_from_dict(self.placement)
            if placement is not None:
                try:
                    win32gui.SetWindowPlacement(hwnd, placement)
                except Exception:
                    pass

            left, top, right, bottom = self.rect
            win32gui.SetWindowPos(
                hwnd,
                0,
                left,
                top,
                max(1, right - left),
                max(1, bottom - top),
                win32con.SWP_NOZORDER
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_FRAMECHANGED
                | win32con.SWP_SHOWWINDOW,
            )

            show_cmd = int(self.placement.get("show_cmd", win32con.SW_SHOWNORMAL))
            win32gui.ShowWindow(hwnd, show_cmd or win32con.SW_SHOWNORMAL)
            return True
        except Exception:
            return False
