from __future__ import annotations

from typing import Optional

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QWidget,
        QMainWindow,
        QHBoxLayout,
        QVBoxLayout,
        QLabel,
        QPushButton,
        QTabWidget,
        QCheckBox,
        QSlider,
        QSpinBox,
        QComboBox,
        QFileDialog,
        QStatusBar,
        QGroupBox,
    )
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore
    QMainWindow = object  # type: ignore
    pyqtSignal = lambda *a, **k: None  # type: ignore

from .video_widget import VideoWidget


class MainWindow(QMainWindow):  # type: ignore[misc]
    startRequested = pyqtSignal()
    stopRequested = pyqtSignal()
    calibrate5Requested = pyqtSignal()
    calibrate9Requested = pyqtSignal()
    settingsSaved = pyqtSignal()
    cameraSettingsRequested = pyqtSignal()
    scanCamerasRequested = pyqtSignal()
    useSelectedCameraRequested = pyqtSignal()

    def __init__(self):  # type: ignore[no-redef]
        super().__init__()
        self.setWindowTitle("MonocularEyeTracker")
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout()

        # Left: video and status
        left = QVBoxLayout()
        self.video = VideoWidget()
        left.addWidget(self.video, stretch=1)
        self.status_label = QLabel("Face: -- | Eye: -- | Conf: -- | FPS: --")
        left.addWidget(self.status_label)

        # Right: tabs
        right = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self._build_tab_home(), "Home")
        tabs.addTab(self._build_tab_calibration(), "Calibration")
        tabs.addTab(self._build_tab_camera_settings(), "Camera Settings")
        tabs.addTab(self._build_tab_failsafe(), "Fail-Safe")
        right.addWidget(tabs, stretch=1)

        # Start/Stop
        self.btn_start = QPushButton("Start Tracking")
        self.btn_stop = QPushButton("Stop Tracking")
        self.btn_stop.setEnabled(False)
        right.addWidget(self.btn_start)
        right.addWidget(self.btn_stop)
        note = QLabel("Cursor only — OptiKey handles clicking.")
        try:
            note.setStyleSheet("color: #cc0000; font-weight: bold;")
        except Exception:
            pass
        right.addWidget(note)

        # Wire
        self.btn_start.clicked.connect(self.startRequested)  # type: ignore[attr-defined]
        self.btn_stop.clicked.connect(self.stopRequested)  # type: ignore[attr-defined]

        root.addLayout(left, stretch=3)
        root.addLayout(right, stretch=2)
        central.setLayout(root)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

    # Tabs --------------------------------------------------------------
    def _build_tab_home(self):
        w = QWidget()
        v = QVBoxLayout()
        # Basic tracking controls and tips
        info = QLabel("Start tracking when you are ready. Press Space or Esc at any time to PANIC (stop).")
        try:
            info.setWordWrap(True)
        except Exception:
            pass
        v.addWidget(info)
        v.addWidget(QLabel("Smoothing (EMA Alpha)"))
        self.sld_alpha = QSlider(Qt.Orientation.Horizontal)
        self.sld_alpha.setRange(1, 9)
        self.sld_alpha.setValue(3)
        v.addWidget(self.sld_alpha)
        self.chk_right_eye_only = QCheckBox("Right-eye only (MediaPipe Iris)")
        self.chk_right_eye_only.setChecked(True)
        v.addWidget(self.chk_right_eye_only)
        # Buttons placed below the tabs area already; keep Home simple
        w.setLayout(v)
        return w
    def _build_tab_calibration(self):
        w = QWidget()
        v = QVBoxLayout()
        self.btn_calib5 = QPushButton("5-Point Calibration")
        self.btn_calib9 = QPushButton("9-Point Calibration")
        self.chk_samples = QCheckBox("Collect 20–30 samples per point (recommended)")
        self.chk_auto_check = QCheckBox("Auto-check accuracy after calibration")
        self.chk_enable_drift = QCheckBox("Enable drift correction")
        v.addWidget(self.btn_calib5)
        v.addWidget(self.btn_calib9)
        v.addWidget(self.chk_samples)
        v.addWidget(self.chk_auto_check)
        v.addWidget(self.chk_enable_drift)
        self.lbl_calib_metrics = QLabel("Mean error: -- px | Max error: -- px")
        v.addWidget(self.lbl_calib_metrics)
        w.setLayout(v)
        self.btn_calib5.clicked.connect(self.calibrate5Requested)  # type: ignore[attr-defined]
        self.btn_calib9.clicked.connect(self.calibrate9Requested)  # type: ignore[attr-defined]
        return w

    def _build_tab_camera_settings(self):
        w = QWidget()
        v = QVBoxLayout()
        # Camera selection
        v.addWidget(QLabel("Camera"))
        row_cam = QHBoxLayout()
        self.cmb_cameras = QComboBox()
        self.btn_scan_cam = QPushButton("Scan")
        self.btn_use_cam = QPushButton("Use")
        try:
            self.btn_use_cam.setEnabled(False)
        except Exception:
            pass
        row_cam.addWidget(self.cmb_cameras, stretch=1)
        row_cam.addWidget(self.btn_scan_cam)
        row_cam.addWidget(self.btn_use_cam)
        v.addLayout(row_cam)
        # Wire camera selection actions (handled by AppCore)
        self.btn_scan_cam.clicked.connect(self.scanCamerasRequested)  # type: ignore[attr-defined]
        self.btn_use_cam.clicked.connect(self.useSelectedCameraRequested)  # type: ignore[attr-defined]

        # Minimal inline controls per spec
        self.cmb_res = QComboBox()
        self.cmb_res.addItems(["640x480", "1280x720", "1920x1080"])  # basic choices
        v.addWidget(QLabel("Resolution"))
        v.addWidget(self.cmb_res)
        self.cmb_fps = QComboBox()
        self.cmb_fps.addItems(["15", "30", "60"])  # basic choices
        v.addWidget(QLabel("Frame rate (FPS)"))
        v.addWidget(self.cmb_fps)
        self.sld_brightness = QSlider(Qt.Orientation.Horizontal)
        self.sld_brightness.setRange(0, 255)
        v.addWidget(QLabel("Brightness"))
        v.addWidget(self.sld_brightness)
        self.sld_contrast = QSlider(Qt.Orientation.Horizontal)
        self.sld_contrast.setRange(0, 255)
        v.addWidget(QLabel("Contrast"))
        v.addWidget(self.sld_contrast)
        self.btn_apply_cam = QPushButton("Apply Resolution/FPS")
        v.addWidget(self.btn_apply_cam)
        self.btn_camera_settings = QPushButton("Open Advanced Camera Settings…")
        v.addWidget(self.btn_camera_settings)
        self.btn_camera_settings.clicked.connect(self.cameraSettingsRequested)  # type: ignore[attr-defined]
        w.setLayout(v)
        return w

    def _build_tab_failsafe(self):
        w = QWidget()
        v = QVBoxLayout()
        label = QLabel("Fail-Safe: Press Space or Esc to stop tracking instantly. Use the button below if needed.")
        try:
            label.setWordWrap(True)
        except Exception:
            pass
        v.addWidget(label)
        self.btn_panic = QPushButton("PANIC — Stop Tracking")
        v.addWidget(self.btn_panic)
        # Wire up in AppCore via public slot name
        w.setLayout(v)
        return w

    def _build_tab_system(self):
        w = QWidget()
        self.btn_camera_settings.clicked.connect(self.cameraSettingsRequested)  # type: ignore[attr-defined]
        v = QVBoxLayout()
        self.spn_camera = QSpinBox()
        self.spn_camera.setRange(0, 10)
        self.spn_camera.setValue(0)
        v.addWidget(QLabel("Camera index"))
        v.addWidget(self.spn_camera)
        self.cmb_res = QComboBox()
        self.cmb_res.addItems(["1280x720", "1920x1080"])  # fixed options for now
        v.addWidget(QLabel("Resolution"))
        v.addWidget(self.cmb_res)
        self.btn_save = QPushButton("Save settings.json")
        self.btn_load = QPushButton("Load settings.json")
        v.addWidget(self.btn_save)
        v.addWidget(self.btn_load)
        self.btn_save.clicked.connect(self.settingsSaved)  # type: ignore[attr-defined]
        w.setLayout(v)
        return w

    # Public update API -------------------------------------------------
    def update_status(self, *, face_ok: bool, eye_ok: bool, conf: float, fps: float) -> None:
        self.status_label.setText(f"Face: {'detected' if face_ok else 'lost'} | Eye: {'detected' if eye_ok else 'lost'} | Conf: {int(conf*100)}% | FPS: {fps:.1f}")

    def update_video(self, *, frame, landmarks=None, iris=None, box=None, predicted=None) -> None:
        self.video.set_overlays(frame=frame, landmarks=landmarks, iris_center=iris, eyelid_box=box, predicted=predicted, show_landmarks=True, show_vector=True, show_pred=True)

    def toggle_controls(self, tracking: bool) -> None:
        self.btn_start.setEnabled(not tracking)
        self.btn_stop.setEnabled(tracking)
