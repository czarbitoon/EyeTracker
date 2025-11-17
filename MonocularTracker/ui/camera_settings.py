from __future__ import annotations

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QWidget,
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QComboBox,
        QPushButton,
        QCheckBox,
        QSlider,
        QTabWidget,
        QFormLayout,
        QMessageBox,
    )
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore
    QDialog = object  # type: ignore
    pyqtSignal = lambda *a, **k: None  # type: ignore

from MonocularTracker.tracking.camera_controller import CameraController
from MonocularTracker.core.settings import SettingsManager

class CameraSettingsWindow(QDialog):  # type: ignore[misc]
    restartRequested = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, controller: CameraController, settings: SettingsManager):  # type: ignore[no-redef]
        super().__init__()
        self.setWindowTitle("Camera Settings")
        self.controller = controller
        self.settings = settings
        self._build_ui()
        self._load_settings_into_ui()

    # UI construction --------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tab_resolution_fps(), "Resolution & FPS")
        self.tabs.addTab(self._build_tab_exposure(), "Exposure & Lighting")
        self.tabs.addTab(self._build_tab_focus(), "Focus")
        self.tabs.addTab(self._build_tab_diagnostics(), "Diagnostics")
        root.addWidget(self.tabs)
        btn_row = QHBoxLayout()
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self._on_close)  # type: ignore[attr-defined]
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_close)
        root.addLayout(btn_row)
        self.setLayout(root)

    def _build_tab_resolution_fps(self):
        w = QWidget()
        v = QVBoxLayout()
        self.cmb_resolution = QComboBox()
        self.cmb_fps = QComboBox()
        self.btn_apply_res = QPushButton("Apply")
        v.addWidget(QLabel("Resolution preset"))
        v.addWidget(self.cmb_resolution)
        v.addWidget(QLabel("FPS"))
        v.addWidget(self.cmb_fps)
        v.addWidget(self.btn_apply_res)
        self.btn_apply_res.clicked.connect(self._apply_resolution_fps)  # type: ignore[attr-defined]
        w.setLayout(v)
        return w

    def _build_tab_exposure(self):
        w = QWidget()
        form = QFormLayout()
        self.chk_auto_exposure = QCheckBox("Auto exposure")
        self.sld_exposure = QSlider(Qt.Orientation.Horizontal)
        self.sld_exposure.setRange(-13, 0)  # typical webcam manual exposure range
        self.sld_gain = QSlider(Qt.Orientation.Horizontal)
        self.sld_gain.setRange(0, 100)
        self.sld_brightness = QSlider(Qt.Orientation.Horizontal)
        self.sld_brightness.setRange(0, 255)
        self.sld_contrast = QSlider(Qt.Orientation.Horizontal)
        self.sld_contrast.setRange(0, 255)
        self.chk_auto_wb = QCheckBox("Auto white balance")
        self.sld_wb_temp = QSlider(Qt.Orientation.Horizontal)
        self.sld_wb_temp.setRange(2500, 7500)
        form.addRow(self.chk_auto_exposure)
        form.addRow("Exposure", self.sld_exposure)
        form.addRow("Gain", self.sld_gain)
        form.addRow("Brightness", self.sld_brightness)
        form.addRow("Contrast", self.sld_contrast)
        form.addRow(self.chk_auto_wb)
        form.addRow("WB Temperature", self.sld_wb_temp)
        # Signals
        self.chk_auto_exposure.stateChanged.connect(lambda _: self._apply_auto_exposure())  # type: ignore[attr-defined]
        self.sld_exposure.valueChanged.connect(lambda _: self._apply_exposure())  # type: ignore[attr-defined]
        self.sld_gain.valueChanged.connect(lambda _: self._apply_gain())  # type: ignore[attr-defined]
        self.sld_brightness.valueChanged.connect(lambda _: self._apply_brightness())  # type: ignore[attr-defined]
        self.sld_contrast.valueChanged.connect(lambda _: self._apply_contrast())  # type: ignore[attr-defined]
        self.chk_auto_wb.stateChanged.connect(lambda _: self._apply_auto_wb())  # type: ignore[attr-defined]
        self.sld_wb_temp.valueChanged.connect(lambda _: self._apply_wb_temp())  # type: ignore[attr-defined]
        # Enable/disable states based on auto toggles
        self.chk_auto_exposure.stateChanged.connect(lambda _: self._update_enable_states())  # type: ignore[attr-defined]
        self.chk_auto_wb.stateChanged.connect(lambda _: self._update_enable_states())  # type: ignore[attr-defined]
        w.setLayout(form)
        return w

    def _build_tab_focus(self):
        w = QWidget()
        form = QFormLayout()
        self.chk_auto_focus = QCheckBox("Auto focus")
        self.sld_focus = QSlider(Qt.Orientation.Horizontal)
        self.sld_focus.setRange(0, 100)
        form.addRow(self.chk_auto_focus)
        form.addRow("Focus", self.sld_focus)
        self.chk_auto_focus.stateChanged.connect(lambda _: self._apply_auto_focus())  # type: ignore[attr-defined]
        self.sld_focus.valueChanged.connect(lambda _: self._apply_focus())  # type: ignore[attr-defined]
        self.chk_auto_focus.stateChanged.connect(lambda _: self._update_enable_states())  # type: ignore[attr-defined]
        w.setLayout(form)
        return w

    def _build_tab_diagnostics(self):
        w = QWidget()
        v = QVBoxLayout()
        self.lbl_cam_index = QLabel("Camera index: --")
        self.lbl_scan_status = QLabel("")
        # Camera scanning and selection
        self.cmb_cameras = QComboBox()
        self.btn_scan = QPushButton("Scan Cameras")
        self.btn_use_camera = QPushButton("Use Selected Camera")
        self.lbl_current_fps = QLabel("Current FPS: --")
        self.btn_restart = QPushButton("Restart Camera")
        self.btn_save = QPushButton("Save Settings")
        self.btn_load = QPushButton("Load Settings")
        v.addWidget(self.lbl_cam_index)
        v.addWidget(self.lbl_scan_status)
        v.addWidget(self.cmb_cameras)
        row = QHBoxLayout()
        row.addWidget(self.btn_scan)
        row.addWidget(self.btn_use_camera)
        v.addLayout(row)
        v.addWidget(self.lbl_current_fps)
        v.addWidget(self.btn_restart)
        v.addWidget(self.btn_save)
        v.addWidget(self.btn_load)
        self.btn_restart.clicked.connect(self._do_restart)  # type: ignore[attr-defined]
        self.btn_save.clicked.connect(self._do_save)  # type: ignore[attr-defined]
        self.btn_load.clicked.connect(self._do_load)  # type: ignore[attr-defined]
        self.btn_scan.clicked.connect(self._scan_cameras)  # type: ignore[attr-defined]
        self.btn_use_camera.clicked.connect(self._apply_selected_camera)  # type: ignore[attr-defined]
        # Initial disabled state until a scan populates the list
        try:
            self.btn_use_camera.setEnabled(False)
        except Exception:
            pass
        w.setLayout(v)
        return w

    # Load settings into UI ---------------------------------------------
    def _load_settings_into_ui(self) -> None:
        # Resolutions
        supported_res = self.controller.get_supported_resolutions()
        self.cmb_resolution.clear()
        for w, h in supported_res:
            self.cmb_resolution.addItem(f"{w}x{h}")
        # FPS
        supported_fps = self.controller.get_supported_fps()
        self.cmb_fps.clear()
        for f in supported_fps:
            self.cmb_fps.addItem(str(f))
        # Current stored settings
        w0, h0 = self.settings.camera_resolution()
        fps0 = self.settings.camera_fps()
        self._select_combo(self.cmb_resolution, f"{w0}x{h0}")
        self._select_combo(self.cmb_fps, str(fps0))
        self.chk_auto_exposure.setChecked(self.settings.camera_auto_exposure())
        self.sld_exposure.setValue(int(self.settings.camera_exposure()))
        self.sld_gain.setValue(int(self.settings.camera_gain()))
        self.sld_brightness.setValue(int(self.settings.camera_brightness()))
        self.sld_contrast.setValue(int(self.settings.camera_contrast()))
        self.chk_auto_wb.setChecked(self.settings.camera_auto_wb())
        self.sld_wb_temp.setValue(int(self.settings.camera_wb_temperature()))
        self.chk_auto_focus.setChecked(self.settings.camera_auto_focus())
        self.sld_focus.setValue(int(self.settings.camera_focus()))
        self.lbl_cam_index.setText(f"Camera index: {self.settings.camera_index()}")
        self._update_enable_states()

    def _select_combo(self, combo, text: str) -> None:
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    # Apply handlers ----------------------------------------------------
    def _apply_resolution_fps(self) -> None:
        res_txt = self.cmb_resolution.currentText().strip()
        fps_txt = self.cmb_fps.currentText().strip()
        try:
            w_s, h_s = res_txt.split("x")
            w = int(w_s)
            h = int(h_s)
            fps = int(fps_txt)
        except Exception:
            QMessageBox.warning(self, "Invalid", "Resolution/FPS parse failed.")
            return
        self.controller.set_resolution(w, h)
        self.controller.set_fps(fps)
        self.controller.apply_resolution_fps()
        QMessageBox.information(self, "Camera", "Resolution/FPS applied. Camera restarted.")

    def _apply_auto_exposure(self) -> None:
        ok = self.controller.set_auto_exposure(self.chk_auto_exposure.isChecked())
        if not ok:
            self._unsupported_tooltip("Auto exposure not supported.")

    def _apply_exposure(self) -> None:
        if self.chk_auto_exposure.isChecked():
            return
        ok = self.controller.set_exposure(float(self.sld_exposure.value()))
        if not ok:
            self._unsupported_tooltip("Manual exposure not supported.")

    def _apply_gain(self) -> None:
        ok = self.controller.set_gain(float(self.sld_gain.value()))
        if not ok:
            self._unsupported_tooltip("Gain not supported.")

    def _apply_brightness(self) -> None:
        ok = self.controller.set_brightness(float(self.sld_brightness.value()))
        if not ok:
            self._unsupported_tooltip("Brightness not supported.")

    def _apply_contrast(self) -> None:
        ok = self.controller.set_contrast(float(self.sld_contrast.value()))
        if not ok:
            self._unsupported_tooltip("Contrast not supported.")

    def _apply_auto_wb(self) -> None:
        ok = self.controller.set_auto_white_balance(self.chk_auto_wb.isChecked())
        if not ok:
            self._unsupported_tooltip("Auto white balance not supported.")

    def _apply_wb_temp(self) -> None:
        if self.chk_auto_wb.isChecked():
            return
        ok = self.controller.set_white_balance(int(self.sld_wb_temp.value()))
        if not ok:
            self._unsupported_tooltip("Manual white balance not supported.")

    def _apply_auto_focus(self) -> None:
        ok = self.controller.set_auto_focus(self.chk_auto_focus.isChecked())
        if not ok:
            self._unsupported_tooltip("Auto focus not supported.")

    def _apply_focus(self) -> None:
        if self.chk_auto_focus.isChecked():
            return
        ok = self.controller.set_focus(float(self.sld_focus.value()))
        if not ok:
            self._unsupported_tooltip("Manual focus not supported.")

    def _do_restart(self) -> None:
        self.controller.apply_resolution_fps()
        QMessageBox.information(self, "Camera", "Camera restarted.")

    def _do_save(self) -> None:
        self.settings.save()
        QMessageBox.information(self, "Settings", "Saved to settings.json")

    def _do_load(self) -> None:
        self.settings.load()
        self._load_settings_into_ui()
        QMessageBox.information(self, "Settings", "Loaded from settings.json")

    def _unsupported_tooltip(self, text: str) -> None:
        try:
            QMessageBox.information(self, "Unsupported", text)
        except Exception:
            pass

    def _on_close(self) -> None:
        try:
            self.close()
        finally:
            self.closed.emit()  # type: ignore[attr-defined]

    # Enable/disable manual sliders based on auto toggles
    def _update_enable_states(self) -> None:
        try:
            self.sld_exposure.setEnabled(not self.chk_auto_exposure.isChecked())
        except Exception:
            pass
        try:
            self.sld_wb_temp.setEnabled(not self.chk_auto_wb.isChecked())
        except Exception:
            pass
        try:
            self.sld_focus.setEnabled(not self.chk_auto_focus.isChecked())
        except Exception:
            pass

    # Camera enumeration and selection
    def _scan_cameras(self) -> None:
        try:
            import cv2  # type: ignore
        except Exception:
            self._unsupported_tooltip("OpenCV not available.")
            return
        # UI state during scan
        try:
            self.lbl_scan_status.setText("Scanning…")
            self.btn_scan.setEnabled(False)
            self.btn_use_camera.setEnabled(False)
            self.cmb_cameras.clear()
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
                        self.cmb_cameras.addItem(label, userData=i)
                        indices.append(i)
                        seen.add(i)
                        break
                finally:
                    try:
                        if cap is not None:
                            cap.release()
                    except Exception:
                        pass
        try:
            if not indices:
                self.cmb_cameras.addItem("No cameras found")
                self.lbl_scan_status.setText("No cameras found")
                return
            for i in indices:
                self.cmb_cameras.addItem(f"Camera {i}", userData=i)
            # Preselect current
            cur = self.settings.camera_index()
            idx = self.cmb_cameras.findData(cur)
            if idx >= 0:
                self.cmb_cameras.setCurrentIndex(idx)
            self.lbl_scan_status.setText(f"Found {len(indices)} camera(s)")
            self.btn_use_camera.setEnabled(True)
        finally:
            try:
                self.btn_scan.setEnabled(True)
            except Exception:
                pass

    def _apply_selected_camera(self) -> None:
        data = self.cmb_cameras.currentData()
        if data is None or isinstance(data, str):
            self._unsupported_tooltip("Select a valid camera first.")
            return
        new_idx = int(data)
        # Persist and ask controller/app to switch
        try:
            # Use controller to change index so app restarts camera properly
            if hasattr(self.controller, "set_camera_index"):
                self.controller.set_camera_index(new_idx)  # type: ignore[attr-defined]
            else:
                # Fallback: store and ask for restart
                self.settings.set_camera_index(new_idx)
                self.controller.apply_resolution_fps()
            # Persist selection
            try:
                self.settings.set_camera_index(new_idx)
                self.settings.save()
            except Exception:
                pass
        except Exception:
            pass
        self.lbl_cam_index.setText(f"Camera index: {self.settings.camera_index()}")