from __future__ import annotations

from typing import List, Tuple

import numpy as np  # type: ignore
import matplotlib
matplotlib.use("Agg")  # headless-safe backend; canvases will set interactive backend
import matplotlib.pyplot as plt  # type: ignore

from .error_metrics import PointError


def fig_scatter(true_pts: List[Tuple[int, int]], pred_pts: List[Tuple[int, int]], errors: List[PointError]):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title("Calibration Error Scatter Plot")
    tp = np.array(true_pts)
    pp = np.array(pred_pts)
    if len(tp) > 0:
        ax.scatter(tp[:, 0], tp[:, 1], c="green", label="True")
    if len(pp) > 0:
        ax.scatter(pp[:, 0], pp[:, 1], c="red", label="Predicted")
    for e in errors:
        ax.plot([e.true_xy[0], e.pred_xy[0]], [e.true_xy[1], e.pred_xy[1]], c="orange", linewidth=1)
        ax.text(e.pred_xy[0], e.pred_xy[1], f"{int(round(e.dist_px))} px", fontsize=8, color="orange")
    ax.legend(loc="best")
    ax.set_xlabel("X (px)")
    ax.set_ylabel("Y (px)")
    ax.invert_yaxis()  # screen coordinates origin top-left
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def fig_vectors(true_pts: List[Tuple[int, int]], pred_pts: List[Tuple[int, int]]):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title("Gaze Error Vectors")
    if not true_pts:
        fig.tight_layout()
        return fig
    tp = np.array(true_pts)
    pp = np.array(pred_pts) if pred_pts else np.zeros_like(tp)
    dx = pp[:, 0] - tp[:, 0]
    dy = pp[:, 1] - tp[:, 1]
    # Normalize vectors visually to avoid very long arrows dominating
    mag = np.sqrt(dx * dx + dy * dy) + 1e-6
    scale = np.clip(50.0 / np.max(mag), 0.2, 2.0)
    ax.quiver(tp[:, 0], tp[:, 1], dx * scale, dy * scale, angles='xy', scale_units='xy', scale=1, color='red')
    ax.scatter(tp[:, 0], tp[:, 1], c="green", label="True")
    ax.legend(loc="best")
    ax.set_xlabel("X (px)")
    ax.set_ylabel("Y (px)")
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def fig_heatmap(heatmap: np.ndarray, screen_resolution: Tuple[int, int]):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title("Error Heatmap")
    im = ax.imshow(heatmap, cmap="hot", origin="upper", interpolation="nearest")
    fig.colorbar(im, ax=ax, label="Weighted error")
    ax.set_xlabel("X bins")
    ax.set_ylabel("Y bins")
    fig.tight_layout()
    return fig


def fig_histogram(errors: List[PointError], threshold_px: float = 50.0):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title("Error Distribution")
    dists = np.array([e.dist_px for e in errors], dtype=float) if errors else np.zeros((1,), dtype=float)
    ax.hist(dists, bins=20, color='steelblue', edgecolor='black', alpha=0.8)
    ax.axvline(threshold_px, color='red', linestyle='--', label=f'Threshold {int(threshold_px)} px')
    ax.set_xlabel("Error (px)")
    ax.set_ylabel("Count")
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def fig_summary(mean_px: float, max_px: float, rms_px: float):
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.axis('off')
    text = f"Mean: {mean_px:.1f} px\nMax: {max_px:.1f} px\nRMS: {rms_px:.1f} px"
    ax.text(0.1, 0.7, text, fontsize=14, va='top')
    fig.tight_layout()
    return fig
