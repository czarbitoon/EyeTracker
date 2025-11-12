from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import math
import numpy as np  # type: ignore


@dataclass
class PointError:
    true_xy: Tuple[int, int]
    pred_xy: Tuple[int, int]
    dist_px: float


def compute_point_errors(true_points: Sequence[Tuple[int, int]], predicted_points: Sequence[Tuple[int, int]]) -> List[PointError]:
    assert len(true_points) == len(predicted_points), "true and predicted lists must have same length"
    out: List[PointError] = []
    for t, p in zip(true_points, predicted_points):
        dx = float(p[0] - t[0])
        dy = float(p[1] - t[1])
        dist = math.hypot(dx, dy)
        out.append(PointError(true_xy=t, pred_xy=p, dist_px=dist))
    return out


def compute_mean_error(errors: Sequence[PointError]) -> float:
    if not errors:
        return 0.0
    return float(sum(e.dist_px for e in errors) / float(len(errors)))


def compute_max_error(errors: Sequence[PointError]) -> float:
    if not errors:
        return 0.0
    return float(max(e.dist_px for e in errors))


def compute_rms_error(errors: Sequence[PointError]) -> float:
    if not errors:
        return 0.0
    return float(math.sqrt(sum(e.dist_px * e.dist_px for e in errors) / float(len(errors))))


def compute_error_distribution(errors: Sequence[PointError], bin_width_px: float = 10.0) -> Tuple[np.ndarray, np.ndarray]:
    if not errors:
        return np.array([0.0]), np.array([0.0])
    dists = np.array([e.dist_px for e in errors], dtype=float)
    max_d = max(1.0, float(dists.max()))
    bins = int(math.ceil(max_d / bin_width_px))
    bins = max(5, min(100, bins))
    hist, edges = np.histogram(dists, bins=bins, range=(0.0, max_d))
    return hist.astype(float), edges.astype(float)


def compute_error_heatmap(
    errors: Sequence[PointError],
    screen_resolution: Tuple[int, int],
    grid: Tuple[int, int] = (64, 36),
    blur_sigma: float = 1.0,
) -> np.ndarray:
    """Return a heatmap grid (H, W) of error density weighted by distance.

    We bin true point locations and accumulate their error magnitudes. A simple Gaussian blur smooths the map.
    """
    W, H = int(screen_resolution[0]), int(screen_resolution[1])
    gw, gh = int(grid[0]), int(grid[1])
    gw = max(8, gw)
    gh = max(5, gh)
    heat = np.zeros((gh, gw), dtype=float)
    if not errors or W <= 0 or H <= 0:
        return heat
    for e in errors:
        tx, ty = e.true_xy
        ix = int(min(gw - 1, max(0, tx * gw // max(1, W))))
        iy = int(min(gh - 1, max(0, ty * gh // max(1, H))))
        heat[iy, ix] += float(e.dist_px)
    if blur_sigma > 0.0:
        # Simple separable kernel (approx Gaussian) of size 5
        k = np.array([1, 4, 6, 4, 1], dtype=float)
        k = (k / k.sum()).reshape(1, -1)
        heat = _convolve_separable(heat, k)
        heat = _convolve_separable(heat, k.T)
    return heat


def _convolve_separable(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    # Reflect padding
    pad = (k.shape[1] - 1) // 2 if k.shape[0] == 1 else (k.shape[0] - 1) // 2
    if k.shape[0] == 1:
        padded = np.pad(a, ((0, 0), (pad, pad)), mode="reflect")
        out = np.zeros_like(a)
        for i in range(out.shape[1]):
            window = padded[:, i : i + k.shape[1]]
            out[:, i] = (window * k).sum(axis=1)
    else:
        padded = np.pad(a, ((pad, pad), (0, 0)), mode="reflect")
        out = np.zeros_like(a)
        for i in range(out.shape[0]):
            window = padded[i : i + k.shape[0], :]
            out[i, :] = (window * k).sum(axis=0)
    return out
