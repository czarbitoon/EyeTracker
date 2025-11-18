from __future__ import annotations

import math
from typing import List, Tuple, Callable

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QWidget


class CalibrationUI(QWidget):
    sampleRequested = pyqtSignal(tuple)  # (x,y)
    finished = pyqtSignal()

    def __init__(self, screen_size: Tuple[int, int], points: int = 9, dwell_ms: int = 2500, radius: int = 60):
        super().__init__()
        self.setWindowTitle("Calibration")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.showFullScreen()
        self.screen = screen_size
        self.points = self._grid_points(points)
        self.idx = -1
        self.radius = int(radius)
        self.timer = QTimer(self)
        self.timer.setInterval(int(dwell_ms))
        self.timer.timeout.connect(self._next)
        self._next()

    def _grid_points(self, n: int) -> List[Tuple[int, int]]:
        w, h = self.screen
        # 5 or 9 point grid (corners + center or 9 grid)
        if n <= 5:
            return [
                (int(w*0.1), int(h*0.1)),
                (int(w*0.9), int(h*0.1)),
                (int(w*0.5), int(h*0.5)),
                (int(w*0.1), int(h*0.9)),
                (int(w*0.9), int(h*0.9)),
            ]
        return [
            (int(w*0.1), int(h*0.1)), (int(w*0.5), int(h*0.1)), (int(w*0.9), int(h*0.1)),
            (int(w*0.1), int(h*0.5)), (int(w*0.5), int(h*0.5)), (int(w*0.9), int(h*0.5)),
            (int(w*0.1), int(h*0.9)), (int(w*0.5), int(h*0.9)), (int(w*0.9), int(h*0.9)),
        ]

    def _next(self):
        self.idx += 1
        if self.idx >= len(self.points):
            self.timer.stop()
            self.close()
            self.finished.emit()
            return
        self.update()

    def paintEvent(self, e):  # type: ignore[override]
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0))
        if 0 <= self.idx < len(self.points):
            x, y = self.points[self.idx]
            p.setBrush(QColor(255, 255, 255))
            p.setPen(Qt.NoPen)
            p.drawEllipse(x - self.radius, y - self.radius, self.radius*2, self.radius*2)
        p.end()
        # Inform sampler to collect for current point
        if 0 <= self.idx < len(self.points):
            self.sampleRequested.emit(self.points[self.idx])
