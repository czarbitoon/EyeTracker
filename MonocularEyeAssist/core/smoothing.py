from __future__ import annotations

from collections import deque
from typing import Optional, Tuple


class EMA2D:
    def __init__(self, alpha: float = 0.35) -> None:
        self.alpha = float(alpha)
        self._state: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        self._state = None

    def update(self, x: float, y: float) -> Tuple[float, float]:
        if self._state is None:
            self._state = (float(x), float(y))
            return self._state
        ax = self.alpha * x + (1.0 - self.alpha) * self._state[0]
        ay = self.alpha * y + (1.0 - self.alpha) * self._state[1]
        self._state = (ax, ay)
        return self._state


class TrendPredictor:
    """Detect rapid jitter and project a small lookahead along trend."""

    def __init__(self, window: int = 8, lookahead: float = 0.2) -> None:
        self.hist = deque(maxlen=max(4, int(window)))
        self.lookahead = float(lookahead)

    def reset(self) -> None:
        self.hist.clear()

    def update(self, x: float, y: float) -> Tuple[float, float]:
        self.hist.append((float(x), float(y)))
        if len(self.hist) < 4:
            return (x, y)
        xs = [p[0] for p in self.hist]
        ys = [p[1] for p in self.hist]
        vx = xs[-1] - xs[-2]
        vy = ys[-1] - ys[-2]
        # Simple jitter metric: mean absolute successive diff
        mx = sum(abs(xs[i] - xs[i - 1]) for i in range(1, len(xs))) / (len(xs) - 1)
        my = sum(abs(ys[i] - ys[i - 1]) for i in range(1, len(ys))) / (len(ys) - 1)
        jitter = (mx + my) * 0.5
        if jitter < 2.0:  # pixels
            return (x, y)
        return (x + self.lookahead * vx, y + self.lookahead * vy)
