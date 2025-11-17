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
import os

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
        # Try multiple backends and indices for robustness on Windows
        # Allow override via env EYETRACKER_CAMERA_BACKEND = dshow|msmf|any
        preferred = (os.environ.get("EYETRACKER_CAMERA_BACKEND", "") or "").strip().lower()
        be_list = []
        try:
            dshow = getattr(cv2, "CAP_DSHOW", None)
            ms_f = getattr(cv2, "CAP_MSMF", None)
            anyb = getattr(cv2, "CAP_ANY", None)
        except Exception:
            dshow = None
            ms_f = None
            anyb = None
        def add_be(x):
            if x is not None and x not in be_list:
                be_list.append(x)
        if preferred == "dshow":
            add_be(dshow); add_be(ms_f); add_be(anyb)
        elif preferred == "msmf":
            add_be(ms_f); add_be(dshow); add_be(anyb)
        elif preferred == "any":
            add_be(anyb); add_be(dshow); add_be(ms_f)
        else:
            add_be(dshow); add_be(ms_f); add_be(anyb)
        # Fallback if none resolved
        if not be_list:
            try:
                be_list = [cv2.CAP_ANY]
            except Exception:
                be_list = [0]

        tried = []
        candidate_indices = [int(self.index)] + [i for i in range(0, 11) if i != int(self.index)]

        opened = False
        for idx in candidate_indices:
            for be in be_list:
                try:
                    cap = cv2.VideoCapture(idx, be)
                    tried.append((idx, be))
                    if cap is None or not cap.isOpened():
                        if cap is not None:
                            cap.release()
                        continue
                    # We have a camera device opened; accept and continue
                    self.cap = cap
                    self.index = int(idx)
                    opened = True
                    break
                except Exception:
                    continue
            if opened:
                break

        if not opened:
            # Helpful message for Windows camera privacy and exclusive access
            tried_text = ", ".join([f"{i}:{be}" for (i, be) in tried]) or "(none)"
            msg = (
                "No camera detected. Tried indices 0-10 with backends.\n"
                f"Tried: {tried_text}\n"
                "Tips: Close other apps using the camera; then check Windows Settings > Privacy & security > Camera,\n"
                "ensure 'Camera access' and 'Let desktop apps access your camera' are enabled.\n"
                "You can also force a backend via EYETRACKER_CAMERA_BACKEND=msmf|dshow|any before launching."
            )
            raise RuntimeError(msg)

        # Try to set desired resolution
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        except Exception:
            pass
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

        # Some cameras need a couple of reads to warm up; retry briefly
        tries = 0
        frame = None
        ok = False
        while tries < 3:
            ok, frame = self.cap.read()
            if ok and frame is not None:
                break
            tries += 1
            time.sleep(0.01)
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

