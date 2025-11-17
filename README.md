# MonocularEyeTracker

Windows desktop app that moves the mouse cursor using RIGHT-eye gaze. Tabs: Home, Calibration, Camera Settings, Fail-Safe. Uses OpenCV + MediaPipe Iris (FaceMesh refine) for monocular tracking, 9-point calibration, pyautogui cursor control, and a panic hotkey (Space/Esc) to instantly stop tracking.

![CI](https://github.com/czarbitoon/EyeTracker/actions/workflows/windows-build.yml/badge.svg)

## Project Structure

```text
MonocularEyeTracker/
  run.py
  MonocularTracker/
    core/ (app orchestration)
    tracking/ (pipeline, parser, mapping, calibration)
    ui/ (main window, calibration UI, camera settings, panic overlay)
    control/ (cursor, fps monitor)
    analysis/ (calibration plots, metrics)
    settings.json
    calibration_state.json
```

## Requirements

Python 3.10–3.11 on Windows.

Install dependencies:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python run.py
```

## Calibration

Use the Calibration tab (5 or 9 points). Data is saved to `calibration_state.json` automatically after training.

## Build Windows .exe (PyInstaller)

```powershell
pyinstaller -y MonocularEyeTracker.spec
```

Output: `dist/MonocularEyeTracker/MonocularEyeTracker.exe`.

## Safety / Fail-Safe

Press Space or Esc (panic) to stop tracking immediately. Fail-Safe tab provides a PANIC button.

## Notes

Refine iris estimation and drift correction for production use. Webcams may ignore FPS/size hints.

## Legacy README (Original MonocularTracker)

A Python-based monocular eye-tracking input engine designed to integrate with OptiKey by emulating standard mouse input. Tracks the RIGHT eye using MediaPipe FaceMesh/Iris, maps features to screen coordinates with learnable regressors, and provides smoothing and dwell-click.

## Features
- Right-eye iris center + eyelid bounding box extraction (MediaPipe FaceMesh with iris refinement)
- Normalized eye features to (nx, ny) in [0,1]
- Calibration module to collect feature → screen samples
- ML mapping: Polynomial regression or MLPRegressor
- Smoothing (EMA), dwell-click, optional blink detection
- Cursor control via pyautogui (works with OptiKey as a normal mouse)
- Minimal PyQt6 overlays and calibration UI

## Project structure
```
MonocularTracker/
  app.py
  camera.py
  gaze_parser.py
  settings.json
  ai/
    regressors.py
    drift_corrector.py
  calibration/
    calibrator.py
    models.py
    samples/
  control/
    cursor.py
    events.py
  ui/
    calibration_ui.py
    overlay.py
  utils/
    smoothing.py
    dwell.py
    blink.py
```

## Requirements
- Python 3.10–3.11 recommended on Windows
- See `requirements.txt` for Python dependencies

Install (PowerShell):
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run
Use module form to ensure package imports:
```powershell
python -m MonocularTracker.app
```

Or use helper script:
```powershell
python run.py
```

On startup, the app attempts to load a saved calibration from `MonocularTracker/calibration_state.json`. After you complete a calibration run, the trained model is saved back to that file automatically.

## Calibration workflow

1. Launch the app; open the calibration UI (or call `CalibrationUI.start()` if disabled).
2. Follow the moving dots. The app collects (nx, ny) → (x, y) samples for each target point.
3. When finished, the chosen regressor trains; cursor then tracks gaze.
4. Dwell over UI elements to trigger left-clicks (if enabled).

## Notes

- Scaffold implementation: refine iris center estimation, EAR for blink, and drift correction for production use.
- If camera FPS is unstable, software pacing in `camera.py` maintains consistent processing intervals.
- OptiKey integration: pyautogui moves the OS cursor and clicks, so OptiKey recognizes input as a standard mouse.

## Troubleshooting

- If PyQt6 or MediaPipe aren’t installed, imports may warn until you run `pip install -r requirements.txt`.
- Some webcams ignore FPS/size hints; code falls back to actual camera-reported resolution.
- pyautogui failsafe disabled in `app.py` to prevent corner stops.
- Windows High-DPI warning: If you see `qt.qpa.window: SetProcessDpiAwarenessContext() failed: Access is denied.`, it's harmless. This app now defaults to a safer DPI mode on Windows to avoid it. You can force a specific DPI awareness by setting an environment variable before launch:
  - `EYETRACKER_DPI_AWARENESS=1` for system-DPI aware
  - `EYETRACKER_DPI_AWARENESS=2` for per-monitor (v1) [default]
  - `EYETRACKER_DPI_AWARENESS=3` for per-monitor (v2)
   
   Example (PowerShell):
   
   ```powershell
   $env:EYETRACKER_DPI_AWARENESS = "1"; python run.py
   ```
   
   If you only want to silence the log, optionally set:
   
   ```powershell
   $env:QT_LOGGING_RULES = "qt.qpa.window=false"; python run.py
   ```

## License

MIT (update as needed).
