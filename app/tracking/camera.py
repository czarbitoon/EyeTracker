from __future__ import annotations

"""
Minimal camera feed module for Phase 1 (Controlled Migration).

Responsibilities:
- Open a webcam
- Read frames at a fixed target FPS using a monotonic clock
- Close cleanly

No gaze, no UI, no calibration, no JSON, no smoothing.
"""
import time
from typing import Optional

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None


class Camera:
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720, target_fps: int = 30) -> None:
        self.index = int(index)
        self.width = int(width)
        self.height = int(height)
        self.target_fps = max(1, int(target_fps))
        self._frame_interval = 1.0 / float(self.target_fps)
        self._last_time = 0.0
        self.cap = None

    def start(self) -> bool:
        if cv2 is None:
            return False
        cap = cv2.VideoCapture(self.index)
        if not cap or not cap.isOpened():
            return False
        # Best-effort resolution hint
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        except Exception:
            pass
        # Best-effort FPS hint
        try:
            cap.set(cv2.CAP_PROP_FPS, float(self.target_fps))
        except Exception:
            pass
        self.cap = cap
        self._last_time = time.perf_counter()
        return True

    def read(self) -> tuple[bool, Optional[object]]:
        if self.cap is None:
            return False, None
        # Pace to target FPS using a monotonic clock
        now = time.perf_counter()
        elapsed = now - self._last_time
        remaining = self._frame_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_time = time.perf_counter()
        ok, frame = self.cap.read()
        if not ok:
            return False, None
        return True, frame

    def stop(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            finally:
                self.cap = None

    @property
    def is_open(self) -> bool:
        return bool(self.cap is not None and getattr(self.cap, "isOpened", lambda: False)())
