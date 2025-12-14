from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

from app.tracking.smoothing import ButterworthLowPass

# For initial migration, reuse existing parser and calibration mapping
from MonocularTracker.camera import Camera
from MonocularTracker.tracking.gaze_parser import GazeParser
from MonocularTracker.tracking.mapping import Mapping

@dataclass
class FrameResult:
    frame: Optional[object]
    face_ok: bool
    eye_ok: bool
    predicted_xy: Optional[Tuple[int, int]]
    features: Optional[object]

class MonocularTracker:
    def __init__(self, camera_index: int, screen_size: Tuple[int, int], drift_enabled: bool, drift_lr: float, eye_mode: str = "auto") -> None:
        self.cam = Camera(index=camera_index, width=1280, height=720, target_fps=30)
        self.parser = GazeParser(eye_mode=eye_mode)
        sr_hz = float(getattr(self.cam, "target_fps", 30))
        self.smoother = ButterworthLowPass(sample_rate_hz=sr_hz)
        # Mapping with sampling rate for internal smoothing stages; we will call map_only for strict order
        self.map = Mapping(alpha=0.25, drift_enabled=drift_enabled, drift_lr=drift_lr, sample_rate_hz=sr_hz)
        self.screen_size = screen_size
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.cam.open()
        self.running = True

    def stop(self) -> None:
        if not self.running:
            return
        self.cam.close()
        self.running = False

    def frame(self) -> Optional[object]:
        if not self.running:
            return None
        return self.cam.read()

    def process(self) -> FrameResult:
        frame_interval = 1.0 / float(getattr(self.cam, "target_fps", 30))
        start_t = time.perf_counter()
        fr = self.frame()
        if fr is None:
            elapsed = time.perf_counter() - start_t
            remaining = frame_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            return FrameResult(frame=None, face_ok=False, eye_ok=False, predicted_xy=None, features=None)
        feats = self.parser.process(fr)
        if feats is None:
            elapsed = time.perf_counter() - start_t
            remaining = frame_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            return FrameResult(frame=fr, face_ok=False, eye_ok=False, predicted_xy=None, features=None)
        # Validate detection
        nx = float(feats.nx); ny = float(feats.ny)
        if not (math.isfinite(nx) and math.isfinite(ny)):
            elapsed = time.perf_counter() - start_t
            remaining = frame_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            return FrameResult(frame=fr, face_ok=True, eye_ok=False, predicted_xy=None, features=feats)
        # Smooth normalized
        snx, sny = self.smoother.apply_float((nx, ny))
        snx = max(0.0, min(1.0, snx)); sny = max(0.0, min(1.0, sny))
        # Map to screen
        x, y = self.map.map_only((snx, sny))
        # Pace
        elapsed = time.perf_counter() - start_t
        remaining = frame_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        return FrameResult(frame=fr, face_ok=True, eye_ok=True, predicted_xy=(x, y), features=feats)
