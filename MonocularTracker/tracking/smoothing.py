from __future__ import annotations

from typing import Optional, Tuple


class Ema:
    def __init__(self, alpha: float = 0.25) -> None:
        self.alpha = max(0.01, min(0.99, float(alpha)))
        self._state: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        self._state = None

    def apply(self, xy: Tuple[int, int]) -> Tuple[int, int]:
        x, y = float(xy[0]), float(xy[1])
        if self._state is None:
            self._state = (x, y)
        else:
            sx, sy = self._state
            sx = self.alpha * x + (1 - self.alpha) * sx
            sy = self.alpha * y + (1 - self.alpha) * sy
            self._state = (sx, sy)
        sx, sy = self._state
        return int(round(sx)), int(round(sy))
