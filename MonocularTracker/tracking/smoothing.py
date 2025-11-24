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


class TrendPredictor:
    """Project a small lookahead along recent motion trend.

    Keeps a tiny history to estimate velocity and nudges the point forward
    to reduce perceived lag during quick eye moves. If motion is very small
    (low jitter), returns the input unchanged.
    """

    def __init__(self, window: int = 8, lookahead: float = 0.15) -> None:
        from collections import deque

        self._hist = deque(maxlen=max(4, int(window)))
        self.lookahead = float(lookahead)

    def reset(self) -> None:
        try:
            self._hist.clear()
        except Exception:
            pass

    def update(self, x: int, y: int) -> Tuple[int, int]:
        xi = int(x); yi = int(y)
        self._hist.append((float(xi), float(yi)))
        if len(self._hist) < 4:
            return (xi, yi)
        xs = [p[0] for p in self._hist]
        ys = [p[1] for p in self._hist]
        vx = xs[-1] - xs[-2]
        vy = ys[-1] - ys[-2]
        # Simple jitter metric: mean abs successive diff
        mx = sum(abs(xs[i] - xs[i - 1]) for i in range(1, len(xs))) / (len(xs) - 1)
        my = sum(abs(ys[i] - ys[i - 1]) for i in range(1, len(ys))) / (len(ys) - 1)
        jitter = 0.5 * (mx + my)
        if jitter < 1.5:  # px threshold under which we avoid projecting
            return (xi, yi)
        px = float(xi) + self.lookahead * vx
        py = float(yi) + self.lookahead * vy
        return (int(round(px)), int(round(py)))
