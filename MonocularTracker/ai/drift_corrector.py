"""
Drift correction module.

Mechanics:
- Maintain a rolling window of prediction errors e = (target - observed).
- Compute rolling mean drift. If its magnitude exceeds 8% of screen width,
  nudge a global bias offset toward compensating the drift.
- Apply corrections smoothly with a small learning rate (default 0.01).
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Tuple, Optional


class DriftCorrector:
    def __init__(
        self,
        enabled: bool = True,
        window_size: int = 60,
        threshold_ratio: float = 0.08,
        learn_rate: float = 0.01,
    ) -> None:
        self.enabled = enabled
        self.window_size = max(1, int(window_size))
        self.threshold_ratio = float(threshold_ratio)
        self.learn_rate = float(learn_rate)

        self._errors: Deque[Tuple[float, float]] = deque(maxlen=self.window_size)
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0

    # Public API ---------------------------------------------------------
    def correct(self, xy: Tuple[int, int]) -> Tuple[int, int]:
        """Apply current bias correction to a predicted point."""
        if not self.enabled:
            return xy
        x, y = xy
        return int(round(x + self._offset_x)), int(round(y + self._offset_y))

    def update(self, observed_xy: Tuple[int, int], target_xy: Tuple[int, int], screen_size: Tuple[int, int]) -> None:
        """Feed an error sample and adapt bias if drift is significant.

        observed_xy: the current mapped prediction (after correction is fine)
        target_xy: the expected/true screen position for this frame (e.g., calibration/validation point)
        screen_size: (width, height) in pixels; threshold uses width
        """
        if not self.enabled:
            return
        ox, oy = observed_xy
        tx, ty = target_xy
        err = (float(tx - ox), float(ty - oy))
        self._errors.append(err)

        mean_err = self._mean_error()
        if mean_err is None:
            return
        mx, my = mean_err
        drift_mag = (mx * mx + my * my) ** 0.5
        thresh = float(screen_size[0]) * self.threshold_ratio
        if drift_mag > max(1.0, thresh):
            # Move the bias a tiny step toward compensating the drift
            self._offset_x += mx * self.learn_rate
            self._offset_y += my * self.learn_rate

    def reset(self) -> None:
        self._errors.clear()
        self._offset_x = 0.0
        self._offset_y = 0.0

    # Introspection ------------------------------------------------------
    def mean_error(self) -> Optional[Tuple[float, float]]:
        return self._mean_error()

    def offset(self) -> Tuple[float, float]:
        return self._offset_x, self._offset_y

    # Internals ----------------------------------------------------------
    def _mean_error(self) -> Optional[Tuple[float, float]]:
        if not self._errors:
            return None
        sx = sum(e[0] for e in self._errors)
        sy = sum(e[1] for e in self._errors)
        n = float(len(self._errors))
        return sx / n, sy / n
