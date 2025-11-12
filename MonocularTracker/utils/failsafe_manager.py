"""
Fail-safe manager for cursor-only operation.

Responsibilities:
- Freeze cursor on face/eye loss
- Reject jitter spikes (sudden large jumps)
- Freeze on low FPS (long frame gaps)
- Drift-limit protection (if bias grows too large)
- Auto-sleep when idle for long

This module NEVER clicks. It only decides whether to allow moving the cursor
and optionally clamps the position to the last safe value.
"""
from __future__ import annotations

import time
from typing import Optional, Tuple


class FailsafeManager:
    def __init__(
        self,
        *,
        max_jump_ratio: float = 0.15,   # reject jumps > 15% of screen width
        max_frame_gap_s: float = 0.25,  # freeze if dt > 250ms
        max_drift_pixels: float = 120.0,  # if drift offset magnitude exceeds this, freeze corrections
        autosleep_idle_s: float = 120.0,  # after 2 minutes without movement, freeze
    ) -> None:
        self.max_jump_ratio = float(max_jump_ratio)
        self.max_frame_gap_s = float(max_frame_gap_s)
        self.max_drift_pixels = float(max_drift_pixels)
        self.autosleep_idle_s = float(autosleep_idle_s)

        self._last_xy: Optional[Tuple[int, int]] = None
        self._last_time = time.monotonic()
        self._frozen = False
        self._reason = ""
        self._last_move_time = self._last_time

    # Public API --------------------------------------------------------
    def reset(self) -> None:
        self._last_xy = None
        self._frozen = False
        self._reason = ""
        now = time.monotonic()
        self._last_time = now
        self._last_move_time = now

    def is_frozen(self) -> bool:
        return self._frozen

    def reason(self) -> str:
        return self._reason

    def process(
        self,
        candidate_xy: Optional[Tuple[int, int]],
        *,
        features_present: bool,
        screen_size: Tuple[int, int],
        drift_offset: Optional[Tuple[float, float]] = None,
    ) -> Optional[Tuple[int, int]]:
        """Return allowed position or None to freeze.
        
        - candidate_xy may be None (e.g., no feature this frame) -> freeze
        - features_present False -> freeze
        - low FPS -> freeze
        - spike rejection -> clamp to last position
        - drift-limit -> freeze if exceeded
        - auto-sleep -> freeze after long idle
        """
        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now

        # Low FPS freeze
        if dt > self.max_frame_gap_s:
            self._frozen = True
            self._reason = "low-fps"
            return None

        if not features_present or candidate_xy is None:
            self._frozen = True
            self._reason = "no-features"
            return None

        # Drift limit protection (do not allow large corrections)
        if drift_offset is not None:
            ox, oy = drift_offset
            if (ox * ox + oy * oy) ** 0.5 > self.max_drift_pixels:
                self._frozen = True
                self._reason = "drift-limit"
                return None

        # Spike rejection
        if self._last_xy is not None:
            w = max(1, int(screen_size[0]))
            max_jump = w * self.max_jump_ratio
            dx = float(candidate_xy[0] - self._last_xy[0])
            dy = float(candidate_xy[1] - self._last_xy[1])
            if (dx * dx + dy * dy) ** 0.5 > max_jump:
                # Reject spike: clamp to last
                candidate_xy = self._last_xy

        # Auto-sleep (idle)
        if self._last_xy is not None and candidate_xy == self._last_xy:
            if (now - self._last_move_time) > self.autosleep_idle_s:
                self._frozen = True
                self._reason = "autosleep"
                return None
        else:
            self._last_move_time = now

        # All checks passed -> allow
        self._frozen = False
        self._reason = ""
        self._last_xy = candidate_xy
        return candidate_xy
