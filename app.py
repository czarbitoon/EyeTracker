"""
Standalone app main loop (OpenCV window) for MonocularTracker.

Flow:
- Initialize Camera, GazeParser, Calibrator, Smoother, DwellClicker, Cursor
- Load calibration if it exists; otherwise launch PyQt6 CalibrationUI and save model
- Capture frames, extract monocular features (RIGHT eye only)
- Predict screen coordinates (calibrated model or fallback mapping)
- Apply smoothing, move OS cursor, dwell-click, and show debug frame
- Press ESC to exit
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional, Tuple

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover
    pyautogui = None  # type: ignore

from MonocularTracker.camera import Camera
from MonocularTracker.gaze_parser import GazeParser, GazeFeatures
from MonocularTracker.calibration.calibrator import Calibrator
from MonocularTracker.utils.smoothing import Smoother
from MonocularTracker.utils.dwell import DwellClicker
from MonocularTracker.control.cursor import CursorController

# Optional UI for calibration
try:
    from PyQt6.QtWidgets import QApplication
    from MonocularTracker.ui.calibration_ui import CalibrationUI
except Exception:  # pragma: no cover
    QApplication = None  # type: ignore
    CalibrationUI = None  # type: ignore


def load_settings() -> dict:
    settings_path = os.path.join(os.path.dirname(__file__), "MonocularTracker", "settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def run_calibration_ui(camera: Camera, parser: GazeParser, calib_path: str) -> Optional[Calibrator]:
    if QApplication is None or CalibrationUI is None:
        print("Calibration UI unavailable (PyQt6 not installed). Skipping calibration.")
        return None

    app = QApplication.instance() or QApplication(sys.argv)
    calibrator = Calibrator(None)

    ui = CalibrationUI(
        samples_per_point=25,
        dwell_ms=1500,
    )

    def on_sample_requested(pos: Tuple[int, int]):
        frame = camera.read()
        if frame is None:
            return
        feats = parser.process(frame)
        if feats is None:
            return
        calibrator.add_sample((feats.nx, feats.ny), pos)

    def on_finished():
        calibrator.train()
        try:
            calibrator.save(calib_path)
        except Exception as e:
            print(f"Warning: failed to save calibration: {e}")

    ui.sampleRequested.connect(on_sample_requested)  # type: ignore[attr-defined]
    ui.calibrationFinished.connect(on_finished)  # type: ignore[attr-defined]
    ui.start()
    app.exec()
    if calibrator.is_trained:
        return calibrator
    return None


def main() -> int:
    if cv2 is None:
        print("OpenCV not installed")
        return 1

    # Settings and screen size
    settings = load_settings()
    try:
        if pyautogui:
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0
            screen_w, screen_h = pyautogui.size()
        else:
            screen_w, screen_h = (1920, 1080)
    except Exception:
        screen_w, screen_h = (1920, 1080)

    # Components
    camera = Camera(index=settings.get("camera_index", 0), width=1280, height=720, target_fps=30)
    parser = GazeParser(right_eye_only=True)
    smoother = Smoother(alpha=float(settings.get("smoothing", {}).get("alpha", 0.6)))
    dwell_ms = int(settings.get("dwell", {}).get("time_ms", 700))
    clicker = DwellClicker(dwell_ms=dwell_ms)
    cursor = CursorController()

    calib_path = os.path.join(os.path.dirname(__file__), "MonocularTracker", "calibration_state.json")

    # Open camera
    try:
        camera.open()
    except Exception as e:
        print(f"Failed to open camera: {e}")
        return 1

    # Load or run calibration
    calibrator: Optional[Calibrator] = None
    if os.path.exists(calib_path):
        try:
            calibrator = Calibrator.load(calib_path)
            print("Loaded calibration.")
        except Exception as e:
            print(f"Failed to load calibration: {e}")
            calibrator = None
    if calibrator is None:
        print("Starting calibration UI...")
        calibrated = run_calibration_ui(camera, parser, calib_path)
        if calibrated is not None:
            calibrator = calibrated
        else:
            print("Calibration not completed; will use fallback mapping.")

    # Main loop
    print("Starting main loop. Press ESC to exit.")
    try:
        while True:
            frame = camera.read()
            if frame is None:
                continue
            feats: Optional[GazeFeatures] = parser.process(frame, debug=True)
            if feats is None:
                cv2.imshow("MonocularTracker", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
                continue

            # Predict screen position
            if calibrator and calibrator.is_trained:
                tx, ty = calibrator.predict((feats.nx, feats.ny))
            else:
                tx = int(screen_w * feats.nx)
                ty = int(screen_h * feats.ny)

            # Smooth
            sxy = smoother.apply((tx, ty))
            if sxy is None:
                sxy = (tx, ty)
            sx, sy = sxy

            # Move cursor
            cursor.move_cursor(sx, sy)

            # Dwell click
            if clicker.check((sx, sy)):
                cursor.left_click()

            # Show debug frame
            cv2.imshow("MonocularTracker", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        camera.close()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
