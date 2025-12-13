from __future__ import annotations

from typing import Optional, Tuple


# Fixed filter constants (not user-editable)
CUTOFF_HZ = 6.0
ORDER = 2  # biquad

class ButterworthLowPass:
    """Second-order Butterworth low-pass filter for 2D points.

    Parameters:
    - sample_rate_hz: input update rate (e.g., 30 for 30 FPS)
    - cutoff_hz: cutoff frequency; lower = more smoothing (default 4 Hz)

    The filter uses the bilinear transform to compute biquad coefficients.
    """

    def __init__(self, sample_rate_hz: float = 30.0) -> None:
        sr = max(1.0, float(sample_rate_hz))
        fc = max(0.5, min(sr / 2.0 - 0.001, float(CUTOFF_HZ)))
        # Pre-warp and compute biquad coefficients for Butterworth (Q=1/sqrt(2))
        import math

        omega = 2.0 * math.pi * fc / sr
        tan_ = math.tan(omega)
        # Normalize for bilinear transform
        c = 1.0 / tan_
        # Butterworth 2nd-order low-pass (RBJ cookbook form)
        # https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html
        Q = 1.0 / math.sqrt(2.0)
        K = math.tan(math.pi * fc / sr)
        norm = 1.0 / (1.0 + K / Q + K * K)
        b0 = K * K * norm
        b1 = 2.0 * b0
        b2 = b0
        a1 = 2.0 * (K * K - 1.0) * norm
        a2 = (1.0 - K / Q + K * K) * norm

        self._b0 = b0
        self._b1 = b1
        self._b2 = b2
        self._a1 = a1
        self._a2 = a2
        self._x1: Optional[Tuple[float, float]] = None
        self._x2: Optional[Tuple[float, float]] = None
        self._y1: Optional[Tuple[float, float]] = None
        self._y2: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        self._x1 = None
        self._x2 = None
        self._y1 = None
        self._y2 = None

    def apply(self, xy: Tuple[int, int]) -> Tuple[int, int]:
        x0 = float(xy[0]); y0 = float(xy[1])
        if self._x1 is None:
            # Initialize with first sample
            self._x1 = (x0, y0)
            self._x2 = (x0, y0)
            self._y1 = (x0, y0)
            self._y2 = (x0, y0)
            return int(round(x0)), int(round(y0))
        assert self._x2 is not None and self._y1 is not None and self._y2 is not None
        x1, y1 = self._x1
        x2, y2 = self._x2
        yo1, yo2 = self._y1, self._y2
        # Biquad difference equation per axis
        ox = self._b0 * x0 + self._b1 * x1 + self._b2 * x2 - self._a1 * yo1[0] - self._a2 * yo2[0]
        oy = self._b0 * y0 + self._b1 * y1 + self._b2 * y2 - self._a1 * yo1[1] - self._a2 * yo2[1]
        # Update state
        self._x2 = self._x1
        self._x1 = (x0, y0)
        self._y2 = self._y1
        self._y1 = (ox, oy)
        return int(round(ox)), int(round(oy))

    def apply_float(self, xy: Tuple[float, float]) -> Tuple[float, float]:
        """Apply filter to floats, returning floats (no rounding).

        Useful for smoothing normalized coordinates prior to mapping.
        """
        x0 = float(xy[0]); y0 = float(xy[1])
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
