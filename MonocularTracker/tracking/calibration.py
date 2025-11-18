from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    import numpy as np  # type: ignore
    from sklearn.neural_network import MLPRegressor  # type: ignore
    from sklearn.preprocessing import StandardScaler, PolynomialFeatures  # type: ignore
    from sklearn.linear_model import Ridge  # type: ignore
    from sklearn.pipeline import Pipeline as SKPipeline  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore
    MLPRegressor = None  # type: ignore
    StandardScaler = None  # type: ignore
    PolynomialFeatures = None  # type: ignore
    Ridge = None  # type: ignore
    SKPipeline = None  # type: ignore


@dataclass
class Sample:
    feature: Tuple[float, float]
    screen_xy: Tuple[int, int]


class Calibrator:
    def __init__(self, hidden: Tuple[int, int] = (32, 32), activation: str = "tanh", max_iter: int = 800, method: str = "auto") -> None:
        if np is None or MLPRegressor is None:
            raise RuntimeError("scikit-learn and numpy required for calibration")
        self.hidden = hidden
        self.activation = activation
        self.max_iter = max_iter
        self.method = method  # 'mlp' | 'poly2' | 'auto'
        self.samples: List[Sample] = []
        self.mx: Optional[object] = None  # estimator for X
        self.my: Optional[object] = None  # estimator for Y
        self.scaler: Optional[StandardScaler] = None  # type: ignore[assignment]
        self.is_trained = False
        self.last_inlier_mask: Optional[list[bool]] = None
        # Robust config
        self.robust_enabled: bool = True
        self.robust_drop_percent: float = 15.0  # drop worst N percent
        self.min_keep_frac: float = 0.7
        self.min_keep_count: int = 30

    def reset(self) -> None:
        self.samples.clear()
        self.mx = None
        self.my = None
        self.scaler = None
        self.is_trained = False
        self.last_inlier_mask = None

    def add(self, f: Tuple[float, float], xy: Tuple[int, int]) -> None:
        self.samples.append(Sample(f, xy))

    def _train_mlp(self, X, yx, yy):
        scaler = StandardScaler() if StandardScaler is not None else None
        Xs = scaler.fit_transform(X) if scaler is not None else X
        mx = MLPRegressor(hidden_layer_sizes=self.hidden, activation=self.activation, max_iter=self.max_iter, solver="adam", random_state=42)
        my = MLPRegressor(hidden_layer_sizes=self.hidden, activation=self.activation, max_iter=self.max_iter, solver="adam", random_state=42)
        mx.fit(Xs, yx)
        my.fit(Xs, yy)
        # compute simple training error (RMSE)
        import math
        ex = np.asarray(mx.predict(Xs)) - yx
        ey = np.asarray(my.predict(Xs)) - yy
        rmse = math.sqrt(float(np.mean(ex * ex + ey * ey)))
        return mx, my, scaler, rmse

    def _train_poly2(self, X, yx, yy):
        # Pipeline: Standardize -> Polynomial(deg2) -> Ridge
        if SKPipeline is None or PolynomialFeatures is None or Ridge is None:
            # Fallback to MLP path
            return self._train_mlp(X, yx, yy)
        pipe_x = SKPipeline([
            ("scaler", StandardScaler() if StandardScaler is not None else None),
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("ridge", Ridge(alpha=1.0, random_state=42)),
        ])
        pipe_y = SKPipeline([
            ("scaler", StandardScaler() if StandardScaler is not None else None),
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("ridge", Ridge(alpha=1.0, random_state=42)),
        ])
        pipe_x.fit(X, yx)
        pipe_y.fit(X, yy)
        import math
        ex = np.asarray(pipe_x.predict(X)) - yx
        ey = np.asarray(pipe_y.predict(X)) - yy
        rmse = math.sqrt(float(np.mean(ex * ex + ey * ey)))
        return pipe_x, pipe_y, None, rmse

    def _compute_errors(self, X, yx, yy, mx, my, scaler=None):
        if scaler is not None:
            try:
                Xp = scaler.transform(X)
            except Exception:
                Xp = X
        else:
            Xp = X
        pred_x = np.asarray(mx.predict(Xp))
        pred_y = np.asarray(my.predict(Xp))
        dx = pred_x - yx
        dy = pred_y - yy
        return np.sqrt(dx * dx + dy * dy)

    # Public configuration -------------------------------------------------
    def configure_robust(self, enabled: bool, drop_percent: float | None = None) -> None:
        self.robust_enabled = bool(enabled)
        if drop_percent is not None:
            try:
                self.robust_drop_percent = float(max(0.0, min(49.0, drop_percent)))
            except Exception:
                pass

    def train(self) -> None:
        if not self.samples:
            return
        X = np.array([s.feature for s in self.samples], dtype=float)
        yx = np.array([s.screen_xy[0] for s in self.samples], dtype=float)
        yy = np.array([s.screen_xy[1] for s in self.samples], dtype=float)
        # Train candidates and pick the more stable one if method=='auto'
        if self.method in ("mlp", "auto"):
            mx_a, my_a, sc_a, rmse_a = self._train_mlp(X, yx, yy)
        else:
            mx_a = my_a = sc_a = None  # type: ignore[assignment]
            rmse_a = float("inf")
        if self.method in ("poly2", "auto"):
            mx_b, my_b, sc_b, rmse_b = self._train_poly2(X, yx, yy)
        else:
            mx_b = my_b = sc_b = None  # type: ignore[assignment]
            rmse_b = float("inf")

        if rmse_b < rmse_a:
            self.mx, self.my, self.scaler, chosen = mx_b, my_b, sc_b, "poly2"
            base_errs = self._compute_errors(X, yx, yy, mx_b, my_b, sc_b)
        else:
            self.mx, self.my, self.scaler, chosen = mx_a, my_a, sc_a, "mlp"
            base_errs = self._compute_errors(X, yx, yy, mx_a, my_a, sc_a)
        self.method = chosen
        # Robust pass: drop worst N% outliers if enabled and enough samples
        keep_mask = np.ones(len(X), dtype=bool)
        try:
            if self.robust_enabled and len(X) >= 40 and self.robust_drop_percent > 0.0:
                quant = 1.0 - (self.robust_drop_percent / 100.0)
                q = float(np.quantile(base_errs, quant))
                keep_mask = base_errs <= q
                # Safeguards
                min_keep = max(int(self.min_keep_frac * len(X)), self.min_keep_count)
                if keep_mask.sum() < min_keep:
                    # relax threshold by 5%
                    quant = min(0.98, quant + 0.05)
                    q = float(np.quantile(base_errs, quant))
                    keep_mask = base_errs <= q
        except Exception:
            pass
        self.last_inlier_mask = [bool(v) for v in keep_mask]
        if keep_mask.sum() < len(X):
            X2 = X[keep_mask]
            yx2 = yx[keep_mask]
            yy2 = yy[keep_mask]
            # retrain with same selection logic
            if self.method in ("mlp",):
                self.mx, self.my, self.scaler, _ = self._train_mlp(X2, yx2, yy2)
            elif self.method in ("poly2",):
                self.mx, self.my, self.scaler, _ = self._train_poly2(X2, yx2, yy2)
            else:  # auto -> choose again on filtered data
                mx_a, my_a, sc_a, rmse_a = self._train_mlp(X2, yx2, yy2)
                mx_b, my_b, sc_b, rmse_b = self._train_poly2(X2, yx2, yy2)
                if rmse_b < rmse_a:
                    self.mx, self.my, self.scaler, self.method = mx_b, my_b, sc_b, "poly2"
                else:
                    self.mx, self.my, self.scaler, self.method = mx_a, my_a, sc_a, "mlp"
        self.is_trained = True

    def predict(self, f: Tuple[float, float]) -> Tuple[int, int]:
        if not self.is_trained or self.mx is None or self.my is None:
            return (0, 0)
        X = np.array([f], dtype=float)
        if self.scaler is not None:
            try:
                X = self.scaler.transform(X)
            except Exception:
                pass
        # Some estimators are full pipelines; others need scaled input.
        try:
            px = float(self.mx.predict(X)[0])  # type: ignore[arg-type]
            py = float(self.my.predict(X)[0])  # type: ignore[arg-type]
        except Exception:
            # Fall back to passing raw X; pipelines handle their own scaling.
            px = float(self.mx.predict(X)[0])  # type: ignore
            py = float(self.my.predict(X)[0])  # type: ignore
        return int(round(px)), int(round(py))

    # Persistence -------------------------------------------------------
    def save(self, path: str) -> None:
        if not self.is_trained or self.mx is None or self.my is None:
            raise RuntimeError("Model not trained")
        data = {
            "hidden": list(self.hidden),
            "activation": self.activation,
            "max_iter": self.max_iter,
            "method": self.method,
            "mx_state": self._sanitize(self.mx.__getstate__()),
            "my_state": self._sanitize(self.my.__getstate__()),
            "scaler_state": (self._sanitize(self.scaler.__getstate__()) if self.scaler is not None else None),
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
        inst = cls(hidden=tuple(data.get("hidden", [32, 32])), activation=data.get("activation", "tanh"), max_iter=int(data.get("max_iter", 800)), method=data.get("method", "mlp"))
        # Recreate placeholders; exact estimator types are restored by __setstate__
        inst.mx = MLPRegressor(hidden_layer_sizes=inst.hidden, activation=inst.activation, max_iter=inst.max_iter, solver="adam", random_state=42)
        inst.my = MLPRegressor(hidden_layer_sizes=inst.hidden, activation=inst.activation, max_iter=inst.max_iter, solver="adam", random_state=42)
        state_x = cls._restore(data.get("mx_state", {}))
        state_y = cls._restore(data.get("my_state", {}))
        inst.mx.__setstate__(state_x)
        inst.my.__setstate__(state_y)
        # Restore scaler if available
        sc_state = data.get("scaler_state", None)
        if sc_state is not None and StandardScaler is not None:
            inst.scaler = StandardScaler()
            inst.scaler.__setstate__(cls._restore(sc_state))
        else:
            inst.scaler = None
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
