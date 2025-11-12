"""
Overlay UI to visualize gaze point and eye box for debugging.
Note: Transparent always-on-top window; deliberately minimal for scaffold.
"""
from __future__ import annotations

from typing import Optional, Tuple

try:
    from PyQt6.QtCore import Qt, QPoint
    from PyQt6.QtGui import QPainter, QColor
    from PyQt6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class Overlay(QWidget):
    def __init__(self):  # type: ignore[no-redef]
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 300)
        self.move(20, 20)
        self._gaze: Optional[Tuple[int, int]] = None

        self.show()

    def update_gaze(self, screen_xy: Tuple[int, int], _features) -> None:
        self._gaze = (int(screen_xy[0]), int(screen_xy[1]))
        self.update()

    def paintEvent(self, event):  # type: ignore[override]
        if self._gaze is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(0, 255, 0, 200))
        painter.setBrush(QColor(0, 255, 0, 60))
        # Draw a simple circle at the last gaze position relative to this window
        # For full-screen overlay, this widget would cover the screen & draw at absolute position.
        x, y = self._gaze
        x -= self.x()
        y -= self.y()
        r = 10
        painter.drawEllipse(QPoint(int(x), int(y)), r, r)
        painter.end()
