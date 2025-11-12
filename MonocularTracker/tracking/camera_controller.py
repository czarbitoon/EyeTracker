from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from MonocularTracker.core.settings import SettingsManager


class CameraController:
    """
    Thin controller over OpenCV VideoCapture to adjust common webcam properties.

    It reads/writes values to SettingsManager and attempts to apply to the active
    VideoCapture when available. Resolution/FPS changes are considered "major" and
    should be followed by a camera restart, which is delegated to `restart_callback`.
    """

    RES_PRESETS: List[Tuple[int, int]] = [(640, 480), (1280, 720), (1920, 1080)]
    FPS_PRESETS: List[int] = [15, 30, 60]

    def __init__(self, get_cap: Callable[[], Optional[object]], restart_callback: Callable[[], None], settings: SettingsManager, change_index_callback: Optional[Callable[[int], None]] = None) -> None:
        self._get_cap = get_cap
        self._restart = restart_callback
        self.settings = settings
        self._change_index = change_index_callback

    # Helpers -----------------------------------------------------------
    def _cap(self):
        cap = self._get_cap()
        return cap if (cap is not None) else None

    def _set_prop(self, prop_id: int, value: float) -> bool:
        cap = self._cap()
        if cap is None or cv2 is None:
            return False
        try:
            ok = cap.set(prop_id, float(value))
            return bool(ok)
        except Exception:
            return False

    def _get_prop(self, prop_id: int) -> Optional[float]:
        cap = self._cap()
        if cap is None or cv2 is None:
            return None
        try:
            v = cap.get(prop_id)
            return float(v)
        except Exception:
            return None

    # Major settings ----------------------------------------------------
    def set_resolution(self, width: int, height: int) -> None:
        self.settings.set_camera_resolution(int(width), int(height))
        # Do not auto-restart; caller should trigger apply/restart

    def set_fps(self, value: int) -> None:
        self.settings.set_camera_fps(int(value))
        # Try to hint device immediately (may be ignored). Final set on restart
        if cv2 is not None:
            self._set_prop(cv2.CAP_PROP_FPS, float(value))

    def set_camera_index(self, idx: int) -> None:
        self.settings.set_camera_index(int(idx))
        if self._change_index is not None:
            try:
                self._change_index(int(idx))
            except Exception:
                pass

    # Exposure ----------------------------------------------------------
    def set_auto_exposure(self, on_off: bool) -> bool:
        self.settings.set_camera_auto_exposure(bool(on_off))
        if cv2 is None:
            return False
        # OpenCV AUTO_EXPOSURE varies by backend. Try common values.
        for val in (0.75, 1.0, 0.0, 0.25):  # try several hints
            if self._set_prop(cv2.CAP_PROP_AUTO_EXPOSURE, float(val if on_off else 0.0)):
                return True
        return False

    def set_exposure(self, value: float) -> bool:
        self.settings.set_camera_exposure(float(value))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_EXPOSURE, float(value))

    # Gain / Brightness / Contrast -------------------------------------
    def set_gain(self, value: float) -> bool:
        self.settings.set_camera_gain(float(value))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_GAIN, float(value))

    def set_brightness(self, value: float) -> bool:
        self.settings.set_camera_brightness(float(value))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_BRIGHTNESS, float(value))

    def set_contrast(self, value: float) -> bool:
        self.settings.set_camera_contrast(float(value))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_CONTRAST, float(value))

    # White balance -----------------------------------------------------
    def set_white_balance(self, value: int) -> bool:
        self.settings.set_camera_wb_temperature(int(value))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_WB_TEMPERATURE, float(value))

    def set_auto_focus(self, on_off: bool) -> bool:
        self.settings.set_camera_auto_focus(bool(on_off))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_AUTOFOCUS, 1.0 if on_off else 0.0)

    def set_focus(self, value: float) -> bool:
        self.settings.set_camera_focus(float(value))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_FOCUS, float(value))

    def set_auto_white_balance(self, on_off: bool) -> bool:
        self.settings.set_camera_auto_wb(bool(on_off))
        if cv2 is None:
            return False
        return self._set_prop(cv2.CAP_PROP_AUTO_WB, 1.0 if on_off else 0.0)

    # Query -------------------------------------------------------------
    def get_supported_resolutions(self) -> List[Tuple[int, int]]:
        if cv2 is None:
            return self.RES_PRESETS
        cap = self._cap()
        if cap is None:
            # unknown; report presets
            return self.RES_PRESETS
        # Probe by attempting to set and verify, then restore
        try:
            prev_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            prev_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        except Exception:
            prev_w, prev_h = 0, 0
        supported: List[Tuple[int, int]] = []
        for w, h in self.RES_PRESETS:
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if abs(aw - w) < 8 and abs(ah - h) < 8:
                    supported.append((w, h))
            except Exception:
                continue
        # restore
        if prev_w > 0 and prev_h > 0:
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, prev_w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, prev_h)
            except Exception:
                pass
        return supported or self.RES_PRESETS

    def get_supported_fps(self) -> List[int]:
        if cv2 is None:
            return self.FPS_PRESETS
        cap = self._cap()
        if cap is None:
            return self.FPS_PRESETS
        prev = self._get_prop(cv2.CAP_PROP_FPS)
        supported: List[int] = []
        for f in self.FPS_PRESETS:
            try:
                if self._set_prop(cv2.CAP_PROP_FPS, float(f)):
                    val = self._get_prop(cv2.CAP_PROP_FPS)
                    if val is None or abs(val - f) < 1.0:
                        supported.append(f)
            except Exception:
                continue
        # restore
        if prev is not None:
            try:
                self._set_prop(cv2.CAP_PROP_FPS, float(prev))
            except Exception:
                pass
        return supported or self.FPS_PRESETS

    def get_current_settings(self) -> Dict[str, float | int | bool | Tuple[int, int]]:
        w, h = self.settings.camera_resolution()
        fps = self.settings.camera_fps()
        data: Dict[str, float | int | bool | Tuple[int, int]] = {
            "resolution": (w, h),
            "fps": fps,
            "auto_exposure": self.settings.camera_auto_exposure(),
            "exposure": self.settings.camera_exposure(),
            "gain": self.settings.camera_gain(),
            "brightness": self.settings.camera_brightness(),
            "contrast": self.settings.camera_contrast(),
            "auto_wb": self.settings.camera_auto_wb(),
            "wb_temperature": self.settings.camera_wb_temperature(),
            "auto_focus": self.settings.camera_auto_focus(),
            "focus": self.settings.camera_focus(),
        }
        return data

    # Actions -----------------------------------------------------------
    def apply_resolution_fps(self) -> None:
        # Caller uses this after set_resolution/set_fps changes
        self._restart()
