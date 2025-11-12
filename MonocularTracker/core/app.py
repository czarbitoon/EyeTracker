from __future__ import annotations

from typing import Optional, Tuple

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QMessageBox
except Exception:  # pragma: no cover
    QApplication = None  # type: ignore
    QTimer = None  # type: ignore

import os
import sys
import weakref

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover
    pyautogui = None

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

from MonocularTracker.core.settings import SettingsManager
from MonocularTracker.ui.main_window import MainWindow
from MonocularTracker.ui.panic_overlay import PanicOverlay
from MonocularTracker.ui.calibration_ui import CalibrationUI
from MonocularTracker.ui.calibration_plots import CalibrationPlotsWindow
try:
    # Prefer the enhanced camera settings dialog
    from MonocularTracker.ui.camera_settings import CameraSettingsWindow  # type: ignore
except Exception:  # pragma: no cover
    try:
        from MonocularTracker.ui.camera_settings_panel import CameraSettingsWindow  # type: ignore
    except Exception:
        CameraSettingsWindow = None  # type: ignore
from MonocularTracker.tracking.camera_controller import CameraController
from MonocularTracker.tracking.pipeline import Pipeline
from MonocularTracker.control.cursor import CursorController
from MonocularTracker.control.fps_monitor import FPSMonitor


class AppCore:
    def __init__(self) -> None:
        self.settings = SettingsManager()
        if pyautogui:
            try:
                pyautogui.FAILSAFE = False
                pyautogui.PAUSE = 0
            except Exception:
                pass
        self.cursor = CursorController()
        self.timer = QTimer()
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._on_tick)  # type: ignore[attr-defined]
        self.fps = FPSMonitor(window=60)

        self.win = MainWindow()
        self.win.startRequested.connect(self.start_tracking)  # type: ignore[attr-defined]
        self.win.stopRequested.connect(self.stop_tracking)  # type: ignore[attr-defined]
        self.win.calibrate5Requested.connect(lambda: self.start_calibration(points=5))  # type: ignore[attr-defined]
        self.win.calibrate9Requested.connect(lambda: self.start_calibration(points=9))  # type: ignore[attr-defined]
        try:
            self.win.cameraSettingsRequested.connect(self.open_camera_settings)  # type: ignore[attr-defined]
        except Exception:
            pass
        # Wire Fail-Safe button if present
        try:
            if hasattr(self.win, "btn_panic"):
                self.win.btn_panic.clicked.connect(self.trigger_panic)  # type: ignore[attr-defined]
        except Exception:
            pass
        # Wire basic camera settings tab controls if present
        try:
            if hasattr(self.win, "btn_apply_cam"):
                self.win.btn_apply_cam.clicked.connect(self._apply_basic_camera_tab)  # type: ignore[attr-defined]
            if hasattr(self.win, "sld_brightness"):
                self.win.sld_brightness.valueChanged.connect(lambda _: self._cam_controller.set_brightness(float(self.win.sld_brightness.value())))  # type: ignore[attr-defined]
            if hasattr(self.win, "sld_contrast"):
                self.win.sld_contrast.valueChanged.connect(lambda _: self._cam_controller.set_contrast(float(self.win.sld_contrast.value())))  # type: ignore[attr-defined]
        except Exception:
            pass
        self._panic_overlay: Optional[PanicOverlay] = None
        self._install_panic_shortcuts(self.win)
        self._win_ref = weakref.ref(self.win)

        # Setup pipeline
        screen_w, screen_h = self._screen_size()
        self.pipeline = Pipeline(
            camera_index=self.settings.camera_index(),
            screen_size=(screen_w, screen_h),
            alpha=self.settings.smoothing_alpha(),
            drift_enabled=self.settings.drift_enabled(),
            drift_lr=self.settings.drift_learn_rate(),
        )
        self.tracking = False
        self._calibration_ui: Optional[CalibrationUI] = None
        self._calibration_samples_true: list[tuple[int, int]] = []
        self._calibration_samples_pred: list[tuple[int, int]] = []
        self._calibration_features: list[tuple[float, float]] = []
        self._settings_dialog_open = False
        self._cam_settings_wnd = None
        self._cam_controller = CameraController(
            get_cap=lambda: getattr(self.pipeline.cam, "cap", None),
            restart_callback=self._restart_camera,
            settings=self.settings,
        )

        # Attempt to load an existing calibration model
        try:
            calib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "calibration_state.json")
            if os.path.exists(calib_path):
                from MonocularTracker.tracking.calibration import Calibrator
                loaded = Calibrator.load(calib_path)
                # Replace mapping calibrator with the loaded one
                self.pipeline.map.calib = loaded
        except Exception:
            pass

    def _screen_size(self) -> Tuple[int, int]:
        try:
            if pyautogui:
                w, h = pyautogui.size()
                return int(w), int(h)
        except Exception:
            pass
        return (1920, 1080)

    # Panic -------------------------------------------------------------
    def _install_panic_shortcuts(self, host) -> None:
        try:
            from PyQt6.QtGui import QKeySequence
            from PyQt6.QtWidgets import QShortcut
            from PyQt6.QtCore import Qt
        except Exception:
            return
        for key in (QKeySequence(Qt.Key.Key_Space), QKeySequence(Qt.Key.Key_Escape)):
            sc = QShortcut(key, host)
            try:
                sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            except Exception:
                pass
            sc.activated.connect(self.trigger_panic)  # type: ignore[attr-defined]

    def trigger_panic(self) -> None:
        # Stop movement immediately
        self.tracking = False
        try:
            self.timer.stop()
        except Exception:
            pass
        try:
            self.pipeline.stop()
        except Exception:
            pass
        if self._panic_overlay is not None:
            try:
                self._panic_overlay.close()
            except Exception:
                pass
            self._panic_overlay = None
        try:
            QMessageBox.information(self.win, "Safety", "Tracking stopped for safety. Cursor control disabled.")
        except Exception:
            pass
        # Re-enable start button
        self.win.toggle_controls(tracking=False)

    # Tracking ----------------------------------------------------------
    def start_tracking(self) -> None:
        if self.tracking:
            return
        # Safety confirmation
        try:
            if QMessageBox.question(self.win, "Safety", "Start cursor control now?", QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Ok:
                return
        except Exception:
            pass
        self.tracking = True
        self.pipeline.start()
        self.win.toggle_controls(tracking=True)
        # Show panic overlay
        try:
            self._panic_overlay = PanicOverlay()
            self._panic_overlay.show()
        except Exception:
            self._panic_overlay = None
        self.timer.start()

    def stop_tracking(self) -> None:
        self.trigger_panic()

    # Camera settings ---------------------------------------------------
    def _restart_camera(self) -> None:
        was_running = bool(self.pipeline.running)
        try:
            self.pipeline.stop()
        except Exception:
            pass
        # Apply new desired parameters
        try:
            w, h = self.settings.camera_resolution()
            fps = self.settings.camera_fps()
            self.pipeline.cam.width = int(w)
            self.pipeline.cam.height = int(h)
            self.pipeline.cam.set_fps(int(fps))
        except Exception:
            pass
        if was_running:
            try:
                self.pipeline.start()
            except Exception:
                pass

    def open_camera_settings(self) -> None:
        if CameraSettingsWindow is None:
            try:
                QMessageBox.information(self.win, "Camera Settings", "Camera settings UI is unavailable.")
            except Exception:
                pass
            return
        # Disable cursor movement while open
        self._settings_dialog_open = True
        try:
            self._cam_settings_wnd = CameraSettingsWindow(self._cam_controller, self.settings)
            self._cam_settings_wnd.closed.connect(self._on_cam_settings_closed)  # type: ignore[attr-defined]
            self._cam_settings_wnd.show()
        except Exception:
            self._cam_settings_wnd = None

    def _on_cam_settings_closed(self) -> None:
        self._settings_dialog_open = False
        self._cam_settings_wnd = None

    # Calibration -------------------------------------------------------
    def start_calibration(self, points: int) -> None:
        if self.tracking:
            # stop tracking while calibrating
            self.stop_tracking()
        self.pipeline.map.set_calibrating(True)
        self.pipeline.map.calib.reset()
        self._calibration_samples_true.clear()
        self._calibration_samples_pred.clear()
        self._calibration_features.clear()
        self._calibration_ui = CalibrationUI(points_count=points, samples_per_point=25, dwell_ms=1500)
        self._calibration_ui.sampleRequested.connect(self._on_calib_sample)  # type: ignore[attr-defined]
        self._calibration_ui.calibrationFinished.connect(self._on_calib_finished)  # type: ignore[attr-defined]
        self._calibration_ui.start()

    def _on_calib_sample(self, target_xy):  # type: ignore[override]
        # Grab current frame features to sample gaze
        res = self.pipeline.process()
        if res.features is None:
            return
        f = (res.features.nx, res.features.ny)
        self.pipeline.map.add_calibration_sample(f, target_xy)
        self._calibration_samples_true.append(target_xy)
        self._calibration_features.append(f)
        # Predict immediately (before training) for plot reference; will be refined after training
        pred = self.pipeline.map.predict(f)
        self._calibration_samples_pred.append(pred)

    def _on_calib_finished(self):  # type: ignore[override]
        # Train model
        self.pipeline.map.train()
        # Save trained calibration to JSON
        try:
            calib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "calibration_state.json")
            self.pipeline.map.calib.save(calib_path)
        except Exception:
            pass
        # Replace predicted points with final model predictions for accuracy
        final_preds: list[tuple[int, int]] = [self.pipeline.map.predict(f) for f in self._calibration_features]
        # Show plots window
        screen_w, screen_h = self._screen_size()
        plots = CalibrationPlotsWindow((screen_w, screen_h), self._calibration_samples_true, final_preds, threshold_px=150.0)
        plots.accepted.connect(lambda: self._on_calib_accept(plots))  # type: ignore[attr-defined]
        plots.retry.connect(lambda: self._on_calib_retry(plots))  # type: ignore[attr-defined]
        plots.show()
        # End calibration mode
        self.pipeline.map.set_calibrating(False)

    # Apply basic camera settings from the Camera Settings tab in main window
    def _apply_basic_camera_tab(self) -> None:
        try:
            # Resolution
            res_txt = self.win.cmb_res.currentText().strip()
            w_s, h_s = res_txt.split("x")
            w, h = int(w_s), int(h_s)
            self._cam_controller.set_resolution(w, h)
            # FPS
            fps = int(self.win.cmb_fps.currentText().strip())
            self._cam_controller.set_fps(fps)
            # Restart camera to apply
            self._cam_controller.apply_resolution_fps()
        except Exception:
            try:
                QMessageBox.information(self.win, "Camera", "Failed to apply basic camera settings.")
            except Exception:
                pass

    def _on_calib_accept(self, wnd):
        try:
            wnd.close()
        except Exception:
            pass
        # Ready to start tracking again if user chooses
        self.win.toggle_controls(tracking=False)

    def _on_calib_retry(self, wnd):
        try:
            wnd.close()
        except Exception:
            pass
        # Restart calibration with same point count
        if self._calibration_ui is not None:
            pts = getattr(self._calibration_ui, "_requested_points", 5)
            self.start_calibration(points=pts)

    def _on_tick(self) -> None:
        # Process a frame
        res = self.pipeline.process()
        self.fps.tick()

        # Update UI
        if res.frame is not None:
            self.win.update_video(frame=res.frame, landmarks=(res.features.landmarks if res.features else None), iris=(res.features.iris_center if res.features else None), box=(res.features.eyelid_box if res.features else None), predicted=res.predicted_xy)
        conf = 1.0 if (res.features is not None) else 0.0
        self.win.update_status(face_ok=res.face_ok, eye_ok=res.eye_ok, conf=conf, fps=self.fps.fps())

        # Move cursor if available and tracking
        if (not self._settings_dialog_open) and self.tracking and res.predicted_xy is not None:
            x, y = res.predicted_xy
            try:
                self.cursor.move_cursor(x, y)
            except Exception:
                pass

        # Update camera settings diagnostics FPS label if window open
        try:
            if self._cam_settings_wnd is not None:
                fps_val = self.fps.fps()
                self._cam_settings_wnd.lbl_current_fps.setText(f"Current FPS: {fps_val:.1f}")
        except Exception:
            pass


def main() -> int:
    if QApplication is None:
        print("PyQt6 is not installed. Please install dependencies.")
        return 1
    app = QApplication(sys.argv)
    core = AppCore()
    core.win.show()
    code = app.exec()
    try:
        core.pipeline.stop()
        if cv2 is not None:
            cv2.destroyAllWindows()
    except Exception:
        pass
    return int(code)
