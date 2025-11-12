"""
LauncherUI: Safe startup window for Monocular Eye Tracker

Shows title, description, and buttons to start tracking, run calibration, edit settings, or exit.
No camera or tracking starts until the user explicitly clicks Start Tracking.
"""
from __future__ import annotations

import os

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QLabel,
        QPushButton,
        QSpacerItem,
        QSizePolicy,
        QMessageBox,
    )
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class LauncherUI(QWidget):  # type: ignore[misc]
    def __init__(self):  # type: ignore[no-redef]
        super().__init__()
        self.setWindowTitle("Monocular Eye Tracker - Launcher")
        try:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        except Exception:
            pass
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Monocular Eye Tracker")
        try:
            f = QFont()
            f.setPointSize(20)
            f.setBold(True)
            title.setFont(f)
        except Exception:
            pass
        layout.addWidget(title)

        desc = QLabel("Cursor control is disabled until you choose Start Tracking.")
        try:
            desc.setWordWrap(True)
        except Exception:
            pass
        layout.addWidget(desc)

        # Panic hotkey note
        note = QLabel("Cursor only — OptiKey handles click selection. Press SPACE or ESC to STOP tracking.")
        try:
            note.setStyleSheet("color: #cc0000; font-weight: bold;")
        except Exception:
            pass
        layout.addWidget(note)

        layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))

        btn_start = QPushButton("Start Tracking")
        btn_calib = QPushButton("Calibration")
        btn_settings = QPushButton("Settings")
        btn_exit = QPushButton("Exit")
        layout.addWidget(btn_start)
        layout.addWidget(btn_calib)
        layout.addWidget(btn_settings)
        layout.addWidget(btn_exit)

        layout.addSpacerItem(QSpacerItem(0, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.setLayout(layout)

        # Wire up actions
        try:
            from MonocularTracker.app import start_tracking, run_calibration
            from MonocularTracker.ui.settings_ui import SettingsDialog
        except Exception:
            start_tracking = None  # type: ignore
            run_calibration = None  # type: ignore
            SettingsDialog = None  # type: ignore

        def _on_start():
            if start_tracking is None:
                QMessageBox.warning(self, "Error", "Tracking entry point not available.")
                return
            start_tracking(self)

        def _on_calib():
            if run_calibration is None:
                QMessageBox.warning(self, "Error", "Calibration entry point not available.")
                return
            run_calibration(self)

        def _on_settings():
            if SettingsDialog is None:
                QMessageBox.warning(self, "Error", "Settings UI not available.")
                return
            dlg = SettingsDialog(self)
            dlg.exec()

        btn_start.clicked.connect(_on_start)  # type: ignore[attr-defined]
        btn_calib.clicked.connect(_on_calib)  # type: ignore[attr-defined]
        btn_settings.clicked.connect(_on_settings)  # type: ignore[attr-defined]
        btn_exit.clicked.connect(self.close)  # type: ignore[attr-defined]
