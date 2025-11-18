from __future__ import annotations

from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")  # safe fallback; switch to interactive if available
import matplotlib.pyplot as plt


def show_calibration_plots(screen: tuple[int, int], trues: List[Tuple[int, int]], preds: List[Tuple[int, int]]) -> None:
    try:
        # Try interactive if present
        try:
            matplotlib.use("Qt5Agg")
        except Exception:
            pass
        xs_t = [p[0] for p in trues]; ys_t = [p[1] for p in trues]
        xs_p = [p[0] for p in preds]; ys_p = [p[1] for p in preds]
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        ax.scatter(xs_t, ys_t, c='g', label='Target', alpha=0.6)
        ax.scatter(xs_p, ys_p, c='r', label='Predicted', alpha=0.6)
        ax.set_xlim(0, screen[0]); ax.set_ylim(0, screen[1])
        ax.set_title('Calibration Scatter')
        ax.legend()
        plt.tight_layout()
        plt.show()
    except Exception:
        pass
