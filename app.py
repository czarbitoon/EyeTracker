"""
Thin launcher: run the modern MonocularTracker UI.

This file now forwards to `MonocularTracker.core.app.main` for a consistent,
feature-complete experience. Use `python run.py` or `python -m MonocularTracker.core.app`.
"""

import os
import sys

# Ensure project root is on sys.path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from MonocularTracker.core.app import main
except Exception as e:  # pragma: no cover
    print("Failed to import core app. Ensure dependencies are installed.")
    raise SystemExit(1)

if __name__ == "__main__":
    raise SystemExit(main())
