from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import Ridge


def _mad_mask(errors: np.ndarray, thresh: float = 3.5) -> np.ndarray:
    med = np.median(errors)
    mad = np.median(np.abs(errors - med)) + 1e-9
    z = 0.6745 * (errors - med) / mad
    return np.abs(z) <= float(thresh)


@dataclass
class CalibModel:
    scaler: StandardScaler
    poly: PolynomialFeatures
    reg_x: Ridge
    reg_y: Ridge

    def predict(self, feats: np.ndarray) -> np.ndarray:
        F = self.scaler.transform(feats)
        P = self.poly.transform(F)
        x = self.reg_x.predict(P)
        y = self.reg_y.predict(P)
        return np.stack([x, y], axis=1)


class Calibrator:
    def __init__(self, screen_size: Tuple[int, int], degree: int = 2) -> None:
        self.screen = screen_size
        self.degree = int(degree)
        self._feats: List[Tuple[float, float]] = []
        self._targets: List[Tuple[int, int]] = []
        self.model: Optional[CalibModel] = None
        self.last_inlier_mask: Optional[np.ndarray] = None

    def reset(self) -> None:
        self._feats.clear()
        self._targets.clear()
        self.model = None
        self.last_inlier_mask = None

    def add_sample(self, nx: float, ny: float, target: Tuple[int, int]) -> None:
        self._feats.append((float(nx), float(ny)))
        self._targets.append((int(target[0]), int(target[1])))

    def train(self) -> None:
        if len(self._feats) < 12:
            return
        F = np.array(self._feats, dtype=np.float32)
        T = np.array(self._targets, dtype=np.float32)
        sc = StandardScaler()
        Fz = sc.fit_transform(F)
        poly = PolynomialFeatures(self.degree, include_bias=True)
        P = poly.fit_transform(Fz)
        rx = Ridge(alpha=1.0)
        ry = Ridge(alpha=1.0)
        rx.fit(P, T[:, 0])
        ry.fit(P, T[:, 1])
        # Outlier filtering by MAD on residuals
        pred_x = rx.predict(P)
        pred_y = ry.predict(P)
        e = np.sqrt((pred_x - T[:, 0]) ** 2 + (pred_y - T[:, 1]) ** 2)
        mask = _mad_mask(e, 3.0)
        self.last_inlier_mask = mask
        F2 = F[mask]
        T2 = T[mask]
        if len(F2) >= 12:
            Fz2 = sc.fit_transform(F2)
            P2 = poly.fit_transform(Fz2)
            rx.fit(P2, T2[:, 0])
            ry.fit(P2, T2[:, 1])
        self.model = CalibModel(scaler=sc, poly=poly, reg_x=rx, reg_y=ry)

    def predict(self, nx: float, ny: float) -> Tuple[int, int]:
        if self.model is None:
            return (0, 0)
        arr = np.array([[nx, ny]], dtype=np.float32)
        out = self.model.predict(arr)[0]
        x = int(max(0, min(self.screen[0] - 1, out[0])))
        y = int(max(0, min(self.screen[1] - 1, out[1])))
        return (x, y)

    def save(self, path: str) -> None:
        if self.model is None:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "screen": [int(self.screen[0]), int(self.screen[1])],
            "degree": int(self.degree),
            "scaler": {
                "mean": self.model.scaler.mean_.tolist(),
                "scale": self.model.scaler.scale_.tolist(),
            },
            "poly_degree": int(self.model.poly.degree),
            "rx": {"coef": self.model.reg_x.coef_.tolist(), "intercept": float(self.model.reg_x.intercept_)},
            "ry": {"coef": self.model.reg_y.coef_.tolist(), "intercept": float(self.model.reg_y.intercept_)},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load(path: str) -> Optional[CalibModel]:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        screen = tuple(data.get("screen", [1920, 1080]))  # noqa: F841
        degree = int(data.get("degree", 2))
        sc = StandardScaler()
        sc.mean_ = np.array(data["scaler"]["mean"], dtype=np.float64)
        sc.scale_ = np.array(data["scaler"]["scale"], dtype=np.float64)
        sc.var_ = sc.scale_ ** 2
        poly = PolynomialFeatures(int(data.get("poly_degree", degree)), include_bias=True)
        # Fit a dummy to initialize n_input_features_
        poly.fit(np.zeros((1, sc.mean_.shape[0]), dtype=np.float64))
        rx = Ridge(alpha=1.0)
        ry = Ridge(alpha=1.0)
        rx.coef_ = np.array(data["rx"]["coef"], dtype=np.float64)
        rx.intercept_ = float(data["rx"]["intercept"])
        ry.coef_ = np.array(data["ry"]["coef"], dtype=np.float64)
        ry.intercept_ = float(data["ry"]["intercept"])
        return CalibModel(scaler=sc, poly=poly, reg_x=rx, reg_y=ry)
