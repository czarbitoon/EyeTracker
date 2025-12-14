from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import time

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from app.camera import Camera
from .gaze_parser import GazeParser
from .mapping import Mapping
from .smoothing import ButterworthLowPass
try:
    from app.ai.openvino_gaze import OpenVinoGaze  # type: ignore
except Exception:
    OpenVinoGaze = None  # type: ignore


@dataclass
class FrameResult:
    frame: Optional[object]
    face_ok: bool
    eye_ok: bool
    predicted_xy: Optional[Tuple[int, int]]
    features: Optional[object]


class Pipeline:
    def __init__(self, camera_index: int, screen_size: Tuple[int, int], alpha: float, drift_enabled: bool, drift_lr: float, eye_mode: str = "auto", gaze_engine: str = "landmark", model_dir: str | None = None) -> None:
        self.cam = Camera(index=camera_index, width=1280, height=720, target_fps=30)
        self.parser = GazeParser(eye_mode=eye_mode)
        # Derive sampling rate for smoothing from camera FPS
        sr_hz = float(getattr(self.cam, "target_fps", 30))
        self.map = Mapping(alpha=alpha, drift_enabled=drift_enabled, drift_lr=drift_lr, sample_rate_hz=sr_hz)
        # Butterworth smoother for normalized coords (pre-mapping)
        self._norm_lp = ButterworthLowPass(sample_rate_hz=sr_hz)
        self.screen_size = screen_size
        self.running = False
        self._gaze_engine = str(gaze_engine or "landmark")
        self._ov: OpenVinoGaze | None = None  # type: ignore[assignment]
        if OpenVinoGaze is not None and self._gaze_engine in ("openvino", "hybrid"):
            try:
                self._ov = OpenVinoGaze(model_dir=model_dir)
            except Exception:
                self._ov = None

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
        # Enforce fixed FPS pacing around processing
        frame_interval = 1.0 / float(getattr(self.cam, "target_fps", 30))
        start_t = time.perf_counter()
        fr = self.frame()
        if fr is None:
            # If frame read failed, wait remaining interval to maintain cadence
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
        # Strict order without branching:
        # 1) Capture frame (done)
        # 2) Detect face/eyes (feats)
        # 3) Validate detection confidence
        nx = float(feats.nx)
        ny = float(feats.ny)
        import math
        if not (math.isfinite(nx) and math.isfinite(ny)):
            elapsed = time.perf_counter() - start_t
            remaining = frame_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            return FrameResult(frame=fr, face_ok=True, eye_ok=False, predicted_xy=None, features=feats)
        # 4) Apply Butterworth smoothing (normalized coords)
        snx, sny = self._norm_lp.apply_float((nx, ny))
        # Clamp normalized to [0,1]
        snx = max(0.0, min(1.0, float(snx)))
        sny = max(0.0, min(1.0, float(sny)))
        # 5) Map to screen coordinates (direct mapping only)
        x, y = self.map.map_only((snx, sny))
        # 6) Output cursor position
        # Pacing: if processing finished early, sleep remaining; if exceeded budget, skip sleep (drop cadence)
        elapsed = time.perf_counter() - start_t
        remaining = frame_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        return FrameResult(frame=fr, face_ok=True, eye_ok=True, predicted_xy=(x, y), features=feats)
