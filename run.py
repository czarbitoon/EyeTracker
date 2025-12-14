"""App runner: import and run app.main.main()."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if os.name == "nt":
    dpi_mode = (os.environ.get("EYETRACKER_DPI_AWARENESS", "") or "").strip().lower()
    if dpi_mode not in ("0", "1", "2", "3"):
        dpi_mode = "2"
    os.environ.setdefault("QT_QPA_PLATFORM", f"windows:dpiawareness={dpi_mode}")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
