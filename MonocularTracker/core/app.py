from __future__ import annotations

from typing import Optional, Tuple
from collections import deque

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
        # Signal thresholds/window from settings
        x_ok, x_strong, y_ok, y_strong = self.settings.signal_thresholds()
        self._sig_thr_x_ok = float(x_ok)
        self._sig_thr_x_strong = float(x_strong)
        self._sig_thr_y_ok = float(y_ok)
        self._sig_thr_y_strong = float(y_strong)
        # Recent feature history for live signal indicator
        self._sig_hist = deque(maxlen=max(30, int(self.settings.signal_window())))

        self.win = MainWindow()
        self.win.startRequested.connect(self.start_tracking)  # type: ignore[attr-defined]
        self.win.stopRequested.connect(self.stop_tracking)  # type: ignore[attr-defined]
        self.win.calibrate5Requested.connect(lambda: self.start_calibration(points=5))  # type: ignore[attr-defined]
        self.win.calibrate9Requested.connect(lambda: self.start_calibration(points=9))  # type: ignore[attr-defined]
        # Camera selection from main UI
        try:
            self.win.scanCamerasRequested.connect(self._scan_cameras_main)  # type: ignore[attr-defined]
            self.win.useSelectedCameraRequested.connect(self._use_selected_camera_main)  # type: ignore[attr-defined]
        except Exception:
            pass
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
        # Eye mode change signal
        try:
            if hasattr(self.win, "eyeModeChanged"):
                self.win.eyeModeChanged.connect(self._on_eye_mode_changed)  # type: ignore[attr-defined]
        except Exception:
            pass
        # Signal config live-tuning
        try:
            if hasattr(self.win, "signalConfigChanged"):
                self.win.signalConfigChanged.connect(self._on_signal_config_changed)  # type: ignore[attr-defined]
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
              eye_mode=self.settings.eye_mode(),
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
            change_index_callback=self._on_camera_index_changed,
        )
        # Apply thresholds to signal bars if present
        try:
            if getattr(self.win, "signal_bars", None) is not None:
                self.win.signal_bars.set_thresholds(
                    self._sig_thr_x_ok, self._sig_thr_x_strong, self._sig_thr_y_ok, self._sig_thr_y_strong
                )
            # Initialize UI spinboxes if present
            if hasattr(self.win, "set_signal_config"):
                self.win.set_signal_config(
                    self._sig_thr_x_ok,
                    self._sig_thr_x_strong,
                    self._sig_thr_y_ok,
                    self._sig_thr_y_strong,
                    int(self._sig_hist.maxlen or 90),
                )
        except Exception:
            pass
            # Apply saved eye mode to UI if available
            try:
                mode = self.settings.eye_mode()
                if hasattr(self.win, "cmb_eye"):
                    idx_map = {"auto": 0, "right": 1, "left": 2}
                    self.win.cmb_eye.setCurrentIndex(idx_map.get(mode, 0))  # type: ignore[attr-defined]
            except Exception:
                pass

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

        # Start a safe, cursor-disabled camera preview immediately
        # so the left panel isn’t blank before tracking begins.
        try:
            self.pipeline.start()
            self.timer.start()
        except Exception:
            # If preview cannot start (e.g., no camera), keep UI responsive.
            # The user can still select a camera and retry later.
            pass

    def _screen_size(self) -> Tuple[int, int]:
        try:
            if pyautogui:
                w, h = pyautogui.size()
                return int(w), int(h)
        except Exception:
            pass
        return (1920, 1080)

    def _on_eye_mode_changed(self, mode: str) -> None:
        # Persist selection and update live parser
        try:
            self.settings.set_eye_mode(mode)
            self.settings.save()
        except Exception:
            pass
        try:
            if hasattr(self.pipeline, "parser") and self.pipeline.parser is not None:
                self.pipeline.parser.set_mode(mode)
        except Exception:
            pass

    def _on_signal_config_changed(self, x_ok: float, x_strong: float, y_ok: float, y_strong: float, window: int) -> None:
        # Update in-memory thresholds
        self._sig_thr_x_ok = float(x_ok)
        self._sig_thr_x_strong = float(x_strong)
        self._sig_thr_y_ok = float(y_ok)
        self._sig_thr_y_strong = float(y_strong)
        # Update deque window size (preserve recent values)
        try:
            win = max(30, int(window))
            old = list(self._sig_hist)
            self._sig_hist = deque(old[-win:], maxlen=win)
        except Exception:
            pass
        # Persist to settings
        try:
            s = self.settings.data.setdefault("signal", {})
            s.setdefault("ok", {})["rx"] = float(x_ok)
            s.setdefault("ok", {})["ry"] = float(y_ok)
            s.setdefault("strong", {})["rx"] = float(x_strong)
            s.setdefault("strong", {})["ry"] = float(y_strong)
            s["window"] = int(window)
            self.settings.save()
        except Exception:
            pass
        # Update bars
        try:
            if getattr(self.win, "signal_bars", None) is not None:
                self.win.signal_bars.set_thresholds(
                    self._sig_thr_x_ok, self._sig_thr_x_strong, self._sig_thr_y_ok, self._sig_thr_y_strong
                )
        except Exception:
            pass

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
        # Stop movement immediately, but keep preview running.
        self.tracking = False
        # Ensure preview remains active
        try:
            if not bool(self.pipeline.running):
                self.pipeline.start()
        except Exception:
            pass
        try:
            if self.timer is not None and not bool(self.timer.isActive()):
                self.timer.start()
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
        # Try to start camera/pipeline
        try:
            if not bool(self.pipeline.running):
                self.pipeline.start()
        except Exception as e:
            # Show a helpful message and abort start
            try:
                QMessageBox.warning(self.win, "Camera", f"Failed to start camera.\n{e}")
            except Exception:
                print(f"Failed to start camera: {e}")
            self.tracking = False
            self.win.toggle_controls(tracking=False)
            return
        self.tracking = True
        self.win.toggle_controls(tracking=True)
        # Show panic overlay
        try:
            self._panic_overlay = PanicOverlay()
            self._panic_overlay.show()
        except Exception:
            self._panic_overlay = None
        # Ensure periodic processing is running
        try:
            if not bool(self.timer.isActive()):
                self.timer.start()
        except Exception:
            pass
            # Eye mode change
            try:
                if hasattr(self.win, "eyeModeChanged"):
                    self.win.eyeModeChanged.connect(self._on_eye_mode_changed)  # type: ignore[attr-defined]
            except Exception:
                pass

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

    def _on_camera_index_changed(self, idx: int) -> None:
        # Update active camera index and restart to apply
        try:
            self.pipeline.cam.index = int(idx)
        except Exception:
            pass
        # Persist is handled by SettingsManager via controller
        self._restart_camera()

    # Camera scanning support for main UI -----------------------------
    def _scan_cameras_main(self) -> None:
        try:
            import cv2  # type: ignore
        except Exception:
            try:
                QMessageBox.information(self.win, "Camera", "OpenCV is not available.")
            except Exception:
                pass
            return
        # Update UI state
        try:
            self.win.btn_scan_cam.setEnabled(False)
            self.win.btn_use_cam.setEnabled(False)
            self.win.cmb_cameras.clear()
        except Exception:
            pass
        indices = []
        seen = set()
        backends = [
            ("MSMF", getattr(cv2, "CAP_MSMF", None)),
            ("DShow", getattr(cv2, "CAP_DSHOW", None)),
            ("Any", getattr(cv2, "CAP_ANY", None)),
        ]
        backends = [(n, b) for (n, b) in backends if b is not None]
        for i in range(0, 11):
            for (be_name, be) in backends:
                try:
                    cap = cv2.VideoCapture(i, be)
                    ok = bool(cap is not None and cap.isOpened())
                    if ok and i not in seen:
                        # Try to read some diagnostics
                        try:
                            aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            fps = cap.get(cv2.CAP_PROP_FPS)
                            fps_txt = f"{fps:.0f}" if isinstance(fps, (int, float)) and fps > 0 else "?"
                            label = f"Camera {i} — {aw}x{ah} @ {fps_txt} [{be_name}]"
                        except Exception:
                            label = f"Camera {i} [{be_name}]"
                        self.win.cmb_cameras.addItem(label, userData=i)
                        indices.append(i)
                        seen.add(i)
                        break
                finally:
                    try:
                        if cap is not None:
                            cap.release()
                    except Exception:
                        pass
        # Populate combo
        try:
            if not indices:
                self.win.cmb_cameras.addItem("No cameras found")
                self.win.btn_use_cam.setEnabled(False)
            else:
                for i in indices:
                    self.win.cmb_cameras.addItem(f"Camera {i}", userData=i)
                cur = self.settings.camera_index()
                idx = self.win.cmb_cameras.findData(cur)
                if idx >= 0:
                    self.win.cmb_cameras.setCurrentIndex(idx)
                self.win.btn_use_cam.setEnabled(True)
        finally:
            try:
                self.win.btn_scan_cam.setEnabled(True)
            except Exception:
                pass

    def _use_selected_camera_main(self) -> None:
        try:
            data = self.win.cmb_cameras.currentData()
        except Exception:
            data = None
        if data is None or isinstance(data, str):
            try:
                QMessageBox.information(self.win, "Camera", "Select a valid camera first.")
            except Exception:
                pass
            return
        new_idx = int(data)
        try:
            self._cam_controller.set_camera_index(new_idx)
            # Persist and restart handled by callback + restart
            try:
                self.settings.set_camera_index(new_idx)
                self.settings.save()
            except Exception:
                pass
        except Exception as e:
            try:
                QMessageBox.warning(self.win, "Camera", f"Failed to switch camera.\n{e}")
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
        # Pause cursor movement during calibration but keep camera running
        if self.tracking:
            self.tracking = False
            try:
                self.timer.stop()
            except Exception:
                pass
            # Close panic overlay if visible
            if self._panic_overlay is not None:
                try:
                    self._panic_overlay.close()
                except Exception:
                    pass
                self._panic_overlay = None
            # Keep pipeline running so we can capture frames for calibration
        # Ensure camera/pipeline is running for calibration sampling
        if not bool(self.pipeline.running):
            try:
                self.pipeline.start()
            except Exception as e:
                try:
                    QMessageBox.warning(self.win, "Camera", f"Cannot start camera for calibration.\n{e}")
                except Exception:
                    print(f"Cannot start camera for calibration: {e}")
                return
        self.pipeline.map.set_calibrating(True)
        # Apply robust settings from UI, if available
        try:
            robust_on = bool(getattr(self.win, "chk_robust").isChecked())
            pct = float(getattr(self.win, "spn_outlier_pct").value()) if hasattr(self.win, "spn_outlier_pct") else 15.0
            self.pipeline.map.calib.configure_robust(robust_on, drop_percent=pct)
        except Exception:
            try:
                self.pipeline.map.calib.configure_robust(True, drop_percent=15.0)
            except Exception:
                pass
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
        feats = self._calibration_features
        trues = self._calibration_samples_true
        # If calibrator performed outlier filtering, evaluate on inliers only
        try:
            mask = getattr(self.pipeline.map.calib, "last_inlier_mask", None)
            if mask is not None and len(mask) == len(feats):
                feats = [f for f, m in zip(feats, mask) if m]
                trues = [t for t, m in zip(trues, mask) if m]
        except Exception:
            pass
        final_preds: list[tuple[int, int]] = [self.pipeline.map.predict(f) for f in feats]
        # Show plots window with adaptive threshold (~8% of diagonal)
        screen_w, screen_h = self._screen_size()
        try:
            import math
            diag = math.hypot(float(screen_w), float(screen_h))
            thr = max(100.0, min(0.08 * diag, 260.0))
        except Exception:
            thr = 150.0
        plots = CalibrationPlotsWindow((screen_w, screen_h), trues, final_preds, threshold_px=float(thr))
        # If inlier filtering happened, hint it in the title
        try:
            total = len(self._calibration_features)
            kept = len(feats)
            if kept != total:
                plots.setWindowTitle(f"Calibration Analysis — kept {kept}/{total} samples")
        except Exception:
            pass
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

        # Live signal indicator from recent (nx, ny)
        try:
            if res.features is not None:
                self._sig_hist.append((float(res.features.nx), float(res.features.ny)))
            if len(self._sig_hist) >= 30:
                xs = [p[0] for p in self._sig_hist]
                ys = [p[1] for p in self._sig_hist]
                rx = max(xs) - min(xs)
                ry = max(ys) - min(ys)
                # Thresholds from settings (normalized units)
                if rx >= self._sig_thr_x_strong and ry >= self._sig_thr_y_strong:
                    q = "Strong"
                elif rx >= self._sig_thr_x_ok and ry >= self._sig_thr_y_ok:
                    q = "OK"
                else:
                    q = "Weak"
                self.win.update_signal(rx=rx, ry=ry, quality=q)
        except Exception:
            pass

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
