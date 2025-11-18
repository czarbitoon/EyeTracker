from __future__ import annotations

import sys
import os

from PyQt5.QtWidgets import QApplication

from MonocularEyeAssist.core.app import AppCore


def main() -> int:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    app = QApplication(sys.argv)
    core = AppCore()
    core.win.show()
    code = app.exec_()
    try:
        core.shutdown()
    except Exception:
        pass
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
