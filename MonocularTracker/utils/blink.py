"""
Blink detection using Eye Aspect Ratio (EAR) from MediaPipe eyelid landmarks.

States returned by update(): "open", "blink", "long_blink".

Usage patterns:
- Provide EAR directly: update(ear: float)
- Or provide eyelid landmarks (MediaPipe indices for right eye):
  indices 33 (outer), 133 (inner), 159 (upper lid), 145 (lower lid)
  e.g., update({33:(x,y), 133:(x,y), 159:(x,y), 145:(x,y)})
"""
from __future__ import annotations

import time
from typing import Dict, Optional, Tuple, Union

Point = Tuple[float, float]
LandmarkMap = Dict[int, Point]


class BlinkDetector:
    def __init__(
        self,
        enabled: bool = False,
        # thresholds
        blink_thresh: float = 0.21,  # EAR below this considered closed
        open_thresh: float = 0.25,   # EAR above this considered open (hysteresis)
        long_blink_ms: int = 300,
        min_blink_ms: int = 50,
        # Back-compat aliases
        ear_threshold: Optional[float] = None,
        min_duration_ms: Optional[int] = None,
    ) -> None:
        self.enabled = enabled
        if ear_threshold is not None:
            blink_thresh = ear_threshold
        if min_duration_ms is not None:
            min_blink_ms = min_duration_ms
        self.blink_thresh = float(blink_thresh)
        self.open_thresh = float(open_thresh)
        self.long_blink_ms = int(long_blink_ms)
        self.min_blink_ms = int(min_blink_ms)

        # State
        self._closed_since: Optional[float] = None
        self._announced_long: bool = False

    # Public API ---------------------------------------------------------
    def update(self, ear_or_landmarks: Union[float, LandmarkMap, None]) -> str:
        """Update detector with either EAR value or eyelid landmarks.

        Returns one of: "open", "blink", "long_blink".
        """
        if not self.enabled:
            return "open"

        ear: Optional[float]
        if isinstance(ear_or_landmarks, dict):
            ear = self._ear_from_landmarks(ear_or_landmarks)
        else:
            ear = float(ear_or_landmarks) if ear_or_landmarks is not None else None

        if ear is None or ear != ear:  # NaN check
            return "open"

        now = time.time() * 1000.0

        # Closed region
        if ear < self.blink_thresh:
            if self._closed_since is None:
                self._closed_since = now
                self._announced_long = False
                return "open"
            # Check long blink while still closed (optional early announcement)
            elapsed = now - self._closed_since
            if elapsed >= self.long_blink_ms and not self._announced_long:
                self._announced_long = True
                return "long_blink"
            return "open"

        # Open region (consider hysteresis)
        if ear >= self.open_thresh:
            if self._closed_since is not None:
                elapsed = now - self._closed_since
                self._closed_since = None
                was_long = elapsed >= self.long_blink_ms
                was_blink = (not was_long) and (elapsed >= self.min_blink_ms)
                if was_long:
                    return "long_blink"
                if was_blink:
                    return "blink"
            return "open"

        # In hysteresis band: keep previous trend, do not trigger
        return "open"

    # Helpers ------------------------------------------------------------
    @staticmethod
    def _euclid(a: Point, b: Point) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return (dx * dx + dy * dy) ** 0.5

    def _ear_from_landmarks(self, lm: LandmarkMap) -> Optional[float]:
        try:
            p_left = lm[33]
            p_right = lm[133]
            p_up = lm[159]
            p_down = lm[145]
        except KeyError:
            return None
        horiz = self._euclid(p_left, p_right)
        if horiz <= 0:
            return None
        vert = self._euclid(p_up, p_down)
        return float(vert / horiz)
