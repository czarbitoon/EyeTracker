"""
Gaze parsing & feature extraction using MediaPipe FaceMesh (refine_landmarks=True).

Requirements implemented:
    - Track only one face.
    - Extract RIGHT_IRIS indices [474, 475, 476, 477].
    - Extract RIGHT_LIDS indices [33, 133, 159, 145].
    - Compute iris center (average of iris landmarks).
    - Compute eyelid bounding box.
    - Normalize (nx, ny) = (iris - eyelid_min) / eyelid_size, clipped to [0,1].
    - Return None if detection fails at any step.
    - Optional debug overlay drawing (rectangle + center point).

Further improvements (TODO):
    - Perspective compensation / robust pupil center.
    - Lighting normalization.
    - Per-user adaptive calibration of normalization space.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None  # type: ignore
    mp = None  # type: ignore


RIGHT_IRIS_IDX = [474, 475, 476, 477]
RIGHT_EYE_LANDMARKS = [33, 133, 159, 145]  # eyelid bounding landmarks


@dataclass
class GazeFeatures:
    iris_center: Tuple[float, float]
    eyelid_box: Tuple[int, int, int, int]
    nx: float
    ny: float
    ear: Optional[float] = None


class GazeParser:
    def __init__(self, right_eye_only: bool = True):
        if mp is None:
            raise RuntimeError("mediapipe not installed.")
        self.right_eye_only = right_eye_only
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, frame, debug: bool = False) -> Optional[GazeFeatures]:  # frame is a BGR numpy array
        if cv2 is None or np is None:
            return None
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self._mesh.process(rgb)
        if not res.multi_face_landmarks:
            return None
        face = res.multi_face_landmarks[0]
        pts = face.landmark

        # Iris center (average of iris landmarks)
        iris_coords = self._gather_points(pts, RIGHT_IRIS_IDX, w, h)
        if len(iris_coords) < 2:  # require at least 2 points to form a center
            return None
        cx = sum(p[0] for p in iris_coords) / len(iris_coords)
        cy = sum(p[1] for p in iris_coords) / len(iris_coords)

        # Eyelid bounding box from chosen eye landmarks
        eye_coords = self._gather_points(pts, RIGHT_EYE_LANDMARKS, w, h)
        if len(eye_coords) < 2:
            return None
        xs = [p[0] for p in eye_coords]
        ys = [p[1] for p in eye_coords]
        x1, x2 = int(min(xs)), int(max(xs))
        y1, y2 = int(min(ys)), int(max(ys))
        # Expand a little margin
        margin = 2
        x1 = max(0, x1 - margin)
        y1 = max(0, y1 - margin)
        x2 = min(w - 1, x2 + margin)
        y2 = min(h - 1, y2 + margin)
        box_w = x2 - x1
        box_h = y2 - y1
        if box_w <= 0 or box_h <= 0:
            return None

        nx = (cx - x1) / box_w
        ny = (cy - y1) / box_h
        nx = float(max(0.0, min(1.0, nx)))
        ny = float(max(0.0, min(1.0, ny)))

        ear = self._compute_simple_ear(eye_coords)

        features = GazeFeatures(
            iris_center=(cx, cy),
            eyelid_box=(x1, y1, x2, y2),
            nx=nx,
            ny=ny,
            ear=ear,
        )

        if debug:
            self._draw_debug(frame, features)
        return features

    @staticmethod
    def _gather_points(pts, indices: List[int], w: int, h: int) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for i in indices:
            try:
                p = pts[i]
            except IndexError:
                continue
            out.append((p.x * w, p.y * h))
        return out

    @staticmethod
    def _compute_simple_ear(eye_coords: List[Tuple[float, float]]) -> Optional[float]:
        # Very rough eye aspect ratio proxy: vertical distance between top(159) and bottom(145)
        # divided by horizontal distance between corners (33,133), indices assumed known ordering.
        # For robust blink detection, refine later with proper EAR formula.
        if len(eye_coords) < 4:
            return None
        # Mapping by landmark index to coordinate
        # We'll just approximate using min/max y for vertical, min/max x for horizontal
        xs = [c[0] for c in eye_coords]
        ys = [c[1] for c in eye_coords]
        horiz = max(xs) - min(xs)
        vert = max(ys) - min(ys)
        if horiz <= 0:
            return None
        return vert / horiz

    @staticmethod
    def _draw_debug(frame, features: GazeFeatures) -> None:
        if cv2 is None:
            return
        x1, y1, x2, y2 = features.eyelid_box
        cx, cy = features.iris_center
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
        cv2.circle(frame, (int(cx), int(cy)), 2, (0, 0, 255), -1)
