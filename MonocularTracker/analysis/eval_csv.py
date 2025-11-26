from __future__ import annotations

import csv
import math
import sys
from typing import List, Tuple


def load_csv(path: str) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], List[float]]:
    true_pts: List[Tuple[int, int]] = []
    pred_pts: List[Tuple[int, int]] = []
    dists: List[float] = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            tx = int(float(row["true_x"]))
            ty = int(float(row["true_y"]))
            px = int(float(row["pred_x"]))
            py = int(float(row["pred_y"]))
            true_pts.append((tx, ty))
            pred_pts.append((px, py))
            try:
                d = float(row.get("dist_px", "nan"))
                if math.isnan(d):
                    d = math.hypot(px - tx, py - ty)
            except Exception:
                d = math.hypot(px - tx, py - ty)
            dists.append(d)
    return true_pts, pred_pts, dists


def summarize(dists: List[float]) -> None:
    if not dists:
        print("No rows found.")
        return
    n = len(dists)
    mean = sum(dists) / n
    mx = max(dists)
    rms = math.sqrt(sum(d*d for d in dists) / n)
    q50 = sorted(dists)[n//2]
    q90 = sorted(dists)[int(0.9*n)]
    print(f"Samples: {n}")
    print(f"Mean error: {mean:.2f}px")
    print(f"RMS error:  {rms:.2f}px")
    print(f"Max error:  {mx:.2f}px")
    print(f"Median:     {q50:.2f}px | P90: {q90:.2f}px")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m MonocularTracker.analysis.eval_csv <path-to-csv>")
        raise SystemExit(2)
    _, preds, dists = load_csv(sys.argv[1])
    summarize(dists)
