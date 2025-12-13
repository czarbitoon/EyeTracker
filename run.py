"""Convenience launcher for MonocularTracker.

Preferred entry: `python run.py`
Equivalent module form: `python -m MonocularTracker.core.app`
Falls back to `MonocularTracker.app` if core UI import fails.
"""
import os
import sys

# Ensure the project root (directory containing this file) is on sys.path.
# This is necessary when using the embedded Python distribution with a ._pth file,
# which disables automatic path configuration.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows High-DPI: avoid Qt attempting PER_MONITOR_AWARE_V2 when blocked by policy.
# Set a safer default DPI awareness before importing PyQt6/Qt.
if os.name == "nt":
  # Allow override via env: set EYETRACKER_DPI_AWARENESS to one of: 0, 1, 2, 3
  # 0=unaware, 1=system, 2=per-monitor (v1), 3=per-monitor (v2)
  dpi_mode = (os.environ.get("EYETRACKER_DPI_AWARENESS", "") or "").strip().lower()
  # Default to per-monitor v1, which avoids the SetProcessDpiAwarenessContext "Access is denied" on some systems
  if dpi_mode not in ("0", "1", "2", "3"):
    dpi_mode = "2"
  # Only set if not already specified by user
  os.environ.setdefault("QT_QPA_PLATFORM", f"windows:dpiawareness={dpi_mode}")
  # Enable Qt high-DPI scaling and sane rounding policy
  os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
  os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

try:
  from MonocularTracker.core.app import main
except Exception as e:  # pragma: no cover
  print("Failed to import MonocularTracker.core.app:", e)
  print("Install dependencies with 'pip install -r requirements.txt'.")
  raise SystemExit(1)

if __name__ == "__main__":
    raise SystemExit(main())
