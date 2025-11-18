from __future__ import annotations

import os
import time
from collections import deque
from typing import Optional, Tuple

import cv2
import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QKeySequence
from PyQt5.QtWidgets import QShortcut

from MonocularEyeAssist.core.settings import Settings
from MonocularEyeAssist.ui.main_window import MainWindow
from MonocularEyeAssist.ui.calibration_ui import CalibrationUI
from MonocularEyeAssist.ui.panic_overlay import PanicOverlay
from MonocularEyeAssist.ui.plots import show_calibration_plots
from MonocularEyeAssist.tracking.camera import Camera
from MonocularEyeAssist.tracking.gaze_right import RightEyeTracker
from MonocularEyeAssist.core.calibration import Calibrator
from MonocularEyeAssist.core.smoothing import EMA2D, TrendPredictor
from MonocularEyeAssist.control.cursor import Cursor


class AppCore:
    def __init__(self) -> None:
        self.settings = Settings()
        self.win = MainWindow()
        self._connect_signals()
        self._panic_overlay: Optional[PanicOverlay] = None

        self._screen = self._screen_size()
        self.cam = Camera(index=self.settings.camera_index(), width=self.settings.camera_resolution()[0], height=self.settings.camera_resolution()[1], fps=self.settings.camera_fps())
        self.right = RightEyeTracker()
        self.calib = Calibrator(screen_size=self._screen, degree=self.settings.calib_degree())
        self.ema = EMA2D(alpha=self.settings.smoothing_alpha())
        self.predict = TrendPredictor(window=8, lookahead=0.2)
        self.cursor = Cursor()
        self.tracking = False
        self.show_landmarks = True

        self.timer = QTimer()
        self.timer.setInterval(16)  # ~60 fps
        self.timer.timeout.connect(self._on_tick)

        # Try to open camera for preview
        try:
            self.cam.open()
            self.timer.start()
        except Exception:
            pass

        # Load previous calibration if available
        try:
            prof_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "profiles")
            path = os.path.join(prof_dir, f"{self.settings.data.get('calibration',{}).get('profile','default')}.json")
            from MonocularEyeAssist.core.calibration import Calibrator
            loaded = Calibrator.load(path)
            if loaded is not None:
                self.calib.model = loaded
        except Exception:
            pass

        # Panic hotkey (Ctrl+Shift+Q)
        try:
            sc = QShortcut(QKeySequence("Ctrl+Shift+Q"), self.win)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(self._panic)
        except Exception:
            pass

    def shutdown(self) -> None:
        try:
            if self.cam:
                self.cam.close()
        except Exception:
            pass

    def _connect_signals(self) -> None:
        self.win.startRequested.connect(self._start)
        self.win.stopRequested.connect(self._stop)
        self.win.calibrateRequested.connect(self._start_calibration)
        self.win.scanCamerasRequested.connect(self._scan_cameras)
        self.win.useSelectedCameraRequested.connect(self._use_camera)
        self.win.panicRequested.connect(self._panic)
        self.win.smoothingChanged.connect(self._set_smoothing)
        self.win.resolutionChanged.connect(self._set_resolution)
        self.win.brightnessChanged.connect(self._set_brightness)
        self.win.exposureChanged.connect(self._set_exposure)
        self.win.mirrorToggled.connect(self._set_mirror)
        self.win.landmarksToggled.connect(self._set_landmarks)

    def _screen_size(self) -> Tuple[int, int]:
        try:
            import pyautogui  # type: ignore
            w, h = pyautogui.size()
            return int(w), int(h)
        except Exception:
            return (1920, 1080)

    # Control ----------------------------------------------------------
    def _start(self):
        self.tracking = True
        self.win.toggle_controls(True)
        try:
            if not self.timer.isActive():
                self.timer.start()
        except Exception:
            pass

    def _stop(self):
        self.tracking = False
        self.win.toggle_controls(False)
        if self._panic_overlay:
            try:
                self._panic_overlay.close()
            except Exception:
                pass
            self._panic_overlay = None

    def _panic(self):
        self.tracking = False
        self.win.toggle_controls(False)
        try:
            if not self.timer.isActive():
                self.timer.start()
        except Exception:
            pass
        self._panic_overlay = PanicOverlay()
        self._panic_overlay.show()

    # Camera settings --------------------------------------------------
    def _scan_cameras(self):
        self.win.cmb_cameras.clear()
        for i in range(0, 11):
            cap = None
            try:
                cap = cv2.VideoCapture(i)
                if cap and cap.isOpened():
                    self.win.cmb_cameras.addItem(f"Camera {i}", userData=i)
            finally:
                if cap is not None:
                    cap.release()

    def _use_camera(self):
        data = self.win.cmb_cameras.currentData()
        if data is None:
            QMessageBox.information(self.win, "Camera", "Select a valid camera.")
            return
        idx = int(data)
        self.settings.set_camera_index(idx)
        self.settings.save()
        try:
            self.cam.close()
        except Exception:
            pass
        self.cam = Camera(index=idx, width=self.settings.camera_resolution()[0], height=self.settings.camera_resolution()[1], fps=self.settings.camera_fps())
        self.cam.open()

    def _set_resolution(self, txt: str):
        try:
            w, h = txt.split("x")
            w, h = int(w), int(h)
        except Exception:
            return
        self.settings.data.setdefault("camera", {})["resolution"] = [w, h]
        self.settings.save()
        try:
            self.cam.close()
        except Exception:
            pass
        self.cam = Camera(index=self.settings.camera_index(), width=w, height=h, fps=self.settings.camera_fps())
        self.cam.open()

    def _set_brightness(self, v: float):
        self.settings.data.setdefault("camera", {})["brightness"] = float(v)
        self.settings.save()
        try:
            self.cam.set_brightness(v)
        except Exception:
            pass

    def _set_exposure(self, v: float):
        self.settings.data.setdefault("camera", {})["exposure"] = float(v)
        self.settings.save()
        try:
            self.cam.set_exposure(v)
        except Exception:
            pass

    def _set_mirror(self, on: bool):
        self.settings.set_mirror(bool(on))
        self.settings.save()

    def _set_landmarks(self, on: bool):
        self.show_landmarks = bool(on)

    def _set_smoothing(self, a: float):
        self.settings.set_smoothing_alpha(a)
        self.settings.save()
        self.ema = EMA2D(alpha=a)

    # Calibration ------------------------------------------------------
    def _start_calibration(self, points: int):
        self.tracking = False
        self.ema.reset(); self.predict.reset()
        cal = CalibrationUI(self._screen, points=points, dwell_ms=2500, radius=60)
        cal.sampleRequested.connect(self._calib_sample)
        cal.finished.connect(self._calib_finish)
        self._calib_ui = cal
        self._calib_targets: list[tuple[int, int]] = []
        # Flattened filtered features for training
        self._calib_feats: list[tuple[float, float]] = []
        # Raw per-point samples (list per target)
        self._calib_raw_samples: list[list[tuple[float, float]]] = []
        self._calib_filtered_per_point: list[list[tuple[float, float]]] = []
        self._calib_point_errors: list[float] = []
        self._calib_point_conf: list[float] = []
        cal.show()

    def _calib_sample(self, target_xy):  # type: ignore[override]
        # Collect raw samples (50–100 typical) during dwell for this point
        try:
            start = time.time()
            raw: list[tuple[float, float]] = []
            while (time.time() - start) < 2.0:  # 2 seconds active sampling
                frame = self.cam.read()
                if frame is None:
                    continue
                f = self.right.process(frame, mirror=self.settings.mirror())
                if f is None:
                    continue
                raw.append((f.nx, f.ny))
            if not raw:
                return
            # Outlier filtering (>2 std dev from mean center)
            xs = np.array([p[0] for p in raw], dtype=np.float32)
            ys = np.array([p[1] for p in raw], dtype=np.float32)
            cx = float(xs.mean()); cy = float(ys.mean())
            dx = xs - cx; dy = ys - cy
            dist = np.sqrt(dx * dx + dy * dy)
            sd = float(dist.std())
            if sd <= 1e-6:
                mask = np.ones_like(dist, dtype=bool)
            else:
                mask = dist <= (2.0 * sd)
            filtered = [(float(xs[i]), float(ys[i])) for i in range(len(raw)) if bool(mask[i])]
            if len(filtered) < 8:  # fallback if over-filtered
                filtered = raw
            self._calib_raw_samples.append(raw)
            self._calib_filtered_per_point.append(filtered)
            # For training later we just record target now
            self._calib_targets.append(tuple(target_xy))
        except Exception:
            pass

    def _calib_finish(self):  # type: ignore[override]
        self.calib.reset()
        # Flatten all filtered samples for training with replicated targets
        flat_feats: list[tuple[float, float]] = []
        flat_targets: list[tuple[int, int]] = []
        for idx, filtered in enumerate(self._calib_filtered_per_point):
            tgt = self._calib_targets[idx]
            for (nx, ny) in filtered:
                flat_feats.append((nx, ny))
                flat_targets.append(tgt)
        for (f, t) in zip(flat_feats, flat_targets):
            self.calib.add_sample(f[0], f[1], t)
        self.calib.train()
        # Save profile
        prof_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "profiles")
        os.makedirs(prof_dir, exist_ok=True)
        path = os.path.join(prof_dir, f"{self.settings.data.get('calibration',{}).get('profile','default')}.json")
        self.calib.save(path)
        # Compute per-point confidence & errors
        try:
            self._calib_point_errors.clear(); self._calib_point_conf.clear()
            diag = (self._screen[0] ** 2 + self._screen[1] ** 2) ** 0.5
            threshold = 0.05 * diag  # 5% diagonal baseline
            for idx, filtered in enumerate(self._calib_filtered_per_point):
                tgt = self._calib_targets[idx]
                errs = []
                for (nx, ny) in filtered:
                    px, py = self.calib.predict(nx, ny)
                    err = ((px - tgt[0]) ** 2 + (py - tgt[1]) ** 2) ** 0.5
                    errs.append(err)
                mean_err = float(np.mean(errs)) if errs else float('inf')
                self._calib_point_errors.append(mean_err)
                conf = max(0.0, 1.0 - (mean_err / threshold))
                self._calib_point_conf.append(conf)
            overall = float(np.mean(self._calib_point_errors)) if self._calib_point_errors else float('inf')
        except Exception:
            overall = float('inf')
        # Show scatter of filtered samples colored by point index
        try:
            from MonocularEyeAssist.ui.calibration_results import CalibrationResultsWindow
            wnd = CalibrationResultsWindow(
                screen=self._screen,
                targets=self._calib_targets,
                samples=self._calib_filtered_per_point,
                point_errors=self._calib_point_errors,
                point_conf=self._calib_point_conf,
                overall_error=overall,
            )
            wnd.show()
        except Exception:
            pass
        QMessageBox.information(self.win, "Calibration", "Calibration complete.")

    # Tick -------------------------------------------------------------
    def _on_tick(self):
        frame = self.cam.read()
        if frame is None:
            return
        feat = self.right.process(frame, mirror=self.settings.mirror())
        face_ok = feat is not None
        eye_ok = feat is not None
        conf = 1.0 if feat is not None else 0.0
        fps = 0.0  # lightweight UI; omit fps calc to keep simple
        self.win.update_status(face_ok=face_ok, eye_ok=eye_ok, conf=conf, fps=fps)

        # Draw preview with landmarks (optional)
        try:
            vis = frame.copy()
            if self.show_landmarks and feat is not None:
                (x1, y1, x2, y2) = feat.eyelid_box
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 1)
                cx, cy = feat.iris_center
                cv2.circle(vis, (int(cx), int(cy)), 2, (0, 255, 255), -1)
                if feat.landmarks:
                    for (lx, ly) in feat.landmarks:
                        cv2.circle(vis, (int(lx), int(ly)), 1, (255, 0, 0), -1)
            vis_small = cv2.resize(vis, (640, 360))
            rgb = cv2.cvtColor(vis_small, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.win.video.setPixmap(QPixmap.fromImage(qimg))
        except Exception:
            pass

        if not self.tracking or feat is None:
            return

        # Predict cursor
        nx, ny = feat.nx, feat.ny
        x, y = self.calib.predict(nx, ny) if self.calib.model is not None else (0, 0)
        sx, sy = self.ema.update(x, y)
        px, py = self.predict.update(sx, sy)
        self.cursor.move_to(int(px), int(py))
