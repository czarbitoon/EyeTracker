"""
Settings dialog for Monocular Eye Tracker

Allows editing a small subset of settings in settings.json:
- dwell.time_ms
- smoothing.alpha
- blink.enabled
"""
from __future__ import annotations

import json
import os

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QSpinBox,
        QDoubleSpinBox,
        QCheckBox,
        QPushButton,
        QMessageBox,
    )
except Exception:  # pragma: no cover
    QDialog = object  # type: ignore


def _settings_path() -> str:
    # This file is in MonocularTracker/ui/; settings.json sits in MonocularTracker/
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "settings.json")


def _load_settings() -> dict:
    path = _settings_path()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_settings(data: dict) -> None:
    path = _settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class SettingsDialog(QDialog):  # type: ignore[misc]
    def __init__(self, parent=None):  # type: ignore[no-redef]
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._build_ui()
        self._load_into_ui()

    def _build_ui(self) -> None:
        v = QVBoxLayout()

        # Dwell time
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Dwell time (ms):"))
        self.spn_dwell = QSpinBox()
        self.spn_dwell.setRange(100, 5000)
        self.spn_dwell.setSingleStep(50)
        row1.addWidget(self.spn_dwell)
        v.addLayout(row1)

        # Smoothing alpha
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Smoothing alpha (0-1):"))
        self.spn_alpha = QDoubleSpinBox()
        self.spn_alpha.setDecimals(2)
        self.spn_alpha.setRange(0.0, 1.0)
        self.spn_alpha.setSingleStep(0.05)
        row2.addWidget(self.spn_alpha)
        v.addLayout(row2)

        # Blink enable
        row3 = QHBoxLayout()
        self.chk_blink = QCheckBox("Enable blink click")
        row3.addWidget(self.chk_blink)
        v.addLayout(row3)

        # Action buttons
        row_btn = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        row_btn.addWidget(btn_save)
        row_btn.addWidget(btn_cancel)
        v.addLayout(row_btn)

        self.setLayout(v)

        btn_save.clicked.connect(self._on_save)  # type: ignore[attr-defined]
        btn_cancel.clicked.connect(self.reject)  # type: ignore[attr-defined]

    def _load_into_ui(self) -> None:
        try:
            cfg = _load_settings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load settings: {e}")
            cfg = {}

        dwell_ms = int(cfg.get("dwell", {}).get("time_ms", 700))
        alpha = float(cfg.get("smoothing", {}).get("alpha", 0.25))
        blink_enabled = bool(cfg.get("blink", {}).get("enabled", False))

        self.spn_dwell.setValue(dwell_ms)
        self.spn_alpha.setValue(alpha)
        self.chk_blink.setChecked(blink_enabled)

    def _on_save(self) -> None:
        try:
            cfg = _load_settings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load settings: {e}")
            return

        # Apply changes
        cfg.setdefault("dwell", {})
        cfg["dwell"]["time_ms"] = int(self.spn_dwell.value())

        cfg.setdefault("smoothing", {})
        cfg["smoothing"]["alpha"] = float(self.spn_alpha.value())

        cfg.setdefault("blink", {})
        cfg["blink"]["enabled"] = bool(self.chk_blink.isChecked())

        try:
            _save_settings(cfg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
            return

        self.accept()
