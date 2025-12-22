from __future__ import annotations

import math
from typing import Optional, Tuple

CUTOFF_HZ = 6.0
ORDER = 2

class ButterworthLowPass:
    def __init__(self, sample_rate_hz: float) -> None:
        sr = max(1.0, float(sample_rate_hz))
        fc = max(0.5, min(sr / 2.0 - 0.001, float(CUTOFF_HZ)))
        # RBJ cookbook biquad coeffs for Butterworth LPF (order=2)
        Q = 1.0 / math.sqrt(2.0)
        K = math.tan(math.pi * fc / sr)
        norm = 1.0 / (1.0 + K / Q + K * K)
        self._b0 = K * K * norm
        self._b1 = 2.0 * self._b0
        self._b2 = self._b0
        self._a1 = 2.0 * (K * K - 1.0) * norm
        self._a2 = (1.0 - K / Q + K * K) * norm
        self._x1: Optional[Tuple[float, float]] = None
        self._x2: Optional[Tuple[float, float]] = None
        self._y1: Optional[Tuple[float, float]] = None
        self._y2: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        self._x1 = None
        self._x2 = None
        self._y1 = None
        self._y2 = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        x0 = float(x); y0 = float(y)
        if self._x1 is None:
            self._x1 = (x0, y0)
            self._x2 = (x0, y0)
            self._y1 = (x0, y0)
            self._y2 = (x0, y0)
            return (x0, y0)
        assert self._x2 is not None and self._y1 is not None and self._y2 is not None
        x1, y1 = self._x1
        x2, y2 = self._x2
        yo1, yo2 = self._y1, self._y2
        ox = self._b0 * x0 + self._b1 * x1 + self._b2 * x2 - self._a1 * yo1[0] - self._a2 * yo2[0]
        oy = self._b0 * y0 + self._b1 * y1 + self._b2 * y2 - self._a1 * yo1[1] - self._a2 * yo2[1]
        self._x2 = self._x1
        self._x1 = (x0, y0)
        self._y2 = self._y1
        self._y1 = (ox, oy)
        return (ox, oy)
