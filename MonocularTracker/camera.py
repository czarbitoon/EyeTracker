"""
Camera abstraction using OpenCV VideoCapture.

Requirements covered:
- Opens default webcam (index 0 by default)
- Sets resolution to 1280x720 (720p), with fallback if unsupported
- read() returns BGR frames (OpenCV default)
- Graceful shutdown and error handling
- Consistent FPS via software pacing (target_fps)
"""
from __future__ import annotations

import time
from typing import Optional, Tuple

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None


class Camera:
    def __init__(
        self,
        index: int = 0,
        width: int = 1280,
        height: int = 720,
        target_fps: int = 30,
    ) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.target_fps = max(1, int(target_fps))
        self._frame_interval = 1.0 / float(self.target_fps)
        self._last_time = 0.0
        self.cap = None

    def open(self) -> None:
        if cv2 is None:
            raise RuntimeError("OpenCV (cv2) is not installed.")
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)  # CAP_DSHOW for Windows stability
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera index {self.index}")
        # Try to set 720p resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        # Best-effort FPS hint (camera/driver may ignore)
        try:
            self.cap.set(cv2.CAP_PROP_FPS, float(self.target_fps))
        except Exception:
            pass
        # Verify and store actual resolution
        try:
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if actual_w > 0 and actual_h > 0:
                self.width, self.height = actual_w, actual_h
        except Exception:
            pass
        self._last_time = time.perf_counter()

    def read(self) -> Optional[object]:  # Returns a BGR numpy array or None on failure
        if self.cap is None:
            return None
        # Software pacing to achieve consistent FPS
        now = time.perf_counter()
        elapsed = now - self._last_time
        remaining = self._frame_interval - elapsed
        if remaining > 0:
            # Sleep a bit to maintain target frame interval
            time.sleep(remaining)
        self._last_time = time.perf_counter()

        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        # OpenCV returns BGR by default; ensure it's contiguous
        try:
            return frame
        except Exception:
            return None

    def close(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            finally:
                self.cap = None

    @property
    def is_open(self) -> bool:
        return bool(self.cap is not None and getattr(self.cap, "isOpened", lambda: False)())

    def set_fps(self, fps: int) -> None:
        """Update pacing FPS (software interval); attempts to set camera hint too."""
        self.target_fps = max(1, int(fps))
        self._frame_interval = 1.0 / float(self.target_fps)
        if self.cap is not None:
            try:
                self.cap.set(cv2.CAP_PROP_FPS, float(self.target_fps))
            except Exception:
                pass

