"""全局拖拽监听：把外部普通窗口拖入容器空槽时吸附嵌入。

原理（轮询）：
- 左键按下瞬间，若前台窗口是未嵌入的可嵌入普通窗口，记为候选。
- 拖动过程中若该窗口位置发生明显移动，才判定为"正在拖动窗口"，
  以此避免在编辑器内选择文字被误判。
- 拖动中根据光标所在的空槽屏幕区域发出 hover 高亮信号。
- 松开左键时，若光标落在某空槽内，发出 drop 嵌入信号。
"""
import win32api
import win32gui
from PySide6.QtCore import QObject, QPoint, QTimer, Signal

import win32_utils

VK_LBUTTON = 0x01


class DragWatcher(QObject):
    hover = Signal(int)        # 当前悬停的空槽 index，-1 表示无
    drop = Signal(int, int)    # (hwnd, cell_index)

    def __init__(self, grid_window):
        super().__init__()
        self.gw = grid_window
        self.timer = QTimer(self)
        self.timer.setInterval(70)
        self.timer.timeout.connect(self._tick)
        self.was_down = False
        self.candidate = None
        self.start_rect = None
        self.moving = False
        self.current_hover = -1

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def _reset(self):
        self.candidate = None
        self.start_rect = None
        self.moving = False
        if self.current_hover != -1:
            self.current_hover = -1
            self.hover.emit(-1)

    def _is_embedded(self, hwnd):
        return any(c.child_hwnd == hwnd for c in self.gw.cells)

    def _cell_at_cursor(self):
        try:
            x, y = win32api.GetCursorPos()
        except Exception:
            return -1
        for cell in self.gw.cells:
            if cell.child_hwnd is not None:
                continue
            top_left = cell.host.mapToGlobal(QPoint(0, 0))
            w = cell.host.width()
            h = cell.host.height()
            if (top_left.x() <= x <= top_left.x() + w
                    and top_left.y() <= y <= top_left.y() + h):
                return cell.index
        return -1

    def _tick(self):
        down = win32api.GetKeyState(VK_LBUTTON) < 0

        if down and not self.was_down:
            fg = win32gui.GetForegroundWindow()
            if win32_utils.is_embeddable_window(fg) and not self._is_embedded(fg):
                self.candidate = fg
                self.start_rect = win32_utils.get_window_rect(fg)
                self.moving = False

        if down and self.candidate:
            rect = win32_utils.get_window_rect(self.candidate)
            if rect and self.start_rect:
                if (abs(rect[0] - self.start_rect[0]) > 8
                        or abs(rect[1] - self.start_rect[1]) > 8):
                    self.moving = True
            if self.moving:
                idx = self._cell_at_cursor()
                if idx != self.current_hover:
                    self.current_hover = idx
                    self.hover.emit(idx)

        if not down and self.was_down:
            if self.candidate and self.moving and self.current_hover >= 0:
                self.drop.emit(self.candidate, self.current_hover)
            self._reset()

        self.was_down = down
