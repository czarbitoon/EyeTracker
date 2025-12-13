from __future__ import annotations

from typing import Optional, Tuple

from .calibration import Calibrator
from .drift_corrector import DriftCorrector
from .smoothing import ButterworthLowPass, TrendPredictor


class Mapping:
    def __init__(self, alpha: float = 0.25, drift_enabled: bool = True, drift_lr: float = 0.01, sample_rate_hz: float = 30.0) -> None:
        self.calib = Calibrator()
        # Use Butterworth low-pass only for smoothing; constants set in filter
        self.lp = ButterworthLowPass(sample_rate_hz=sample_rate_hz)
        self.pred = TrendPredictor(window=8, lookahead=0.15)
        self.drift = DriftCorrector(enabled=drift_enabled, learn_rate=drift_lr)
        self._calibrating = False
        self._last_out: Optional[Tuple[int, int]] = None

    def set_calibrating(self, on: bool) -> None:
        self._calibrating = bool(on)

    def reset(self) -> None:
        self.lp.reset()
        try:
            self.pred.reset()
        except Exception:
            pass
        self.drift.reset()
        self._last_out = None

    def add_calibration_sample(self, feature: Tuple[float, float], screen_xy: Tuple[int, int]) -> None:
        self.calib.add(feature, screen_xy)

    def train(self) -> None:
        self.calib.train()

    def predict(self, feature: Tuple[float, float]) -> Tuple[int, int]:
        return self.calib.predict(feature)

    def map_only(self, feature: Tuple[float, float]) -> Tuple[int, int]:
        """Direct mapping without drift correction, trend prediction, or smoothing."""
        return self.calib.predict(feature)

    def predict_stable(self, feature: Tuple[float, float], screen_size: Tuple[int, int]) -> Tuple[int, int]:
        # raw mapping
        x, y = self.predict(feature)
        # Validate raw output
        import math
        if not (isinstance(x, (int, float)) and isinstance(y, (int, float)) and math.isfinite(x) and math.isfinite(y)):
            return self._last_out if self._last_out is not None else (0, 0)
        # clamp immediately to screen bounds BEFORE smoothing/prediction
        w, h = screen_size
        x = int(max(0, min(w - 1, int(round(x)))))
        y = int(max(0, min(h - 1, int(round(y)))))
        # gentle drift correction (disabled during calibration)
        if self._calibrating:
            xy_corr = (x, y)
        else:
            xy_corr = self.drift.correct((x, y))
        # short lookahead to reduce perceived lag
        px, py = self.pred.update(xy_corr[0], xy_corr[1])
        # Validate post-prediction
        if not (math.isfinite(px) and math.isfinite(py)):
            return self._last_out if self._last_out is not None else (x, y)
        # Clamp again pre-smoothing to ensure bounds
        px = int(max(0, min(w - 1, int(round(px)))))
        py = int(max(0, min(h - 1, int(round(py)))))
        # smoothing (Butterworth low-pass only)
        sx, sy = self.lp.apply((px, py))
        # tiny deadzone to suppress micro-jitter
        if self._last_out is not None:
            dx = sx - self._last_out[0]
            dy = sy - self._last_out[1]
            if (dx * dx + dy * dy) ** 0.5 < 1.5:
                sx, sy = self._last_out
        # clamp to screen
        sx = max(0, min(w - 1, sx))
        sy = max(0, min(h - 1, sy))
        self._last_out = (sx, sy)
        return sx, sy
