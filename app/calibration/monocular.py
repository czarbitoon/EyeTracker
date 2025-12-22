from __future__ import annotations

"""
Monocular calibration stubs.

This module provides a minimal, structured API for future calibration
steps. It does not perform any heavy computation yet; it's a scaffold
for collecting samples and producing calibration parameters.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class CalibrationSample:
    # Normalized gaze inputs (0..1)
    nx: float
    ny: float
    # Target screen pixel coordinates
    sx: int
    sy: int


@dataclass
class CalibrationParams:
    # Placeholder affine-like parameters for mapping
    gain_x: float = 1.0
    gain_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0


class MonocularCalibration:
    """
    Collect samples and compute simple calibration parameters.

    Intended usage:
    - Add samples pairing normalized gaze with target screen pixels
    - Compute simple gains/offsets as a first approximation
    - Export/import params for later use
    """

    def __init__(self) -> None:
        self._samples: List[CalibrationSample] = []
        self._params: CalibrationParams = CalibrationParams()

    def add_sample(self, nx: float, ny: float, sx: int, sy: int) -> None:
        self._samples.append(CalibrationSample(float(nx), float(ny), int(sx), int(sy)))

    def clear(self) -> None:
        self._samples.clear()

    def compute(self) -> CalibrationParams:
        """Compute naive gains/offsets from collected samples.

        For now, this applies a simple least-squares fit for each axis:
          sx ≈ offset_x + gain_x * nx
          sy ≈ offset_y + gain_y * ny

        Returns the updated CalibrationParams.
        """
        if not self._samples:
            return self._params

        # Simple linear regression per axis: y = a + b x
        def linear_fit(pairs: List[Tuple[float, float]]) -> Tuple[float, float]:
            # pairs: (x, y)
            n = len(pairs)
            sum_x = sum(p[0] for p in pairs)
            sum_y = sum(p[1] for p in pairs)
            sum_xx = sum(p[0] * p[0] for p in pairs)
            sum_xy = sum(p[0] * p[1] for p in pairs)
            denom = (n * sum_xx - sum_x * sum_x)
            if denom == 0:
                b = 0.0
                a = sum_y / n if n else 0.0
            else:
                b = (n * sum_xy - sum_x * sum_y) / denom
                a = (sum_y - b * sum_x) / n
            return a, b

        xs_pairs = [(s.nx, float(s.sx)) for s in self._samples]
        ys_pairs = [(s.ny, float(s.sy)) for s in self._samples]
        ox, gx = linear_fit(xs_pairs)
        oy, gy = linear_fit(ys_pairs)
        self._params = CalibrationParams(gain_x=gx, gain_y=gy, offset_x=ox, offset_y=oy)
        return self._params

    def params(self) -> CalibrationParams:
        return self._params

    def sample_count(self) -> int:
        return len(self._samples)


class MonocularCalibrator:
    """
    Monocular calibration using directional samples with explicit user control.

    API:
      - start()
      - add_sample(name, dx, dy)
      - is_complete()
      - compute(screen_width, screen_height) -> bool
      - map(dx, dy) -> (x, y)
      - reset()

    Stores samples for center/left/right/up/down as (dx, dy). Computes per-axis
    scales and maps to screen coordinates, clamping to bounds. Provides JSON
    save/load helpers.
    """

    CALIB_SEQUENCE = ["center", "left", "right", "up", "down"]

    def __init__(self) -> None:
        # Screen spec is set during compute()
        self.screen_width: int | None = None
        self.screen_height: int | None = None
        self.screen_center_x: int | None = None
        self.screen_center_y: int | None = None

        # Samples: each is optional tuple (dx, dy)
        self.samples: dict[str, tuple[float, float] | None] = {k: None for k in self.CALIB_SEQUENCE}

        # Computed scales
        self.scale_x: float | None = None
        self.scale_y: float | None = None

    def start(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.samples = {k: None for k in self.CALIB_SEQUENCE}
        self.scale_x = None
        self.scale_y = None
        # Do not clear screen dims; they are re-provided on compute

    def add_sample(self, name: str, dx: float, dy: float) -> None:
        if name not in self.samples:
            raise ValueError("unknown sample name")
        self.samples[name] = (float(dx), float(dy))

    def is_complete(self) -> bool:
        return all(self.samples.get(k) is not None for k in self.CALIB_SEQUENCE)

    def compute(self, screen_width: int, screen_height: int) -> bool:
        """Compute scale_x/scale_y; validate ranges. Returns True if valid."""
        if screen_width <= 0 or screen_height <= 0:
            return False
        if not self.is_complete():
            return False

        self.screen_width = int(screen_width)
        self.screen_height = int(screen_height)
        self.screen_center_x = self.screen_width // 2
        self.screen_center_y = self.screen_height // 2

        dx_left, _ = self.samples["left"]  # type: ignore[assignment]
        dx_right, _ = self.samples["right"]  # type: ignore[assignment]
        _, dy_up = self.samples["up"]  # type: ignore[assignment]
        _, dy_down = self.samples["down"]  # type: ignore[assignment]

        range_x = dx_right - dx_left
        range_y = dy_down - dy_up
        if range_x == 0.0 or range_y == 0.0:
            return False
        if range_x < 0.0 or range_y < 0.0:
            return False

        self.scale_x = self.screen_width / range_x
        self.scale_y = self.screen_height / range_y
        return True

    def map(self, dx: float, dy: float) -> tuple[int, int]:
        if (self.scale_x is None or self.scale_y is None or
                self.screen_width is None or self.screen_height is None or
                self.screen_center_x is None or self.screen_center_y is None):
            raise ValueError("calibration not computed")
        x = int(round(self.screen_center_x + float(dx) * self.scale_x))
        y = int(round(self.screen_center_y + float(dy) * self.scale_y))
        x = min(self.screen_width - 1, max(0, x))
        y = min(self.screen_height - 1, max(0, y))
        return x, y

    def to_json(self) -> dict:
        return {
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "samples": {k: v for k, v in self.samples.items()},
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
        }

    @classmethod
    def from_json(cls, data: dict) -> "MonocularCalibrator":
        cal = cls()
        cal.screen_width = data.get("screen_width")
        cal.screen_height = data.get("screen_height")
        if cal.screen_width and cal.screen_height:
            cal.screen_center_x = int(cal.screen_width) // 2
            cal.screen_center_y = int(cal.screen_height) // 2
        samples = data.get("samples", {})
        for k in cls.CALIB_SEQUENCE:
            v = samples.get(k)
            if v is not None:
                cal.samples[k] = (float(v[0]), float(v[1]))
        cal.scale_x = data.get("scale_x")
        cal.scale_y = data.get("scale_y")
        return cal

    def save_json(self, path: str) -> None:
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_json(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_json(cls, path: str) -> "MonocularCalibrator":
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_json(data)
