"""
Fullscreen PyQt6 calibration UI showing large circular targets in sequence:
center, top-left, top-right, bottom-left, bottom-right.

Behavior:
- Emits sampleRequested((x,y)) repeatedly while each target is active.
- Waits 1500ms at each target and collects ~20–30 samples (configurable).
- Emits calibrationFinished and closes automatically when done.
"""
from __future__ import annotations

from typing import List, Tuple

try:
    from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QRect
    from PyQt6.QtGui import QPainter, QColor, QGuiApplication
    from PyQt6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore
    pyqtSignal = lambda *a, **k: None  # type: ignore
    QTimer = object  # type: ignore
    Qt = object  # type: ignore
    QRect = object  # type: ignore
    QGuiApplication = object  # type: ignore


class CalibrationUI(QWidget):  # type: ignore[misc]
    sampleRequested = pyqtSignal(tuple)  # (x,y)
    calibrationFinished = pyqtSignal()

    def __init__(
        self,
        points_count: int | None = None,  # 5 or 9 points supported (None->5)
        samples_per_point: int = 25,
        dwell_ms: int = 1500,
        radius_px: int = 34,
        margin_ratio: float = 0.08,  # bring corner points inward a bit
    ):  # type: ignore[no-redef]
        super().__init__()
        self.samples_per_point = int(max(1, samples_per_point))
        self.dwell_ms = int(max(1, dwell_ms))
        self.radius_px = radius_px
        self.margin_ratio = margin_ratio
        self._requested_points = int(points_count or 5)

        # Runtime state
        self.targets: List[Tuple[int, int]] = []
        self._active_index = -1
        self._samples_emitted = 0
        self._point_timer = None  # type: ignore[assignment]
        self._sample_timer = None  # type: ignore[assignment]

        # Visuals
        try:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
        except Exception:
            pass
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        except Exception:
            pass

    # -----------------
    # Public API
    # -----------------
    def start(self) -> None:
        if not isinstance(self, QWidget):
            return
        self._compute_targets()
        self._active_index = 0
        self._samples_emitted = 0
        try:
            self.showFullScreen()
        except Exception:
            self.show()
        self._begin_point()

    # -----------------
    # Internals
    # -----------------
    def _compute_targets(self) -> None:
        self.targets.clear()
        try:
            screen = QGuiApplication.primaryScreen()
            geom = screen.geometry()  # type: ignore[attr-defined]
            sw, sh = geom.width(), geom.height()
            mx = int(sw * self.margin_ratio)
            my = int(sh * self.margin_ratio)
        except Exception:
            # Fallback values
            sw, sh = 1920, 1080
            mx, my = int(sw * self.margin_ratio), int(sh * self.margin_ratio)

        center = (sw // 2, sh // 2)
        tl = (mx, my)
        tr = (sw - mx, my)
        bl = (mx, sh - my)
        br = (sw - mx, sh - my)
        pts = [center, tl, tr, bl, br]
        # optional 9-point: add midpoints of edges
        if self._requested_points == 9:
            top = ((tl[0] + tr[0]) // 2, my)
            bottom = ((bl[0] + br[0]) // 2, sh - my)
            left = (mx, (tl[1] + bl[1]) // 2)
            right = (sw - mx, (tr[1] + br[1]) // 2)
            pts.extend([top, bottom, left, right])
        self.targets.extend(pts)
        self._screen_size = (sw, sh)

    def _begin_point(self) -> None:
        # Start timers for samples and for point duration
        if self._active_index < 0 or self._active_index >= len(self.targets):
            self._finish_all()
            return
        self._samples_emitted = 0
        interval = max(1, int(self.dwell_ms / max(1, self.samples_per_point)))
        # Sample timer
        self._sample_timer = QTimer()
        self._sample_timer.setInterval(interval)
        self._sample_timer.timeout.connect(self._on_sample_tick)  # type: ignore[attr-defined]
        self._sample_timer.start()
        # Point duration timer
        self._point_timer = QTimer()
        self._point_timer.setSingleShot(True)
        self._point_timer.setInterval(self.dwell_ms)
        self._point_timer.timeout.connect(self._on_point_done)  # type: ignore[attr-defined]
        self._point_timer.start()
        self.update()

    def _on_sample_tick(self) -> None:
        if self._active_index < 0 or self._active_index >= len(self.targets):
            return
        target = self.targets[self._active_index]
        self.sampleRequested.emit(target)  # type: ignore[attr-defined]
        self._samples_emitted += 1
        if self._samples_emitted >= self.samples_per_point:
            # Stop emitting further samples for this point; wait for dwell end
            if self._sample_timer:
                self._sample_timer.stop()

    def _on_point_done(self) -> None:
        if self._sample_timer:
            self._sample_timer.stop()
        self._active_index += 1
        if self._active_index >= len(self.targets):
            self._finish_all()
            return
        self._begin_point()

    def _finish_all(self) -> None:
        self.calibrationFinished.emit()  # type: ignore[attr-defined]
        try:
            self.close()
        except Exception:
            try:
                self.hide()
            except Exception:
                pass

    # -----------------
    # Painting
    # -----------------
    def paintEvent(self, event):  # type: ignore[override]
        if not isinstance(self, QWidget):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Dim background
        try:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 200))
        except Exception:
            pass
        # Draw current target
        if 0 <= self._active_index < len(self.targets):
            x, y = self.targets[self._active_index]
            r = self.radius_px
            painter.setBrush(QColor(255, 0, 0, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawEllipse(x - r, y - r, r * 2, r * 2)
        painter.end()
