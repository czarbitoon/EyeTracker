"""Convenience launcher for MonocularTracker.

Allows running with:
  python run.py

Equivalent to:
  python -m MonocularTracker.core.app
"""
import os
import sys

# Ensure the project root (directory containing this file) is on sys.path.
# This is necessary when using the embedded Python distribution with a ._pth file,
# which disables automatic path configuration.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
  from MonocularTracker.core.app import main
except Exception:
  # fallback to legacy app entry if needed
  from MonocularTracker.app import main  # type: ignore

if __name__ == "__main__":
    raise SystemExit(main())
