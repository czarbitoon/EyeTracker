from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    import numpy as np  # type: ignore
    from sklearn.neural_network import MLPRegressor  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore
    MLPRegressor = None  # type: ignore


@dataclass
class Sample:
    feature: Tuple[float, float]
    screen_xy: Tuple[int, int]


class Calibrator:
    def __init__(self, hidden: Tuple[int, int] = (32, 32), activation: str = "tanh", max_iter: int = 800) -> None:
        if np is None or MLPRegressor is None:
            raise RuntimeError("scikit-learn and numpy required for calibration")
        self.hidden = hidden
        self.activation = activation
        self.max_iter = max_iter
        self.samples: List[Sample] = []
        self.mx: Optional[MLPRegressor] = None  # type: ignore[assignment]
        self.my: Optional[MLPRegressor] = None  # type: ignore[assignment]
        self.is_trained = False

    def reset(self) -> None:
        self.samples.clear()
        self.mx = None
        self.my = None
        self.is_trained = False

    def add(self, f: Tuple[float, float], xy: Tuple[int, int]) -> None:
        self.samples.append(Sample(f, xy))

    def train(self) -> None:
        if not self.samples:
            return
        X = np.array([s.feature for s in self.samples], dtype=float)
        yx = np.array([s.screen_xy[0] for s in self.samples], dtype=float)
        yy = np.array([s.screen_xy[1] for s in self.samples], dtype=float)
        self.mx = MLPRegressor(hidden_layer_sizes=self.hidden, activation=self.activation, max_iter=self.max_iter, solver="adam", random_state=42)
        self.my = MLPRegressor(hidden_layer_sizes=self.hidden, activation=self.activation, max_iter=self.max_iter, solver="adam", random_state=42)
        self.mx.fit(X, yx)
        self.my.fit(X, yy)
        self.is_trained = True

    def predict(self, f: Tuple[float, float]) -> Tuple[int, int]:
        if not self.is_trained or self.mx is None or self.my is None:
            return (0, 0)
        X = np.array([f], dtype=float)
        px = float(self.mx.predict(X)[0])
        py = float(self.my.predict(X)[0])
        return int(round(px)), int(round(py))

    # Persistence -------------------------------------------------------
    def save(self, path: str) -> None:
        if not self.is_trained or self.mx is None or self.my is None:
            raise RuntimeError("Model not trained")
        data = {
            "hidden": list(self.hidden),
            "activation": self.activation,
            "max_iter": self.max_iter,
            "mx_state": self._sanitize(self.mx.__getstate__()),
            "my_state": self._sanitize(self.my.__getstate__()),
        }
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> "Calibrator":
        import os, json
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        inst = cls(hidden=tuple(data.get("hidden", [32, 32])), activation=data.get("activation", "tanh"), max_iter=int(data.get("max_iter", 800)))
        inst.mx = MLPRegressor(hidden_layer_sizes=inst.hidden, activation=inst.activation, max_iter=inst.max_iter, solver="adam", random_state=42)
        inst.my = MLPRegressor(hidden_layer_sizes=inst.hidden, activation=inst.activation, max_iter=inst.max_iter, solver="adam", random_state=42)
        state_x = cls._restore(data.get("mx_state", {}))
        state_y = cls._restore(data.get("my_state", {}))
        inst.mx.__setstate__(state_x)
        inst.my.__setstate__(state_y)
        inst.is_trained = True
        return inst

    @staticmethod
    def _sanitize(state):
        def conv(v):
            if isinstance(v, np.ndarray):
                return v.tolist()
            if isinstance(v, list):
                return [conv(x) for x in v]
            if isinstance(v, dict):
                return {k: conv(x) for k, x in v.items()}
            return v
        return {k: conv(v) for k, v in state.items()}

    @staticmethod
    def _restore(state):
        def conv(v):
            if isinstance(v, list):
                if all(isinstance(x, (int, float)) for x in v):
                    return np.array(v, dtype=float)
                return [conv(x) for x in v]
            if isinstance(v, dict):
                return {k: conv(x) for k, x in v.items()}
            return v
        s = {k: conv(v) for k, v in state.items()}
        # coefs_/intercepts_ arrays
        for k in ("coefs_", "intercepts_"):
            if k in s and isinstance(s[k], list):
                s[k] = [np.array(a, dtype=float) for a in s[k]]
        return s

    def accuracy(self, eval_samples: Optional[List[Sample]] = None) -> Tuple[float, float]:
        """Return (mean_error_px, max_error_px)."""
        if eval_samples is None:
            eval_samples = self.samples
        if not eval_samples:
            return (0.0, 0.0)
        errs: List[float] = []
        for s in eval_samples:
            px, py = self.predict(s.feature)
            dx = float(px - s.screen_xy[0])
            dy = float(py - s.screen_xy[1])
            errs.append((dx * dx + dy * dy) ** 0.5)
        mean_err = sum(errs) / float(len(errs))
        return (mean_err, max(errs))
