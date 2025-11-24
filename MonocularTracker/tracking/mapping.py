from __future__ import annotations

from typing import Optional, Tuple

from .calibration import Calibrator
from .drift_corrector import DriftCorrector
from .smoothing import Ema, TrendPredictor


class Mapping:
    def __init__(self, alpha: float = 0.25, drift_enabled: bool = True, drift_lr: float = 0.01) -> None:
        self.calib = Calibrator()
        self.ema = Ema(alpha=alpha)
        self.pred = TrendPredictor(window=8, lookahead=0.15)
        self.drift = DriftCorrector(enabled=drift_enabled, learn_rate=drift_lr)
        self._calibrating = False
        self._last_out: Optional[Tuple[int, int]] = None

    def set_calibrating(self, on: bool) -> None:
        self._calibrating = bool(on)

    def reset(self) -> None:
        self.ema.reset()
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

    def predict_stable(self, feature: Tuple[float, float], screen_size: Tuple[int, int]) -> Tuple[int, int]:
        # raw mapping
        x, y = self.predict(feature)
        # gentle drift correction (disabled during calibration)
        if self._calibrating:
            xy_corr = (x, y)
        else:
            xy_corr = self.drift.correct((x, y))
        # short lookahead to reduce perceived lag
        px, py = self.pred.update(xy_corr[0], xy_corr[1])
        # smoothing
        sx, sy = self.ema.apply((px, py))
        # tiny deadzone to suppress micro-jitter
        if self._last_out is not None:
            dx = sx - self._last_out[0]
            dy = sy - self._last_out[1]
            if (dx * dx + dy * dy) ** 0.5 < 1.5:
                sx, sy = self._last_out
        # clamp to screen
        w, h = screen_size
        sx = max(0, min(w - 1, sx))
        sy = max(0, min(h - 1, sy))
        self._last_out = (sx, sy)
        return sx, sy
