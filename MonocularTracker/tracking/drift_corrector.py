from __future__ import annotations

from collections import deque
from typing import Deque, Optional, Tuple


class DriftCorrector:
    def __init__(self, enabled: bool = True, window: int = 60, threshold_ratio: float = 0.08, learn_rate: float = 0.01) -> None:
        self.enabled = enabled
        self.window = max(1, int(window))
        self.threshold_ratio = float(threshold_ratio)
        self.learn_rate = float(learn_rate)
        self._errs: Deque[Tuple[float, float]] = deque(maxlen=self.window)
        self._off = (0.0, 0.0)

    def correct(self, xy: Tuple[int, int]) -> Tuple[int, int]:
        if not self.enabled:
            return xy
        x, y = xy
        return int(round(x + self._off[0])), int(round(y + self._off[1]))

    def update(self, observed: Tuple[int, int], target: Tuple[int, int], screen: Tuple[int, int]) -> None:
        if not self.enabled:
            return
        ex = float(target[0] - observed[0])
        ey = float(target[1] - observed[1])
        self._errs.append((ex, ey))
        mx, my = self._mean()
        if mx is None:
            return
        mag = (mx * mx + my * my) ** 0.5
        if mag > max(1.0, float(screen[0]) * self.threshold_ratio):
            self._off = (self._off[0] + mx * self.learn_rate, self._off[1] + my * self.learn_rate)

    def offset(self) -> Tuple[float, float]:
        return self._off

    def reset(self) -> None:
        self._errs.clear()
        self._off = (0.0, 0.0)

    def _mean(self) -> Tuple[Optional[float], Optional[float]]:
        if not self._errs:
            return (None, None)
        sx = sum(e[0] for e in self._errs)
        sy = sum(e[1] for e in self._errs)
        n = float(len(self._errs))
        return (sx / n, sy / n)
