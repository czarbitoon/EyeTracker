from __future__ import annotations

import sys
from typing import Tuple

# Minimal main wiring UI, camera, tracking
# For migration, we reuse existing PyQt UI but drive tracking via app.tracking.monocular
try:
    from PyQt6.QtWidgets import QApplication
except Exception:
    QApplication = None  # type: ignore

from app.tracking.monocular import MonocularTracker

# Reuse existing UI window if available
try:
    from MonocularTracker.ui.main_window import MainWindow
except Exception:
    MainWindow = None  # type: ignore


def main(screen_size: Tuple[int, int] = (1920, 1080)) -> None:
    # Headless fallback if PyQt not installed
    if QApplication is None or MainWindow is None:
        tracker = MonocularTracker(camera_index=0, screen_size=screen_size, drift_enabled=True, drift_lr=0.01, eye_mode="auto")
        tracker.start()
        try:
            for _ in range(300):  # run briefly
                res = tracker.process()
                if res.predicted_xy:
                    x, y = res.predicted_xy
                    print(f"Cursor: {x},{y}")
        finally:
            tracker.stop()
        return

    app = QApplication(sys.argv)
    win = MainWindow()

    tracker = MonocularTracker(camera_index=0, screen_size=screen_size, drift_enabled=True, drift_lr=0.01, eye_mode="auto")

    def on_start():
        tracker.start()

    def on_stop():
        tracker.stop()

    def tick():
        res = tracker.process()
        # Update minimal status label
        try:
            face = "OK" if res.face_ok else "--"
            eye = "OK" if res.eye_ok else "--"
            win.status_label.setText(f"Face: {face} | Eye: {eye} | FPS: {getattr(tracker.cam, 'target_fps', 30)}")
        except Exception:
            pass

    try:
        from PyQt6.QtCore import QTimer
        t = QTimer()
        t.timeout.connect(tick)  # type: ignore[attr-defined]
        t.start(0)
    except Exception:
        pass

    win.startRequested.connect(on_start)  # type: ignore[attr-defined]
    win.stopRequested.connect(on_stop)  # type: ignore[attr-defined]

    win.show()
    app.exec()


if __name__ == "__main__":
    main()
