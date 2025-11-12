"""
Calibration data models.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class CalibrationSample:
    feature: Tuple[float, float]  # (nx, ny)
    screen_xy: Tuple[int, int]    # (x, y) in pixels


@dataclass
class CalibrationConfig:
    samples_per_point: int = 20
