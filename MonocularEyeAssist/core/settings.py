from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple


class Settings:
    """Minimal JSON-backed settings manager for MonocularEyeAssist."""

    def __init__(self) -> None:
        here = os.path.dirname(os.path.abspath(__file__))
        self._root = os.path.dirname(here)
        self.path = os.path.join(self._root, "settings.json")
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.data = {
                "camera_index": 0,
                "mirror": True,
                "smoothing": {"alpha": 0.35, "mode": "ema"},
                "calibration": {"profile": "default", "degree": 2},
                "signal": {
                    "window": 90,
                    "ok": {"rx": 0.08, "ry": 0.05},
                    "strong": {"rx": 0.15, "ry": 0.10},
                },
                "camera": {
                    "resolution": [1280, 720],
                    "fps": 30,
                    "brightness": -1.0,
                    "exposure": -1.0,
                    "show_landmarks": True,
                },
            }
            return
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    # Convenience ------------------------------------------------------
    def camera_index(self) -> int:
        return int(self.data.get("camera_index", 0))

    def set_camera_index(self, idx: int) -> None:
        self.data["camera_index"] = int(idx)

    def camera_resolution(self) -> Tuple[int, int]:
        arr = self.data.get("camera", {}).get("resolution", [1280, 720])
        try:
            return int(arr[0]), int(arr[1])
        except Exception:
            return 1280, 720

    def camera_fps(self) -> int:
        return int(self.data.get("camera", {}).get("fps", 30))

    def camera_brightness(self) -> float:
        return float(self.data.get("camera", {}).get("brightness", -1.0))

    def camera_exposure(self) -> float:
        return float(self.data.get("camera", {}).get("exposure", -1.0))

    def mirror(self) -> bool:
        return bool(self.data.get("mirror", True))

    def set_mirror(self, on: bool) -> None:
        self.data["mirror"] = bool(on)

    def smoothing_alpha(self) -> float:
        return float(self.data.get("smoothing", {}).get("alpha", 0.35))

    def set_smoothing_alpha(self, a: float) -> None:
        self.data.setdefault("smoothing", {})["alpha"] = float(a)

    def smoothing_mode(self) -> str:
        return str(self.data.get("smoothing", {}).get("mode", "ema"))

    def set_smoothing_mode(self, m: str) -> None:
        self.data.setdefault("smoothing", {})["mode"] = str(m)

    def calib_degree(self) -> int:
        return int(self.data.get("calibration", {}).get("degree", 2))

    def set_calib_degree(self, d: int) -> None:
        self.data.setdefault("calibration", {})["degree"] = int(d)

    def signal_window(self) -> int:
        try:
            return int(self.data.get("signal", {}).get("window", 90))
        except Exception:
            return 90

    def signal_thresholds(self) -> tuple[float, float, float, float]:
        s = self.data.get("signal", {})
        ok = s.get("ok", {}) if isinstance(s, dict) else {}
        strong = s.get("strong", {}) if isinstance(s, dict) else {}
        x_ok = float(ok.get("rx", 0.08))
        y_ok = float(ok.get("ry", 0.05))
        x_strong = float(strong.get("rx", 0.15))
        y_strong = float(strong.get("ry", 0.10))
        return (x_ok, x_strong, y_ok, y_strong)
