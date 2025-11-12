"""
Settings manager for MonocularTracker.

Loads/saves JSON settings from MonocularTracker/settings.json and exposes helpers.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict


class SettingsManager:
    def __init__(self) -> None:
        here = os.path.dirname(os.path.abspath(__file__))
        self._root = os.path.dirname(here)
        self.path = os.path.join(self._root, "settings.json")
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            # provide minimal defaults
            self.data = {
                "camera_index": 0,
                "smoothing": {"alpha": 0.25},
                "overlay": {"enabled": True},
                "camera": {
                    "show_window": True,
                    "resolution": [1280, 720],
                    "fps": 30,
                    "auto_exposure": True,
                    "exposure": 0.0,
                    "gain": 0.0,
                    "brightness": 0.0,
                    "contrast": 0.0,
                    "auto_wb": True,
                    "wb_temperature": 4500,
                    "auto_focus": True,
                    "focus": 0.0,
                },
                # Optional per-camera profiles keyed by camera index as a string
                "camera_profiles": {},
                "drift": {"enabled": True, "learn_rate": 0.01},
            }
            return
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    # Convenience accessors -------------------------------------------------
    def camera_index(self) -> int:
        return int(self.data.get("camera_index", 0))

    def set_camera_index(self, idx: int) -> None:
        self.data["camera_index"] = int(idx)

    def _profile(self) -> dict:
        """Return (and create) the profile dict for current camera index."""
        profiles = self.data.setdefault("camera_profiles", {})
        key = str(self.camera_index())
        prof = profiles.get(key)
        if not isinstance(prof, dict):
            prof = {}
            profiles[key] = prof
        return prof

    def smoothing_alpha(self) -> float:
        return float(self.data.get("smoothing", {}).get("alpha", 0.25))

    def show_overlay(self) -> bool:
        return bool(self.data.get("overlay", {}).get("enabled", True))

    def show_camera_window(self) -> bool:
        return bool(self.data.get("camera", {}).get("show_window", True))

    def drift_enabled(self) -> bool:
        return bool(self.data.get("drift", {}).get("enabled", True))

    def drift_learn_rate(self) -> float:
        return float(self.data.get("drift", {}).get("learn_rate", 0.01))

    # Camera settings ---------------------------------------------------
    def camera_resolution(self) -> tuple[int, int]:
        # Prefer per-camera profile
        arr = self._profile().get("resolution") or self.data.get("camera", {}).get("resolution", [1280, 720])
        try:
            return int(arr[0]), int(arr[1])
        except Exception:
            return 1280, 720

    def set_camera_resolution(self, w: int, h: int) -> None:
        self._profile()["resolution"] = [int(w), int(h)]
        self.data.setdefault("camera", {})["resolution"] = [int(w), int(h)]

    def camera_fps(self) -> int:
        v = self._profile().get("fps")
        if v is None:
            v = self.data.get("camera", {}).get("fps", 30)
        return int(v)

    def set_camera_fps(self, fps: int) -> None:
        self._profile()["fps"] = int(fps)
        self.data.setdefault("camera", {})["fps"] = int(fps)

    def camera_auto_exposure(self) -> bool:
        v = self._profile().get("auto_exposure")
        if v is None:
            v = self.data.get("camera", {}).get("auto_exposure", True)
        return bool(v)

    def set_camera_auto_exposure(self, on: bool) -> None:
        self._profile()["auto_exposure"] = bool(on)
        self.data.setdefault("camera", {})["auto_exposure"] = bool(on)

    def camera_exposure(self) -> float:
        v = self._profile().get("exposure")
        if v is None:
            v = self.data.get("camera", {}).get("exposure", 0.0)
        return float(v)

    def set_camera_exposure(self, v: float) -> None:
        self._profile()["exposure"] = float(v)
        self.data.setdefault("camera", {})["exposure"] = float(v)

    def camera_gain(self) -> float:
        v = self._profile().get("gain")
        if v is None:
            v = self.data.get("camera", {}).get("gain", 0.0)
        return float(v)

    def set_camera_gain(self, v: float) -> None:
        self._profile()["gain"] = float(v)
        self.data.setdefault("camera", {})["gain"] = float(v)

    def camera_brightness(self) -> float:
        v = self._profile().get("brightness")
        if v is None:
            v = self.data.get("camera", {}).get("brightness", 0.0)
        return float(v)

    def set_camera_brightness(self, v: float) -> None:
        self._profile()["brightness"] = float(v)
        self.data.setdefault("camera", {})["brightness"] = float(v)

    def camera_contrast(self) -> float:
        v = self._profile().get("contrast")
        if v is None:
            v = self.data.get("camera", {}).get("contrast", 0.0)
        return float(v)

    def set_camera_contrast(self, v: float) -> None:
        self._profile()["contrast"] = float(v)
        self.data.setdefault("camera", {})["contrast"] = float(v)

    def camera_auto_wb(self) -> bool:
        v = self._profile().get("auto_wb")
        if v is None:
            v = self.data.get("camera", {}).get("auto_wb", True)
        return bool(v)

    def set_camera_auto_wb(self, on: bool) -> None:
        self._profile()["auto_wb"] = bool(on)
        self.data.setdefault("camera", {})["auto_wb"] = bool(on)

    def camera_wb_temperature(self) -> int:
        v = self._profile().get("wb_temperature")
        if v is None:
            v = self.data.get("camera", {}).get("wb_temperature", 4500)
        return int(v)

    def set_camera_wb_temperature(self, t: int) -> None:
        self._profile()["wb_temperature"] = int(t)
        self.data.setdefault("camera", {})["wb_temperature"] = int(t)

    def camera_auto_focus(self) -> bool:
        v = self._profile().get("auto_focus")
        if v is None:
            v = self.data.get("camera", {}).get("auto_focus", True)
        return bool(v)

    def set_camera_auto_focus(self, on: bool) -> None:
        self._profile()["auto_focus"] = bool(on)
        self.data.setdefault("camera", {})["auto_focus"] = bool(on)

    def camera_focus(self) -> float:
        v = self._profile().get("focus")
        if v is None:
            v = self.data.get("camera", {}).get("focus", 0.0)
        return float(v)

    def set_camera_focus(self, v: float) -> None:
        self._profile()["focus"] = float(v)
        self.data.setdefault("camera", {})["focus"] = float(v)
