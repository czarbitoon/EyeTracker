"""
EMA smoothing utilities for cursor coordinates.

Two APIs:
- Smoother: public, default alpha=0.6, apply((x,y)) -> smoothed (x,y); handles None safely.
- EmaSmoother: legacy wrapper compatible with earlier code (update((x,y)) -> (x,y)).
"""
from __future__ import annotations

from typing import Optional, Tuple


class Smoother:
    def __init__(self, alpha: float = 0.6) -> None:
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self._state: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        self._state = None

    def apply(self, xy: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """Apply EMA smoothing.

        - First non-None input initializes state and returns it.
        - If xy is None, returns the last rounded state if available; otherwise None.
        """
        if xy is None:
            if self._state is None:
                return None
            sx, sy = self._state
            return int(round(sx)), int(round(sy))

        x, y = float(xy[0]), float(xy[1])
        if self._state is None:
            self._state = (x, y)
        else:
            sx, sy = self._state
            ax = self.alpha * x + (1 - self.alpha) * sx
            ay = self.alpha * y + (1 - self.alpha) * sy
            self._state = (ax, ay)
        sx, sy = self._state
        return int(round(sx)), int(round(sy))


class EmaSmoother:
    """Legacy API wrapper used by the app. Uses Smoother internally."""

    def __init__(self, alpha: float = 0.2) -> None:
        self._impl = Smoother(alpha=alpha)

    def reset(self) -> None:
        self._impl.reset()

    def update(self, xy: Tuple[int, int]) -> Tuple[int, int]:
        out = self._impl.apply(xy)
        # For legacy API, we assume xy is not None and output won't be None
        assert out is not None
        return out
