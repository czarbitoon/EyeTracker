# Moved script: OptiKey click sequencer
# This utility script should not be imported by the application.
from __future__ import annotations

import argparse
import sys
import time
from typing import Tuple, List, Sequence

try:
    import pyautogui  # type: ignore
except Exception:
    pyautogui = None

# Copied from original for self-contained usage

def parse_bbox(s: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be 'left,top,right,bottom'")
    l, t, r, b = map(int, parts)
    if r <= l or b <= t:
        raise argparse.ArgumentTypeError("bbox invalid (right<=left or bottom<=top)")
    return l, t, r, b


def interactive_bbox() -> Tuple[int, int, int, int]:
    assert pyautogui is not None
    print("Hover over TOP-LEFT of OptiKey and press Enter...")
    input()
    l, t = pyautogui.position()
    print(f"Captured top-left: ({l},{t})")
    print("Hover over BOTTOM-RIGHT of OptiKey and press Enter...")
    input()
    r, b = pyautogui.position()
    print(f"Captured bottom-right: ({r},{b})")
    if r <= l or b <= t:
        raise RuntimeError("Invalid rectangle captured; try again.")
    return int(l), int(t), int(r), int(b)


def grid_points(bbox: Tuple[int, int, int, int], rows: int, cols: int, margin: float = 0.08) -> List[Tuple[int, int]]:
    l, t, r, b = bbox
    w = r - l
    h = b - t
    mx = int(w * margin)
    my = int(h * margin)
    l2, t2, r2, b2 = l + mx, t + my, r - mx, b - my
    w2 = max(1, r2 - l2)
    h2 = max(1, b2 - t2)
    pts: List[Tuple[int, int]] = []
    for ri in range(rows):
        cy = t2 + int((ri + 0.5) * (h2 / rows))
        for ci in range(cols):
            cx = l2 + int((ci + 0.5) * (w2 / cols))
            pts.append((cx, cy))
    return pts


def _capture_point(prompt: str) -> Tuple[int, int]:
    assert pyautogui is not None
    print(prompt)
    input()
    x, y = pyautogui.position()
    print(f"  -> {x},{y}")
    return int(x), int(y)


def rowspec_points(rowspec: Sequence[int]) -> List[Tuple[int, int]]:
    if any(c < 1 for c in rowspec):
        raise ValueError("rowspec counts must be >= 1")
    pts: List[Tuple[int, int]] = []
    print("Row-spec mode: For each row, capture LEFTMOST then RIGHTMOST key centers.")
    for idx, count in enumerate(rowspec, start=1):
        print(f"Row {idx} with {count} keys")
        lx, ly = _capture_point("Hover LEFTMOST key center for this row and press Enter...")
        rx, ry = _capture_point("Hover RIGHTMOST key center for this row and press Enter...")
        if rx == lx and count > 1:
            print("Warning: left and right X are equal; spreading minimally.")
            rx = lx + count - 1
        y = int(round((ly + ry) / 2))
        if count == 1:
            cx = int(round((lx + rx) / 2))
            pts.append((cx, y))
        else:
            for k in range(count):
                t = k / (count - 1)
                cx = int(round(lx + t * (rx - lx)))
                pts.append((cx, y))
    return pts


def main(argv: List[str]) -> int:
    if pyautogui is None:
        print("pyautogui not installed. Please install requirements.")
        return 1
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0

    parser = argparse.ArgumentParser(description="OptiKey click sequencer for calibration validation")
    parser.add_argument("--rows", type=int, default=4, help="Grid rows (keyboard rows)")
    parser.add_argument("--cols", type=int, default=10, help="Grid columns (keys per row)")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds to wait before starting")
    parser.add_argument("--click-delay", type=float, default=0.15, help="Delay between move and click")
    parser.add_argument("--between", type=float, default=0.35, help="Delay between key clicks")
    parser.add_argument("--bbox", type=parse_bbox, default=None, help="Bounding box 'l,t,r,b' for OptiKey window")
    parser.add_argument("--preview", action="store_true", help="Only move (no click)")
    parser.add_argument("--rowspec", type=str, default=None, help="Comma list of per-row key counts, e.g., '10,9,7' for rowspec mode")
    args = parser.parse_args(argv)

    if args.rows < 1 or args.cols < 1:
        print("rows and cols must be >= 1")
        return 1

    if args.rowspec:
        try:
            counts = [int(x.strip()) for x in args.rowspec.split(",") if x.strip()]
        except Exception:
            print("Invalid --rowspec; must be a comma-separated list of integers, e.g., '10,9,7'")
            return 1
        if not counts:
            print("--rowspec provided but empty")
            return 1
        print(f"Entering rowspec mode with counts: {counts}")
        pts = rowspec_points(counts)
    else:
        if args.bbox is None:
            print("No bbox provided; entering interactive box capture mode.")
            bbox = interactive_bbox()
        else:
            bbox = args.bbox
        print(f"Using bbox: {bbox}")
        pts = grid_points(bbox, rows=args.rows, cols=args.cols)

    print(f"Starting in {args.delay:.1f}s. Please bring OptiKey to front.")
    time.sleep(max(0.0, args.delay))

    for i, (x, y) in enumerate(pts, start=1):
        try:
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(max(0.0, args.click_delay))
            if not args.preview:
                pyautogui.click()
            print(f"[{i:03d}/{len(pts)}] {'clicked' if not args.preview else 'moved to'} {x},{y}")
        except Exception as e:
            print(f"Error at point {i}: {e}")
        time.sleep(max(0.0, args.between))

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
