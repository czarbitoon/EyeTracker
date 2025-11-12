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

    def _build_tab_resolution_fps(self) -> QWidget:
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

    def _build_tab_exposure(self) -> QWidget:
        w = QWidget()
        form = QFormLayout()
        self.chk_auto_exposure = QCheckBox("Auto exposure")
        self.sld_exposure = QSlider(Qt.Orientation.Horizontal)
        self.sld_exposure.setRange(-13, 0)
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
        self.chk_auto_exposure.stateChanged.connect(lambda _: self._apply_auto_exposure())  # type: ignore[attr-defined]
        self.sld_exposure.valueChanged.connect(lambda _: self._apply_exposure())  # type: ignore[attr-defined]
        self.sld_gain.valueChanged.connect(lambda _: self._apply_gain())  # type: ignore[attr-defined]
        self.sld_brightness.valueChanged.connect(lambda _: self._apply_brightness())  # type: ignore[attr-defined]
        self.sld_contrast.valueChanged.connect(lambda _: self._apply_contrast())  # type: ignore[attr-defined]
        self.chk_auto_wb.stateChanged.connect(lambda _: self._apply_auto_wb())  # type: ignore[attr-defined]
        self.sld_wb_temp.valueChanged.connect(lambda _: self._apply_wb_temp())  # type: ignore[attr-defined]
        w.setLayout(form)
        return w

    def _build_tab_focus(self) -> QWidget:
        w = QWidget()
        form = QFormLayout()
        self.chk_auto_focus = QCheckBox("Auto focus")
        self.sld_focus = QSlider(Qt.Orientation.Horizontal)
        self.sld_focus.setRange(0, 100)
        form.addRow(self.chk_auto_focus)
        form.addRow("Focus", self.sld_focus)
        self.chk_auto_focus.stateChanged.connect(lambda _: self._apply_auto_focus())  # type: ignore[attr-defined]
        self.sld_focus.valueChanged.connect(lambda _: self._apply_focus())  # type: ignore[attr-defined]
        w.setLayout(form)
        return w

    def _build_tab_diagnostics(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout()
        self.lbl_cam_index = QLabel("Camera index: --")
        self.lbl_current_fps = QLabel("Current FPS: --")
        self.btn_restart = QPushButton("Restart Camera")
        self.btn_save = QPushButton("Save Settings")
        self.btn_load = QPushButton("Load Settings")
        v.addWidget(self.lbl_cam_index)
        v.addWidget(self.lbl_current_fps)
        v.addWidget(self.btn_restart)
        v.addWidget(self.btn_save)
        v.addWidget(self.btn_load)
        self.btn_restart.clicked.connect(self._do_restart)  # type: ignore[attr-defined]
        self.btn_save.clicked.connect(self._do_save)  # type: ignore[attr-defined]
        self.btn_load.clicked.connect(self._do_load)  # type: ignore[attr-defined]
        w.setLayout(v)
        return w

    # Load settings into UI ---------------------------------------------
    def _load_settings_into_ui(self) -> None:
        supported_res = self.controller.get_supported_resolutions()
        self.cmb_resolution.clear()
        for w, h in supported_res:
            self.cmb_resolution.addItem(f"{w}x{h}")
        supported_fps = self.controller.get_supported_fps()
        self.cmb_fps.clear()
        for f in supported_fps:
            self.cmb_fps.addItem(str(f))
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
