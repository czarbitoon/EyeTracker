from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QSlider,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QStatusBar,
    QGroupBox,
)


class MainWindow(QMainWindow):
    startRequested = pyqtSignal()
    stopRequested = pyqtSignal()
    calibrateRequested = pyqtSignal(int)  # points
    scanCamerasRequested = pyqtSignal()
    useSelectedCameraRequested = pyqtSignal()
    openCameraSettingsRequested = pyqtSignal()
    panicRequested = pyqtSignal()
    smoothingChanged = pyqtSignal(float)
    cameraIndexChanged = pyqtSignal(int)
    resolutionChanged = pyqtSignal(str)
    exposureChanged = pyqtSignal(float)
    brightnessChanged = pyqtSignal(float)
    mirrorToggled = pyqtSignal(bool)
    landmarksToggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MonocularEyeAssist")
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout()

        # Left: video and status
        left = QVBoxLayout()
        self.video = QLabel("Camera preview")
        self.video.setMinimumSize(640, 360)
        self.video.setStyleSheet("background:#111;color:#777;border:1px solid #333;")
        self.status_label = QLabel("Face: -- | Eye: -- | Conf: -- | FPS: --")
        left.addWidget(self.video, stretch=1)
        left.addWidget(self.status_label)

        # Right: tabs
        right = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self._tab_home(), "Home")
        tabs.addTab(self._tab_calib(), "Calibration")
        tabs.addTab(self._tab_camera(), "Camera Settings")
        tabs.addTab(self._tab_panic(), "Panic Mode")
        right.addWidget(tabs, stretch=1)

        # Start/Stop
        self.btn_start = QPushButton("Start Tracking")
        self.btn_stop = QPushButton("Stop Tracking")
        self.btn_stop.setEnabled(False)
        right.addWidget(self.btn_start)
        right.addWidget(self.btn_stop)

        # Wire
        self.btn_start.clicked.connect(self.startRequested)
        self.btn_stop.clicked.connect(self.stopRequested)

        root.addLayout(left, stretch=3)
        root.addLayout(right, stretch=2)
        central.setLayout(root)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

    # Tabs --------------------------------------------------------------
    def _tab_home(self):
        w = QWidget()
        v = QVBoxLayout()
        info = QLabel("Right-eye only. Cursor movement only — pair with OptiKey for speech.")
        info.setWordWrap(True)
        v.addWidget(info)
        v.addWidget(QLabel("Smoothing strength (0=raw, 1=heavy)"))
        self.sld_alpha = QSlider(Qt.Horizontal)
        self.sld_alpha.setRange(0, 100)
        self.sld_alpha.setValue(35)
        self.sld_alpha.valueChanged.connect(lambda val: self.smoothingChanged.emit(float(val) / 100.0))
        v.addWidget(self.sld_alpha)
        w.setLayout(v)
        return w

    def _tab_calib(self):
        w = QWidget()
        v = QVBoxLayout()
        v.addWidget(QLabel("Collects 50–100 samples per point. Big dots, slow pacing."))
        self.btn_calib5 = QPushButton("5-Point Calibration")
        self.btn_calib9 = QPushButton("9-Point Calibration")
        self.btn_calib5.clicked.connect(lambda: self.calibrateRequested.emit(5))
        self.btn_calib9.clicked.connect(lambda: self.calibrateRequested.emit(9))
        v.addWidget(self.btn_calib5)
        v.addWidget(self.btn_calib9)
        w.setLayout(v)
        return w

    def _tab_camera(self):
        w = QWidget()
        v = QVBoxLayout()
        v.addWidget(QLabel("Camera"))
        row = QHBoxLayout()
        self.cmb_cameras = QComboBox(); self.btn_scan = QPushButton("Scan"); self.btn_use = QPushButton("Use")
        row.addWidget(self.cmb_cameras, 1); row.addWidget(self.btn_scan); row.addWidget(self.btn_use)
        v.addLayout(row)
        self.cmb_res = QComboBox(); self.cmb_res.addItems(["640x480", "1280x720", "1920x1080"])  
        v.addWidget(QLabel("Resolution")); v.addWidget(self.cmb_res)
        self.sld_brightness = QSlider(Qt.Horizontal); self.sld_brightness.setRange(-100, 100); v.addWidget(QLabel("Brightness")); v.addWidget(self.sld_brightness)
        self.sld_exposure = QSlider(Qt.Horizontal); self.sld_exposure.setRange(-100, 100); v.addWidget(QLabel("Exposure")); v.addWidget(self.sld_exposure)
        self.chk_mirror = QCheckBox("Mirror feed"); self.chk_mirror.setChecked(True); v.addWidget(self.chk_mirror)
        self.chk_landmarks = QCheckBox("Show right-eye landmarks"); self.chk_landmarks.setChecked(True); v.addWidget(self.chk_landmarks)
        w.setLayout(v)
        # Wire
        self.btn_scan.clicked.connect(self.scanCamerasRequested)
        self.btn_use.clicked.connect(self.useSelectedCameraRequested)
        self.cmb_cameras.currentIndexChanged.connect(lambda _: self.cameraIndexChanged.emit(self.cmb_cameras.currentData() or 0))
        self.cmb_res.currentTextChanged.connect(self.resolutionChanged)
        self.sld_brightness.valueChanged.connect(lambda v: self.brightnessChanged.emit(float(v)))
        self.sld_exposure.valueChanged.connect(lambda v: self.exposureChanged.emit(float(v)))
        self.chk_mirror.toggled.connect(self.mirrorToggled)
        self.chk_landmarks.toggled.connect(self.landmarksToggled)
        return w

    def _tab_panic(self):
        w = QWidget()
        v = QVBoxLayout()
        v.addWidget(QLabel("Ctrl+Shift+Q triggers Panic Mode. Use button below if needed."))
        self.btn_panic = QPushButton("PANIC — Stop Tracking")
        v.addWidget(self.btn_panic)
        self.btn_panic.clicked.connect(self.panicRequested)
        w.setLayout(v)
        return w

    # Public API -------------------------------------------------------
    def toggle_controls(self, tracking: bool) -> None:
        self.btn_start.setEnabled(not tracking)
        self.btn_stop.setEnabled(tracking)

    def update_status(self, *, face_ok: bool, eye_ok: bool, conf: float, fps: float) -> None:
        self.status_label.setText(f"Face: {'detected' if face_ok else 'lost'} | Eye: {'detected' if eye_ok else 'lost'} | Conf: {int(conf*100)}% | FPS: {fps:.1f}")
