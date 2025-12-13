from __future__ import annotations

"""
Lightweight OpenVINO gaze estimation adapter (CPU-only).

This stub provides a safe interface for integrating OpenVINO's gaze-estimation-adas-0002
without hard failing if the runtime or model files are missing. It exposes:

    class OpenVinoGaze:
        available: bool
        def predict(self, eye_crop_bgr, head_pose: tuple[float, float, float]) -> tuple[float, float] | None

Returns a normalized gaze vector (gx, gy) in [-1, 1] if available, else None.
Mapping to screen coordinates should be handled by the existing calibration adapter.
"""

from typing import Optional, Tuple

try:
    import numpy as np  # type: ignore
    from openvino.runtime import Core  # type: ignore
except Exception:
    np = None  # type: ignore
    Core = None  # type: ignore


class OpenVinoGaze:
    def __init__(self, model_dir: Optional[str] = None) -> None:
        self.available = False
        self._core = None
        self._compiled = None
        self._input_names: list[str] = []
        self._output_names: list[str] = []
        try:
            if Core is None:
                return
            core = Core()
            # Expect model files placed in model_dir (IR format .xml/.bin)
            if not model_dir:
                # Leave unavailable unless provided later
                return
            xml = model_dir + "/gaze-estimation-adas-0002.xml"
            binf = model_dir + "/gaze-estimation-adas-0002.bin"
            import os
            if not (os.path.exists(xml) and os.path.exists(binf)):
                return
            net = core.read_model(model=xml, weights=binf)
            compiled = core.compile_model(net, device_name="CPU")
            self._core = core
            self._compiled = compiled
            self._input_names = [inp.get_any_name() for inp in net.inputs]
            self._output_names = [out.get_any_name() for out in net.outputs]
            self.available = True
        except Exception:
            self.available = False

    def predict(self, eye_crop_bgr, head_pose: Tuple[float, float, float]) -> Optional[Tuple[float, float]]:
        if not self.available or self._compiled is None:
            return None
        try:
            # Preprocess: resize to expected size (60x60 typical for ADAS models), BGR->RGB, normalize
            import cv2  # type: ignore
            img = eye_crop_bgr
            if img is None:
                return None
            img = cv2.resize(img, (60, 60))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype(np.float32)
            img = img / 255.0
            # NCHW
            blob = np.transpose(img, (2, 0, 1))[None, :, :, :]
            # Prepare inputs: model expects left/right eye + head pose; for monocular, reuse single eye
            inputs = {}
            # Heuristics: if model has named inputs, try to map
            for name in self._input_names:
                if "head_pose" in name or "head_pose_angles" in name:
                    inputs[name] = np.array([head_pose], dtype=np.float32)
                else:
                    inputs[name] = blob
            result = self._compiled(inputs)
            # Extract gaze vector; pick first output
            out_name = self._output_names[0] if self._output_names else None
            if out_name is None:
                return None
            vec = result[out_name]
            if isinstance(vec, np.ndarray):
                v = vec.reshape(-1)
                if v.size >= 2:
                    gx = float(max(-1.0, min(1.0, v[0])))
                    gy = float(max(-1.0, min(1.0, v[1])))
                    return (gx, gy)
            return None
        except Exception:
            return None
