from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None  # type: ignore
    mp = None  # type: ignore


RIGHT_IRIS_IDX = [474, 475, 476, 477]
RIGHT_EYE_LANDMARKS = [33, 133, 159, 145]


@dataclass
class Features:
    iris_center: Tuple[float, float]
    eyelid_box: Tuple[int, int, int, int]
    nx: float
    ny: float
    landmarks: Optional[List[Tuple[float, float]]] = None


class GazeParser:
    def __init__(self, right_eye_only: bool = True) -> None:
        if mp is None:
            raise RuntimeError("mediapipe not installed.")
        self.right_eye_only = right_eye_only
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5
        )

    def process(self, frame) -> Optional[Features]:
        if cv2 is None or frame is None:
            return None
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self._mesh.process(rgb)
        if not res.multi_face_landmarks:
            return None
        face = res.multi_face_landmarks[0]
        pts = face.landmark

        iris = self._points(pts, RIGHT_IRIS_IDX, w, h)
        if len(iris) < 2:
            return None
        cx = sum(p[0] for p in iris) / len(iris)
        cy = sum(p[1] for p in iris) / len(iris)

        lids = self._points(pts, RIGHT_EYE_LANDMARKS, w, h)
        if len(lids) < 2:
            return None
        xs = [p[0] for p in lids]
        ys = [p[1] for p in lids]
        x1, x2 = int(min(xs)), int(max(xs))
        y1, y2 = int(min(ys)), int(max(ys))
        # small margin
        m = 2
        x1 = max(0, x1 - m)
        y1 = max(0, y1 - m)
        x2 = min(w - 1, x2 + m)
        y2 = min(h - 1, y2 + m)
        bw, bh = x2 - x1, y2 - y1
        if bw <= 0 or bh <= 0:
            return None

        nx = (cx - x1) / bw
        ny = (cy - y1) / bh
        nx = float(max(0.0, min(1.0, nx)))
        ny = float(max(0.0, min(1.0, ny)))

        # return minimal landmarks for overlay (right eye region only)
        landmarks = lids + iris
        return Features(iris_center=(cx, cy), eyelid_box=(x1, y1, x2, y2), nx=nx, ny=ny, landmarks=landmarks)

    @staticmethod
    def _points(pts, idxs: List[int], w: int, h: int) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for i in idxs:
            try:
                p = pts[i]
            except Exception:
                continue
            out.append((p.x * w, p.y * h))
        return out
