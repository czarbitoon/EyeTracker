"""
MonocularTracker: App entry point

High-level flow:
- Capture frames from camera
- Parse right-eye landmarks with MediaPipe FaceMesh (refine_landmarks=True)
- Extract iris center + eyelid bounding box; normalize to (nx, ny) in [0,1]
- If calibrated and model trained, map (nx, ny) -> screen (x, y)
- Smooth cursor motion (EMA); detect dwell for clicking; optional blink detection
- Move OS cursor and click via pyautogui so OptiKey sees normal mouse input

Notes:
- Imports for heavy deps are guarded so the project imports even if not yet installed.
- This is a scaffold with minimal glue; fill in TODOs as you iterate.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Optional, Tuple
import weakref

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

# Allow running this file directly (e.g. `python MonocularTracker/app.py`) by
# ensuring the parent directory is on sys.path so absolute imports work.
if __package__ is None or __package__ == "":  # pragma: no cover - runtime convenience
    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.dirname(parent))  # add project root


try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover - optional at import time
    pyautogui = None  # Will be checked at runtime

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    QApplication = None  # type: ignore
    QTimer = None  # type: ignore

# Local imports (absolute form so they work both as package module and direct script)
from MonocularTracker.camera import Camera
from MonocularTracker.gaze_parser import GazeParser, GazeFeatures
from MonocularTracker.utils.smoothing import EmaSmoother
from MonocularTracker.utils.failsafe_manager import FailsafeManager
from MonocularTracker.control.cursor import CursorController
from MonocularTracker.calibration.calibrator import Calibrator
from MonocularTracker.ai.drift_corrector import DriftCorrector
from MonocularTracker.ui.calibration_ui import CalibrationUI
from MonocularTracker.ui.overlay import Overlay


def load_settings(settings_path: str) -> dict:
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Missing settings file: {settings_path}")
    with open(settings_path, "r", encoding="utf-8") as f:
        return json.load(f)


class App:
    def __init__(
        self,
        settings: dict,
        *,
        enable_cursor: bool = True,
        auto_start_calibration: bool = False,
    ) -> None:
        self.settings = settings
        self.enable_cursor = bool(enable_cursor)
        self.auto_start_calibration = bool(auto_start_calibration)
        self.tracking_enabled = False  # gated by Start Tracking and panic mode
        self._panic_overlay = None  # type: ignore[assignment]
        self.camera = Camera(index=settings.get("camera_index", 0))
        self.parser = GazeParser(right_eye_only=True)

        # Calibration and drift correction
        # Attempt to load previous calibration if available
        self.calibration_path = os.path.join(os.path.dirname(__file__), "calibration_state.json")
        try:
            self.calibrator = Calibrator.load(self.calibration_path)
        except Exception:
            self.calibrator = Calibrator(None)
        self.drift = DriftCorrector(enabled=bool(settings.get("use_drift_correction", True)))

        # Smoothing and detectors
        alpha = float(settings.get("smoothing", {}).get("alpha", 0.2))
        self.smoother = EmaSmoother(alpha=alpha)

        # Fail-safe manager (no clicking, only freeze decisions)
        self.failsafe = FailsafeManager()

        self.cursor = CursorController()

        # UI
        self.overlay: Optional[Overlay] = None
        if bool(settings.get("overlay", {}).get("enabled", True)):
            self.overlay = Overlay()

        calib_cfg = settings.get("calibration", {})
        self.calib_ui = CalibrationUI(
            points_count=int(calib_cfg.get("points", 9)),  # kept for compatibility, ignored internally
            samples_per_point=int(calib_cfg.get("samples_per_point", 25)),
            dwell_ms=int(calib_cfg.get("dwell_ms", 1500)),
        )
        self.calib_ui.sampleRequested.connect(self._on_calibration_sample_requested)
        self.calib_ui.calibrationFinished.connect(self._on_calibration_finished)

        # Timer loop (approx 30 FPS)
        self.timer = QTimer()
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._on_tick)

        # Screen size
        try:
            self.screen_w, self.screen_h = pyautogui.size() if pyautogui else (1920, 1080)
        except Exception:
            self.screen_w, self.screen_h = (1920, 1080)

        # Camera reference window option
        cam_cfg = settings.get("camera", {})
        self.show_camera_window = bool(cam_cfg.get("show_window", True))

    def start(self) -> None:
        # Tracking only runs when explicitly enabled
        if not self.tracking_enabled:
            return
        self.camera.open()
        self.timer.start()
        # Auto calibration only when explicitly requested via flag
        if self.auto_start_calibration:
            self.calib_ui.start()

    def stop(self) -> None:
        self.timer.stop()
        self.camera.close()

    # Panic handling
    def show_panic_overlay(self) -> None:
        try:
            if self._panic_overlay is None:
                from MonocularTracker.ui.panic_overlay import PanicOverlay
                self._panic_overlay = PanicOverlay()
            self._panic_overlay.show()  # type: ignore[operator]
            self._panic_overlay.raise_()  # type: ignore[attr-defined]
        except Exception:
            pass

    def hide_panic_overlay(self) -> None:
        try:
            if self._panic_overlay is not None:
                self._panic_overlay.close()  # type: ignore[operator]
        except Exception:
            pass
        self._panic_overlay = None

    # Main loop
    def _on_tick(self) -> None:
        # Respect panic/disabled state immediately
        if not self.tracking_enabled:
            return
        frame = self.camera.read()
        if frame is None:
            return

        features: Optional[GazeFeatures] = self.parser.process(frame)
        if features is None:
            return

        # Compute target screen position: either via trained model or fallback normalization
        if self.calibrator.is_trained:
            x, y = self.calibrator.predict((features.nx, features.ny))
        else:
            # Fallback: map normalized gaze to screen directly
            x = int(self.screen_w * features.nx)
            y = int(self.screen_h * features.ny)

        # Drift correction and smoothing
        # Apply small drift correction (disabled during calibration)
        if self.auto_start_calibration:
            xy_corr = (x, y)
        else:
            xy_corr = self.drift.correct((x, y))
        sx, sy = self.smoother.update(xy_corr)

        # Fail-safes
        allowed = self.failsafe.process(
            (sx, sy),
            features_present=(features is not None),
            screen_size=(self.screen_w, self.screen_h),
            drift_offset=self.drift.offset() if hasattr(self.drift, "offset") else None,
        )

        # Cursor movement only (no clicking)
        if allowed is not None and self.enable_cursor and self.tracking_enabled:
            ax, ay = allowed
            self.cursor.move_cursor(ax, ay)

        # Overlay feedback
        if self.overlay:
            self.overlay.update_gaze((sx, sy), features)

        # Reference camera output window (optional)
        if self.show_camera_window and cv2 is not None:
            try:
                cv2.imshow("MonocularTracker Camera", frame)
                cv2.waitKey(1)
            except Exception:
                pass

    # Calibration handlers
    def _on_calibration_sample_requested(self, target_pos: Tuple[int, int]) -> None:
        # Capture a small burst of samples at current gaze estimate
        # In a real implementation, average multiple frames during dwell over the target dot.
        frame = self.camera.read()
        if frame is None:
            return
        features = self.parser.process(frame)
        if features is None:
            return
        self.calibrator.add_sample((features.nx, features.ny), target_pos)

    def _on_calibration_finished(self) -> None:
        self.calibrator.train()
        # Save trained model state
        try:
            self.calibrator.save(self.calibration_path)
        except Exception as e:
            print(f"Warning: failed to save calibration: {e}")
        # After calibration, resume safe defaults
        self.auto_start_calibration = False
        self.tracking_enabled = False
        self.enable_cursor = False


_app_controller_singleton: Optional[App] = None
_launcher_ref: Optional[weakref.ReferenceType] = None


def start_tracking(parent_widget=None) -> None:
    """Start the main tracking loop after showing a safety confirmation.

    This will enable cursor control and begin processing frames. Safe by default: nothing runs
    until this function is called.
    """
    global _app_controller_singleton
    if QApplication is None:
        print("PyQt6 is not installed. Please install dependencies from requirements.txt.")
        return

    # Safety confirmation dialog
    try:
        from PyQt6.QtWidgets import QMessageBox
        confirm = QMessageBox(parent_widget)
        confirm.setWindowTitle("Safety Notice")
        confirm.setText(
            "Cursor will now be controlled by eye movement. Move away from the camera or press ESC to stop."
        )
        confirm.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        ret = confirm.exec()
        if ret != int(QMessageBox.StandardButton.Ok):
            return
    except Exception:
        # Headless fallback: continue without dialog
        pass

    settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
    settings = load_settings(settings_path)

    if pyautogui:
        try:
            pyautogui.FAILSAFE = False
        except Exception:
            pass

    if _app_controller_singleton is None:
        _app_controller_singleton = App(settings, enable_cursor=True, auto_start_calibration=False)
    # Enable tracking and cursor, show panic overlay, then start loop
    _app_controller_singleton.enable_cursor = True
    _app_controller_singleton.tracking_enabled = True
    _app_controller_singleton.show_panic_overlay()
    _app_controller_singleton.start()


def run_calibration(parent_widget=None) -> None:
    """Run calibration workflow with cursor control disabled.

    Opens the fullscreen CalibrationUI, collects samples, trains the model, and saves it. The
    OS cursor is not moved during this process.
    """
    global _app_controller_singleton
    if QApplication is None:
        print("PyQt6 is not installed. Please install dependencies from requirements.txt.")
        return

    settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
    settings = load_settings(settings_path)

    # Create a temporary controller for calibration only if tracking is not already running
    controller = _app_controller_singleton
    created_temp = False
    if controller is None:
        controller = App(settings, enable_cursor=False, auto_start_calibration=True)
        created_temp = True
    else:
        # If tracking controller exists, ensure we disable cursor and start calibration UI
        controller.enable_cursor = False
        controller.auto_start_calibration = True

    # Start camera/timers if not already running
    # Do not enable tracking; only open camera/timer to gather samples if auto_start_calibration
    controller.tracking_enabled = True  # enable loop for calibration sampling
    controller.enable_cursor = False
    controller.start()

    # If controller already existed, just start calibration UI now
    if not created_temp:
        try:
            controller.calib_ui.start()
        except Exception:
            pass

    # When calibration finishes, restore safe defaults and stop temp controller
    def _on_done():
        try:
            controller.auto_start_calibration = False
            controller.enable_cursor = False  # remain safe until Start Tracking is requested
            controller.tracking_enabled = False
            if created_temp:
                controller.stop()
            controller.hide_panic_overlay()
        except Exception:
            pass
def trigger_panic() -> None:
    """Global panic: immediately stop tracking and return to the launcher."""
    global _app_controller_singleton
    # Stop tracking immediately
    try:
        from PyQt6.QtWidgets import QMessageBox
    except Exception:
        QMessageBox = None  # type: ignore

    ctl = _app_controller_singleton
    if ctl is not None:
        # Disable movement first to stop mid-frame effects
        ctl.enable_cursor = False
        ctl.tracking_enabled = False
        try:
            ctl.timer.stop()
        except Exception:
            pass
        try:
            ctl.camera.close()
        except Exception:
            pass
        ctl.hide_panic_overlay()

    # Inform user (modal)
    try:
        if QMessageBox is not None:
            # Use the launcher as parent if available for modality
            parent = _launcher_ref() if (_launcher_ref is not None and _launcher_ref()) else None
            QMessageBox.information(parent, "Safety", "Tracking stopped for safety. Cursor control disabled.")
    except Exception:
        pass

    # Return focus to launcher
    try:
        launcher = _launcher_ref() if (_launcher_ref is not None) else None
        if launcher is not None:
            launcher.show()
            launcher.raise_()
            launcher.activateWindow()
    except Exception:
        pass


def _install_global_panic_shortcuts(host_widget) -> None:
    """Install SPACE and ESC as application-wide panic shortcuts."""
    try:
        from PyQt6.QtGui import QKeySequence
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QShortcut
    except Exception:
        return
    for key in (QKeySequence(Qt.Key.Key_Space), QKeySequence(Qt.Key.Key_Escape)):
        sc = QShortcut(key, host_widget)
        try:
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        except Exception:
            pass
        sc.activated.connect(trigger_panic)  # type: ignore[attr-defined]

    try:
        controller.calib_ui.calibrationFinished.connect(_on_done)  # type: ignore[attr-defined]
    except Exception:
        pass


def main() -> int:
    if QApplication is None:
        print("PyQt6 is not installed. Please install dependencies from requirements.txt.")
        return 1
    app = QApplication(sys.argv)

    # Show the safe-start launcher UI. No camera or tracking is started here.
    try:
        from MonocularTracker.ui.launcher_ui import LauncherUI  # import lazily to avoid circular import
        launcher = LauncherUI()
        # Save weakref for panic return path
        global _launcher_ref
        _launcher_ref = weakref.ref(launcher)
        _install_global_panic_shortcuts(launcher)
        launcher.show()
    except Exception as e:
        print(f"Failed to launch UI: {e}")
        return 1

    exit_code = app.exec()
    # Ensure any running controller is stopped on exit
    global _app_controller_singleton
    if _app_controller_singleton is not None:
        try:
            _app_controller_singleton.stop()
        except Exception:
            pass
        _app_controller_singleton = None
    # Close camera window if open
    try:
        if cv2 is not None:
            cv2.destroyWindow("MonocularTracker Camera")
    except Exception:
        pass
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
