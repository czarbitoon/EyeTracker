"""Calibrator class using two separate MLPRegressor models (for X and Y) to map
normalized eye features (nx, ny) -> screen coordinates (x, y).

Features:
  - add_sample(features, screen_xy)
  - train() trains two models with identical hyperparameters
  - predict(features) returns integer (x, y)
  - save(path) / load(path) using JSON with model.__getstate__() data
  - Handles float / ndarray conversions when serializing to JSON

Notes:
  * The constructor accepts an unused positional argument for backward compatibility
    with earlier code that passed a single regressor instance.
  * Hidden layers default (32, 32), activation='tanh', max_iter=800 as required.
  * Requires scikit-learn and numpy.
"""
from __future__ import annotations

import json
import os
from typing import List, Tuple, Any, Dict

try:
    import numpy as np  # type: ignore
    from sklearn.neural_network import MLPRegressor  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore
    MLPRegressor = None  # type: ignore

from .models import CalibrationSample


class Calibrator:
    def __init__(
        self,
        _unused: Any = None,  # backward compatibility placeholder
        hidden_layer_sizes: Tuple[int, int] = (32, 32),
        activation: str = "tanh",
        max_iter: int = 800,
    ) -> None:
        if MLPRegressor is None or np is None:
            raise RuntimeError("scikit-learn and numpy must be installed for calibration.")
        self.hidden_layer_sizes = hidden_layer_sizes
        self.activation = activation
        self.max_iter = max_iter
        self.samples: List[CalibrationSample] = []
        # Avoid strict annotations referencing optional imports in some linters
        self._model_x = None  # type: ignore[assignment]
        self._model_y = None  # type: ignore[assignment]
        self.is_trained = False

    # ------------------------------------------------------------------
    # Sample management
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.samples.clear()
        self.is_trained = False
        self._model_x = None
        self._model_y = None

    def add_sample(self, feature: Tuple[float, float], screen_xy: Tuple[int, int]) -> None:
        self.samples.append(CalibrationSample(feature=feature, screen_xy=screen_xy))

    # ------------------------------------------------------------------
    # Training & Prediction
    # ------------------------------------------------------------------
    def train(self) -> None:
        if not self.samples:
            return
        X = np.array([s.feature for s in self.samples], dtype=float)
        y_x = np.array([s.screen_xy[0] for s in self.samples], dtype=float)
        y_y = np.array([s.screen_xy[1] for s in self.samples], dtype=float)

        self._model_x = MLPRegressor(
            hidden_layer_sizes=self.hidden_layer_sizes,
            activation=self.activation,
            max_iter=self.max_iter,
            solver="adam",
            random_state=42,
        )
        self._model_y = MLPRegressor(
            hidden_layer_sizes=self.hidden_layer_sizes,
            activation=self.activation,
            max_iter=self.max_iter,
            solver="adam",
            random_state=42,
        )

        self._model_x.fit(X, y_x)
        self._model_y.fit(X, y_y)
        self.is_trained = True

    def predict(self, feature: Tuple[float, float]) -> Tuple[int, int]:
        if not self.is_trained or self._model_x is None or self._model_y is None:
            return (0, 0)
        X = np.array([feature], dtype=float)
        px = float(self._model_x.predict(X)[0])
        py = float(self._model_y.predict(X)[0])
        return int(round(px)), int(round(py))

    # ------------------------------------------------------------------
    # Persistence (JSON serialization of model state)
    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        if not self.is_trained or self._model_x is None or self._model_y is None:
            raise RuntimeError("Cannot save: models are not trained.")
        data = {
            "version": 1,
            "hidden_layer_sizes": list(self.hidden_layer_sizes),
            "activation": self.activation,
            "max_iter": self.max_iter,
            "model_x_state": self._sanitize_state(self._model_x.__getstate__()),
            "model_y_state": self._sanitize_state(self._model_y.__getstate__()),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> "Calibrator":
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        hidden_layer_sizes = tuple(data.get("hidden_layer_sizes", [32, 32]))
        activation = data.get("activation", "tanh")
        max_iter = int(data.get("max_iter", 800))
        inst = cls(None, hidden_layer_sizes=hidden_layer_sizes, activation=activation, max_iter=max_iter)
        # Rebuild models
        inst._model_x = MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            activation=activation,
            max_iter=max_iter,
            solver="adam",
            random_state=42,
        )
        inst._model_y = MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            activation=activation,
            max_iter=max_iter,
            solver="adam",
            random_state=42,
        )
        # Restore their internal state
        state_x = cls._restore_state(data.get("model_x_state", {}))
        state_y = cls._restore_state(data.get("model_y_state", {}))
        inst._model_x.__setstate__(state_x)
        inst._model_y.__setstate__(state_y)
        inst.is_trained = True
        return inst

    # ------------------------------------------------------------------
    # State conversion helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _sanitize_state(state: Dict[str, Any]) -> Dict[str, Any]:
        def convert(value: Any) -> Any:
            if np is not None and isinstance(value, np.ndarray):
                return value.tolist()
            if isinstance(value, list):
                # Recursively convert list elements
                return [convert(v) for v in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value
        return {k: convert(v) for k, v in state.items()}

    @staticmethod
    def _restore_state(state: Dict[str, Any]) -> Dict[str, Any]:
        def convert(value: Any) -> Any:
            # For lists that look numeric, convert to numpy array; keep list-of-lists as list of arrays if needed.
            if isinstance(value, list):
                if all(isinstance(el, (int, float)) for el in value):
                    return np.array(value, dtype=float) if np is not None else value
                # list of lists -> possibly coefs_/intercepts_ arrays
                if all(isinstance(el, list) for el in value):
                    return [convert(el) for el in value]
                return [convert(el) for el in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value
        restored = {k: convert(v) for k, v in state.items()}
        # Special handling for coefs_/intercepts_ (should be list of np.ndarray)
        for special in ("coefs_", "intercepts_"):
            if special in restored and isinstance(restored[special], list):
                restored[special] = [np.array(a, dtype=float) if np is not None else a for a in restored[special]]
        return restored
