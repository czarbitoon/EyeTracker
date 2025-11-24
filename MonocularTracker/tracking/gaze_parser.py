from __future__ import annotations

from dataclasses import dataclass
from collections import deque
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
LEFT_IRIS_IDX = [469, 470, 471, 472]
LEFT_EYE_LANDMARKS = [263, 362, 386, 374]


@dataclass
class Features:
    iris_center: Tuple[float, float]
    eyelid_box: Tuple[int, int, int, int]
    nx: float
    ny: float
    landmarks: Optional[List[Tuple[float, float]]] = None
    eye: str = "right"  # 'right'|'left'


class GazeParser:
    def __init__(self, eye_mode: str = "auto") -> None:
        if mp is None:
            raise RuntimeError("mediapipe not installed.")
        self.eye_mode = eye_mode if eye_mode in ("auto", "right", "left") else "auto"
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        # For auto mode, track recent movement per eye to pick the stronger signal
        self._hist_right = deque(maxlen=30)
        self._hist_left = deque(maxlen=30)
        # Median smoothing for iris centers
        self._iris_hist_right = deque(maxlen=5)
        self._iris_hist_left = deque(maxlen=5)
        # Last normalized coords for soft delta-clamp per eye
        self._last_norm_right: Optional[Tuple[float, float]] = None
        self._last_norm_left: Optional[Tuple[float, float]] = None

    def set_mode(self, mode: str) -> None:
        self.eye_mode = mode if mode in ("auto", "right", "left") else "auto"

    def _extract_eye(self, pts, iris_idx, lid_idx, w: int, h: int, tag: str) -> Optional[Features]:
        iris = self._points(pts, iris_idx, w, h)
        if len(iris) < 2:
            return None
        # Raw iris center (mean of iris points)
        cx = sum(p[0] for p in iris) / len(iris)
        cy = sum(p[1] for p in iris) / len(iris)

        # Use specific landmarks for robust normalization and blink detection
        if tag == "right":
            idx_outer, idx_inner, idx_up, idx_low = 33, 133, 159, 145
            iris_hist = self._iris_hist_right
        else:
            idx_outer, idx_inner, idx_up, idx_low = 263, 362, 386, 374
            iris_hist = self._iris_hist_left
        # Fetch points
        def _pt(i):
            try:
                p = pts[i]
                return (p.x * w, p.y * h)
            except Exception:
                return None
        p_outer = _pt(idx_outer)
        p_inner = _pt(idx_inner)
        p_up = _pt(idx_up)
        p_low = _pt(idx_low)
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
        # Median smoothing for iris center
        try:
            iris_hist.append((cx, cy))
            xs = [p[0] for p in iris_hist]
            ys = [p[1] for p in iris_hist]
            cx_s = float(np.median(xs)) if np is not None else float(sum(xs) / len(xs))
            cy_s = float(np.median(ys)) if np is not None else float(sum(ys) / len(ys))
        except Exception:
            cx_s, cy_s = float(cx), float(cy)
        # Normalize using corner/eyelid pair distances (more stable than loose bbox)
        nx = (cx_s - x_outer) / eye_w
        ny = (cy_s - y_up) / eye_h
        nx = float(max(0.0, min(1.0, nx)))
        ny = float(max(0.0, min(1.0, ny)))
        # Soft clamp per-frame delta to suppress spikes
        try:
            last = self._last_norm_right if tag == "right" else self._last_norm_left
            if last is not None:
                max_d = 0.12  # max change per frame in normalized units
                dx = max(-max_d, min(max_d, nx - last[0]))
                dy = max(-max_d, min(max_d, ny - last[1]))
                nx = float(last[0] + dx)
                ny = float(last[1] + dy)
        except Exception:
            pass
        # update last
        if tag == "right":
            self._last_norm_right = (nx, ny)
        else:
            self._last_norm_left = (nx, ny)

        # Eyelid box for overlay (slightly expanded)
        m = 2
        x1 = max(0, int(min(x_outer, x_inner)) - m)
        x2 = min(w - 1, int(max(x_outer, x_inner)) + m)
        y1 = max(0, int(min(y_up, y_low)) - m)
        y2 = min(h - 1, int(max(y_up, y_low)) + m)
        lids = [(x_outer, y_outer), (x_inner, y_inner), (x_up, y_up), (x_low, y_low)]
        landmarks = lids + iris
        return Features(iris_center=(cx_s, cy_s), eyelid_box=(x1, y1, x2, y2), nx=nx, ny=ny, landmarks=landmarks, eye=tag)

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

        # Extract requested eyes
        fr = self._extract_eye(pts, RIGHT_IRIS_IDX, RIGHT_EYE_LANDMARKS, w, h, "right")
        fl = self._extract_eye(pts, LEFT_IRIS_IDX, LEFT_EYE_LANDMARKS, w, h, "left")

        # Record movement history (auto mode)
        if fr is not None:
            self._hist_right.append((fr.nx, fr.ny))
        if fl is not None:
            self._hist_left.append((fl.nx, fl.ny))

        mode = self.eye_mode
        if mode == "right":
            return fr
        if mode == "left":
            return fl
        # auto: choose by movement range, fallback to larger eyelid area
        def score(hist, f: Optional[Features]):
            if f is None:
                return -1.0
            if len(hist) >= 10:
                xs = [p[0] for p in hist]
                ys = [p[1] for p in hist]
                return (max(xs) - min(xs)) + (max(ys) - min(ys))
            # fallback: area proxy
            x1, y1, x2, y2 = f.eyelid_box
            return float((x2 - x1) * (y2 - y1)) / 10000.0
        s_r = score(self._hist_right, fr)
        s_l = score(self._hist_left, fl)
        if s_r >= s_l:
            return fr if fr is not None else fl
        else:
            return fl if fl is not None else fr

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
