from __future__ import annotations

"""
Minimal eye detection module for Phase 1.

Responsibilities:
- Use MediaPipe FaceMesh (preferred) to detect facial/eye landmarks
- Extract approximate eye centers (left/right) from iris landmarks
- Return (success, (left_x, left_y), (right_x, right_y), confidence)

No smoothing, cursor movement, or calibration.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import mediapipe as mp  # type: ignore
except Exception:
    mp = None  # type: ignore

try:
    import numpy as np  # type: ignore
except Exception:
    np = None  # type: ignore


RIGHT_IRIS_IDX = [474, 475, 476, 477]
LEFT_IRIS_IDX = [469, 470, 471, 472]


@dataclass
class DetectionResult:
    success: bool
    left_center: Optional[Tuple[float, float]]
    right_center: Optional[Tuple[float, float]]
    confidence: float

    @property
    def eye_centers(self) -> Tuple[Tuple[float, float], ...]:
        centers = []
        if self.left_center is not None:
            centers.append(self.left_center)
        if self.right_center is not None:
            centers.append(self.right_center)
        return tuple(centers)


class EyeDetector:
    def __init__(self) -> None:
        if mp is None:
            self._mesh = None
        else:
            try:
                self._mesh = mp.solutions.face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
            except Exception:
                self._mesh = None

    def close(self) -> None:
        try:
            if self._mesh is not None:
                self._mesh.close()  # type: ignore[attr-defined]
        except Exception:
            pass
        self._mesh = None

    def detect(self, frame) -> DetectionResult:
        """Detect eye centers in the given BGR frame.

        Returns a DetectionResult with success flag, left/right centers, and a
        simple confidence score (0-1). If MediaPipe is unavailable, returns
        success=False.
        """
        if self._mesh is None or frame is None:
            return DetectionResult(False, None, None, 0.0)
        try:
            import cv2  # type: ignore
        except Exception:
            return DetectionResult(False, None, None, 0.0)

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = None
        try:
            res = self._mesh.process(rgb)
        except Exception:
            return DetectionResult(False, None, None, 0.0)
        if not res or not res.multi_face_landmarks:
            return DetectionResult(False, None, None, 0.0)
        face = res.multi_face_landmarks[0]
        pts = face.landmark

        def _mean_xy(indices) -> Optional[Tuple[float, float]]:
            xs = []
            ys = []
            for i in indices:
                try:
                    p = pts[i]
                    xs.append(p.x * w)
                    ys.append(p.y * h)
                except Exception:
                    return None
            if not xs or not ys:
                return None
            if np is not None:
                cx = float(np.mean(xs))
                cy = float(np.mean(ys))
            else:
                cx = float(sum(xs) / len(xs))
                cy = float(sum(ys) / len(ys))
            return (cx, cy)

        right_c = _mean_xy(RIGHT_IRIS_IDX)
        left_c = _mean_xy(LEFT_IRIS_IDX)
        if right_c is None and left_c is None:
            return DetectionResult(False, None, None, 0.0)
        # Basic confidence: presence of iris landmarks + normalized distance sanity
        conf = 0.5
        try:
            if right_c is not None and left_c is not None:
                dx = abs(right_c[0] - left_c[0])
                if dx > 5:  # eyes should be separated
                    conf = 0.8
        except Exception:
            pass
        return DetectionResult(True, left_c, right_c, conf)
