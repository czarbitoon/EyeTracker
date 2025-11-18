from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Optional, Tuple, List

import cv2
import numpy as np
import mediapipe as mp

RIGHT_IRIS_IDX = [474, 475, 476, 477]
# Right-eye key landmarks: outer corner (33), inner corner (133), upper lid (159), lower lid (145)
RIGHT_EYE_LM = [33, 133, 159, 145]


@dataclass
class RightEyeFeatures:
    iris_center: Tuple[float, float]
    eyelid_box: Tuple[int, int, int, int]
    nx: float
    ny: float
    landmarks: Optional[List[Tuple[float, float]]] = None


class RightEyeTracker:
    def __init__(self) -> None:
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self._iris_hist = deque(maxlen=5)

    def _points(self, pts, idxs: List[int], w: int, h: int) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for i in idxs:
            try:
                p = pts[i]
            except Exception:
                continue
            out.append((p.x * w, p.y * h))
        return out

    def process(self, frame, mirror: bool = True) -> Optional[RightEyeFeatures]:
        if frame is None:
            return None
        if mirror:
            frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self._mesh.process(rgb)
        if not res.multi_face_landmarks:
            return None
        pts = res.multi_face_landmarks[0].landmark
        iris = self._points(pts, RIGHT_IRIS_IDX, w, h)
        if len(iris) < 2:
            return None
        cx = float(sum(p[0] for p in iris) / len(iris))
        cy = float(sum(p[1] for p in iris) / len(iris))
        # Key landmarks
        def _pt(i):
            try:
                p = pts[i]
                return (p.x * w, p.y * h)
            except Exception:
                return None
        p_outer = _pt(33)
        p_inner = _pt(133)
        p_up = _pt(159)
        p_low = _pt(145)
        if None in (p_outer, p_inner, p_up, p_low):
            return None
        x_outer, y_outer = p_outer  # type: ignore[misc]
        x_inner, y_inner = p_inner  # type: ignore[misc]
        x_up, y_up = p_up  # type: ignore[misc]
        x_low, y_low = p_low  # type: ignore[misc]
        eye_w = max(1.0, abs(x_inner - x_outer))
        eye_h = max(1.0, abs(y_low - y_up))
        # Blink/closed-eye rejection
        if (eye_h / eye_w) < 0.15:
            return None
        # Median smoothing
        self._iris_hist.append((cx, cy))
        xs = [p[0] for p in self._iris_hist]
        ys = [p[1] for p in self._iris_hist]
        cx = float(np.median(xs))
        cy = float(np.median(ys))
        # Normalize
        nx = (cx - x_outer) / eye_w
        ny = (cy - y_up) / eye_h
        nx = float(max(0.0, min(1.0, nx)))
        ny = float(max(0.0, min(1.0, ny)))
        # Eyelid box for overlay
        m = 2
        x1 = max(0, int(min(x_outer, x_inner)) - m)
        x2 = min(w - 1, int(max(x_outer, x_inner)) + m)
        y1 = max(0, int(min(y_up, y_low)) - m)
        y2 = min(h - 1, int(max(y_up, y_low)) + m)
        lids = [(x_outer, y_outer), (x_inner, y_inner), (x_up, y_up), (x_low, y_low)]
        return RightEyeFeatures(iris_center=(cx, cy), eyelid_box=(x1, y1, x2, y2), nx=nx, ny=ny, landmarks=lids + iris)
