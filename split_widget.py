# -*- coding: utf-8 -*-
"""带吸附折叠的分隔容器：拖动时某个面板收缩进阈值区间即吸附到 0（VSCode 风格）。"""
from PySide6.QtWidgets import QSplitter


class SnapSplitter(QSplitter):
    def __init__(self, orientation, threshold=160, on_resize=None, parent=None):
        super().__init__(orientation, parent)
        self._threshold = max(0, int(threshold))
        self._on_resize = on_resize
        self._guard = False
        self._last = None
        self.setChildrenCollapsible(True)   # 允许拖到底（0）
        self.setOpaqueResize(True)          # 实时跟随
        self.splitterMoved.connect(self._on_moved)

    def set_threshold(self, t):
        self._threshold = max(0, int(t))

    def sync_last(self):
        """记录当前尺寸，作为下次判断收缩/展开的基准。"""
        self._last = self.sizes()

    def set_sizes_synced(self, sizes):
        """静默设置尺寸（用于列联动），不触发吸附逻辑。"""
        self._guard = True
        self.setSizes(sizes)
        self._guard = False
        self._last = self.sizes()

    def _on_moved(self, pos, index):
        if self._guard:
            return
        sizes = self.sizes()
        last = self._last if (self._last and len(self._last) == len(sizes)) else sizes
        th = self._threshold
        new = sizes[:]
        changed = False

        # 被拖动的 handle 分隔 widget[index-1] 与 widget[index]
        for i in (index - 1, index):
            if 0 <= i < len(sizes):
                shrinking = sizes[i] < last[i]
                # 仅在“正在收缩”且落入 (0, 阈值) 时吸附到 0
                if shrinking and 0 < sizes[i] < th:
                    other = index if i == index - 1 else index - 1
                    if 0 <= other < len(new):
                        new[other] += new[i]
                        new[i] = 0
                        changed = True

        if changed:
            self._guard = True
            self.setSizes(new)
            self._guard = False
            self._last = new
        else:
            self._last = sizes

        if self._on_resize:
            self._on_resize()
