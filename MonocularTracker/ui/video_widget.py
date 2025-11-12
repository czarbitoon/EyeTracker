from __future__ import annotations

from typing import Optional, Tuple

try:
    from PyQt6.QtCore import Qt, QPoint
    from PyQt6.QtGui import QImage, QPainter, QColor, QPen
    from PyQt6.QtWidgets import QWidget
    import numpy as np  # type: ignore
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore
    QImage = object  # type: ignore
    QPainter = object  # type: ignore
    QColor = object  # type: ignore
    QPen = object  # type: ignore
    np = None  # type: ignore
    cv2 = None  # type: ignore


class VideoWidget(QWidget):  # type: ignore[misc]
    def __init__(self):  # type: ignore[no-redef]
        super().__init__()
        self._frame = None
        self._landmarks = None
        self._iris = None
        self._box = None
        self._pred = None
        self._show_landmarks = True
        self._show_vector = True
        self._show_pred = True
        self.setMinimumSize(640, 360)

    def set_overlays(self, *, frame, landmarks=None, iris_center: Optional[Tuple[float, float]] = None, eyelid_box=None, predicted: Optional[Tuple[int, int]] = None, show_landmarks=True, show_vector=True, show_pred=True) -> None:
        self._frame = frame
        self._landmarks = landmarks
        self._iris = iris_center
        self._box = eyelid_box
        self._pred = predicted
        self._show_landmarks = show_landmarks
        self._show_vector = show_vector
        self._show_pred = show_pred
        self.update()

    def paintEvent(self, e):  # type: ignore[override]
        if self._frame is None or QImage is object:
            return
        img = self._to_qimage(self._frame)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        # scale to fit while keeping aspect
        target = self.rect()
        pix = img.scaled(target.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        # center
        x = target.x() + (target.width() - pix.width()) // 2
        y = target.y() + (target.height() - pix.height()) // 2
        painter.drawImage(x, y, pix)

        # compute scale ratio between frame and drawn size to map overlay
        fh = img.height()
        fw = img.width()
        if fw <= 0 or fh <= 0:
            painter.end()
            return
        scale = min(target.width() / fw, target.height() / fh)
        ox = x
        oy = y

        # overlays
        pen = QPen(QColor(0, 255, 0), 2)
        painter.setPen(pen)
        if self._box is not None:
            bx1, by1, bx2, by2 = self._box
            painter.drawRect(ox + int(bx1 * scale), oy + int(by1 * scale), int((bx2 - bx1) * scale), int((by2 - by1) * scale))
        if self._landmarks is not None and self._show_landmarks:
            pen = QPen(QColor(0, 200, 255), 2)
            painter.setPen(pen)
            for lx, ly in self._landmarks:
                painter.drawPoint(ox + int(lx * scale), oy + int(ly * scale))
        if self._iris is not None:
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            painter.drawEllipse(QPoint(ox + int(self._iris[0] * scale), oy + int(self._iris[1] * scale)), 3, 3)
        if self._pred is not None and self._show_pred:
            pen = QPen(QColor(255, 255, 0), 2)
            painter.setPen(pen)
            # just show as a small dot near top-left corner of video region to indicate mapping exists
            painter.drawEllipse(QPoint(ox + 10, oy + 10), 4, 4)
        painter.end()

    @staticmethod
    def _to_qimage(frame):
        if cv2 is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
