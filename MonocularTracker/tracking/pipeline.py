from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from MonocularTracker.camera import Camera
from .gaze_parser import GazeParser
from .mapping import Mapping


@dataclass
class FrameResult:
    frame: Optional[object]
    face_ok: bool
    eye_ok: bool
    predicted_xy: Optional[Tuple[int, int]]
    features: Optional[object]


class Pipeline:
    def __init__(self, camera_index: int, screen_size: Tuple[int, int], alpha: float, drift_enabled: bool, drift_lr: float, eye_mode: str = "auto") -> None:
        self.cam = Camera(index=camera_index, width=1280, height=720, target_fps=30)
        self.parser = GazeParser(eye_mode=eye_mode)
        self.map = Mapping(alpha=alpha, drift_enabled=drift_enabled, drift_lr=drift_lr)
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
        fr = self.frame()
        if fr is None:
            return FrameResult(frame=None, face_ok=False, eye_ok=False, predicted_xy=None, features=None)
        feats = self.parser.process(fr)
        if feats is None:
            return FrameResult(frame=fr, face_ok=False, eye_ok=False, predicted_xy=None, features=None)
        x, y = self.map.predict_stable((feats.nx, feats.ny), self.screen_size)
        return FrameResult(frame=fr, face_ok=True, eye_ok=True, predicted_xy=(x, y), features=feats)
