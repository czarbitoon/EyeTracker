from __future__ import annotations

from typing import Optional, Tuple

import cv2


class Camera:
    def __init__(self, index: int, width: int = 1280, height: int = 720, fps: int = 30) -> None:
        self.index = int(index)
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        for backend in (cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY):
            try:
                self.cap = cv2.VideoCapture(self.index, backend)
                if self.cap and self.cap.isOpened():
                    break
            except Exception:
                self.cap = None
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("Failed to open camera")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if self.fps > 0:
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def set_brightness(self, v: float) -> None:
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, float(v))

    def set_exposure(self, v: float) -> None:
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, float(v))

    def read(self):
        if not self.cap:
            return None
        ok, frame = self.cap.read()
        if not ok:
            return None
        return frame

    def close(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None
