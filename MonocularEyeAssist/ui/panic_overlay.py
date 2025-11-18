from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QWidget


class PanicOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Panic Mode Activated")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.showFullScreen()

    def paintEvent(self, e):  # type: ignore[override]
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(200, 0, 0, 120))
        p.end()
