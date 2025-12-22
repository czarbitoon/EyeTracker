from __future__ import annotations

"""
Cursor mapping utilities.

CursorMapper maps normalized gaze coordinates (0..1) to screen pixels
with a small center dead-zone and edge clamping. No OS cursor movement
occurs in this module.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ScreenSpec:
    width: int
    height: int


class CursorMapper:
    """
    Map normalized gaze (gx, gy) in [0, 1] to screen pixel coordinates.

    Features:
    - Center dead-zone: small area around the center where small jitter is ignored.
    - Edge clamping: output is clamped to [0, width-1] x [0, height-1].

    Notes:
    - No OS cursor movement here; this class only computes coordinates.
    - Dead-zone is expressed as a fraction of screen dimensions.
    """

    def __init__(self, screen_width: int, screen_height: int, dead_zone_frac: float = 0.05) -> None:
        if screen_width <= 0 or screen_height <= 0:
            raise ValueError("screen dimensions must be positive")
        if not (0.0 <= dead_zone_frac < 0.5):
            raise ValueError("dead_zone_frac must be in [0, 0.5)")
        self.spec = ScreenSpec(screen_width, screen_height)
        self.dead_zone_frac = float(dead_zone_frac)

        # Precompute center and dead-zone bounds in pixels
        self._cx = self.spec.width // 2
        self._cy = self.spec.height // 2
        self._dzx = int(self.spec.width * self.dead_zone_frac)
        self._dzy = int(self.spec.height * self.dead_zone_frac)

    def map(self, gx: float, gy: float) -> Tuple[int, int]:
        """Map normalized gaze to screen coordinates with dead-zone + clamping.

        Parameters:
        - gx, gy: normalized gaze in [0,1]. Values outside will be clamped.

        Returns:
        - (x, y): integer screen coordinates within display bounds.
        """
        # Clamp inputs to [0,1]
        if gx != gx or gy != gy:  # NaN check
            gx, gy = 0.5, 0.5
        gx = min(1.0, max(0.0, float(gx)))
        gy = min(1.0, max(0.0, float(gy)))

        # Convert to pixels
        x = int(round(gx * (self.spec.width - 1)))
        y = int(round(gy * (self.spec.height - 1)))

        # Center dead-zone: if inside rectangle around center, snap to center
        if (self._cx - self._dzx) <= x <= (self._cx + self._dzx) and (
            (self._cy - self._dzy) <= y <= (self._cy + self._dzy)
        ):
            x, y = self._cx, self._cy

        # Final clamping to screen bounds
        x = min(self.spec.width - 1, max(0, x))
        y = min(self.spec.height - 1, max(0, y))
        return x, y
