"""
Event dataclasses (placeholder) for future expansion: dwell, blink, calibration events.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class GazeEvent:
    screen_xy: Tuple[int, int]
    raw_feature: Tuple[float, float]


@dataclass
class DwellEvent:
    screen_xy: Tuple[int, int]
    duration_ms: int


@dataclass
class BlinkEvent:
    count: int
