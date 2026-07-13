# -*- coding: utf-8 -*-
"""One lifecycle service for every external window hosted by a cell."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time

import fixwindows
import win32_utils
from app_logging import get_logger, log_event
from window_snapshot import WindowSnapshot


@dataclass
class ManagedWindowBinding:
    hwnd: int
    pane_index: int
    parent_hwnd: int
    snapshot: WindowSnapshot
    original_style: int | None
    input_thread: int = 0
    last_size: tuple[int, int] | None = None
    attached_at: float = 0.0


class WindowManager:
    def __init__(self):
        self._bindings: dict[int, ManagedWindowBinding] = {}
        self.log = get_logger("window_manager")

    def attach(
        self,
        hwnd: int,
        parent_hwnd: int,
        pane_index: int,
    ) -> ManagedWindowBinding | None:
        hwnd = int(hwnd)
        try:
            snapshot = WindowSnapshot.capture(
                hwnd,
                exe=win32_utils.get_window_exe(hwnd),
            )

            if win32_utils.get_parent(hwnd):
                fixwindows.fix_stuck_window(hwnd)

            original_style = win32_utils.embed_window(hwnd, int(parent_hwnd))
            input_thread = int(fixwindows.attach_input(hwnd) or 0)

            binding = ManagedWindowBinding(
                hwnd=hwnd,
                pane_index=int(pane_index),
                parent_hwnd=int(parent_hwnd),
                snapshot=snapshot,
                original_style=original_style,
                input_thread=input_thread,
                attached_at=time.time(),
            )
            self._bindings[hwnd] = binding

            log_event(
                self.log,
                logging.INFO,
                "window_attached",
                pane=pane_index,
                hwnd=hwnd,
                identity=snapshot.identity.to_dict(),
                original_parent=snapshot.parent,
                original_rect=snapshot.rect,
            )
            return binding
        except Exception:
            self.log.exception(
                "window_attach_failed hwnd=%s pane=%s",
                hwnd,
                pane_index,
            )
            return None

    def _detach_input(self, binding: ManagedWindowBinding) -> None:
        if binding.input_thread:
            fixwindows.detach_input(binding.input_thread)
            binding.input_thread = 0

    def take(
        self,
        binding: ManagedWindowBinding | None,
    ) -> ManagedWindowBinding | None:
        if binding is None:
            return None
        self._detach_input(binding)
        binding.last_size = None
        self._bindings.pop(binding.hwnd, None)
        return binding

    def adopt(
        self,
        binding: ManagedWindowBinding | None,
        parent_hwnd: int,
        pane_index: int,
    ) -> ManagedWindowBinding | None:
        if binding is None:
            return None

        try:
            win32_utils.embed_window(binding.hwnd, int(parent_hwnd))
            binding.parent_hwnd = int(parent_hwnd)
            binding.pane_index = int(pane_index)
            binding.input_thread = int(
                fixwindows.attach_input(binding.hwnd) or 0
            )
            binding.last_size = None
            self._bindings[binding.hwnd] = binding

            log_event(
                self.log,
                logging.INFO,
                "window_moved_between_cells",
                hwnd=binding.hwnd,
                pane=pane_index,
                parent=parent_hwnd,
            )
            return binding
        except Exception:
            self.log.exception(
                "window_adopt_failed hwnd=%s pane=%s",
                binding.hwnd,
                pane_index,
            )
            return None

    def detach(self, binding: ManagedWindowBinding | None) -> bool:
        if binding is None:
            return True

        self._detach_input(binding)
        binding.last_size = None
        self._bindings.pop(binding.hwnd, None)

        restored = False
        try:
            # Preserve compatibility with the existing backend, then restore the
            # exact state captured before embedding.
            win32_utils.release_window(binding.hwnd, binding.original_style)
            restored = binding.snapshot.restore(binding.hwnd)
        except Exception:
            self.log.exception("window_detach_failed hwnd=%s", binding.hwnd)

        log_event(
            self.log,
            logging.INFO if restored else logging.WARNING,
            "window_detached",
            hwnd=binding.hwnd,
            pane=binding.pane_index,
            exact_restore=restored,
        )
        return restored

    def forget(self, binding: ManagedWindowBinding | None) -> None:
        if binding is None:
            return
        self._detach_input(binding)
        binding.last_size = None
        self._bindings.pop(binding.hwnd, None)

    def focus(self, binding: ManagedWindowBinding | None) -> None:
        if binding is not None:
            fixwindows.focus_child(binding.hwnd)

    def resize(
        self,
        binding: ManagedWindowBinding | None,
        width: int,
        height: int,
    ) -> None:
        if binding is None:
            return

        size = (max(1, int(width)), max(1, int(height)))
        if binding.last_size == size:
            return

        win32_utils.resize_embedded(binding.hwnd, 0, 0, *size)
        binding.last_size = size

    def enforce(
        self,
        binding: ManagedWindowBinding | None,
        parent_hwnd: int,
        width: int,
        height: int,
    ) -> bool:
        if binding is None:
            return False

        width = max(1, int(width))
        height = max(1, int(height))
        alive = win32_utils.enforce_embed(
            binding.hwnd,
            int(parent_hwnd),
            width,
            height,
        )
        if not alive:
            self.forget(binding)
            return False

        binding.parent_hwnd = int(parent_hwnd)
        binding.last_size = (width, height)
        return True
