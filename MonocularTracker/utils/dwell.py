"""
Dwell click detection utilities.

- DwellClickDetector: existing configurable API used by the app.
- DwellClicker: requested simple API with fixed 40px radius and check(pos) method.
"""
from __future__ import annotations

import time
from typing import Tuple, Optional


class DwellClickDetector:
    def __init__(self, enabled: bool = True, dwell_time_ms: int = 600, radius_px: int = 25) -> None:
        self.enabled = enabled
        self.dwell_time_ms = dwell_time_ms
        self.radius_px = radius_px
        self._anchor: Optional[Tuple[int, int]] = None
        self._anchor_time: float = 0.0

    def reset(self) -> None:
        self._anchor = None
        self._anchor_time = 0.0

    def update(self, xy: Tuple[int, int]) -> bool:
        if not self.enabled:
            return False
        now = time.time() * 1000.0
        if self._anchor is None:
            self._anchor = xy
            self._anchor_time = now
            return False
        ax, ay = self._anchor
        x, y = xy
        dx = x - ax
        dy = y - ay
        if (dx * dx + dy * dy) <= (self.radius_px * self.radius_px):
            if now - self._anchor_time >= self.dwell_time_ms:
                # Reset anchor after click so consecutive clicks require fresh dwell
                self._anchor = xy
                self._anchor_time = now
                return True
            return False
        # Moved outside radius: new anchor
        self._anchor = xy
        self._anchor_time = now
        return False


class DwellClicker:
    """Simple dwell clicker: returns True if the cursor stays within 40px
    of the anchor position for at least dwell_ms milliseconds.

    Behavior:
    - The first check(pos) sets the anchor and starts the timer.
    - Moving outside the 40px radius resets the anchor and timer.
    - When the dwell time elapses inside the radius, returns True once and
      restarts the anchor at the current position (debounce for next click).
    """

    def __init__(self, dwell_ms: int = 600) -> None:
        self.dwell_ms = int(dwell_ms)
        self._anchor: Optional[Tuple[int, int]] = None
        self._anchor_time: float = 0.0
        self._r_px = 40
        self._r2 = self._r_px * self._r_px

    def reset(self) -> None:
        self._anchor = None
        self._anchor_time = 0.0

    def check(self, pos: Tuple[int, int]) -> bool:
        now = time.time() * 1000.0
        if self._anchor is None:
            self._anchor = pos
            self._anchor_time = now
            return False

        ax, ay = self._anchor
        x, y = pos
        dx = x - ax
        dy = y - ay
        if (dx * dx + dy * dy) <= self._r2:
            if (now - self._anchor_time) >= self.dwell_ms:
                # Debounce: restart anchor so subsequent clicks require a fresh dwell
                self._anchor = pos
                self._anchor_time = now
                return True
            return False
        # Movement outside radius: reset timer/anchor
        self._anchor = pos
        self._anchor_time = now
        return False
