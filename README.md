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

## File Map (quick guide)

- `run.py`: Preferred launcher; starts the modern UI in `MonocularTracker/core/app.py`.
- `app.py` (repo root): Thin launcher that forwards to the modern UI.
- `MonocularTracker/core/app.py`: Main application setup, logging suppression, UI wiring.
- `MonocularTracker/tracking/pipeline.py`: Frame processing pipeline and gaze mapping.
- `MonocularTracker/tracking/calibration.py`: Calibration training and error reporting.
- `MonocularTracker/ui/main_window.py`: Primary window; start/stop, calibration controls.
- `MonocularTracker/ui/calibration_ui.py`: Fullscreen calibration overlay with targets and crosshair.
- `MonocularTracker/ui/calibration_plots.py`: Calibration quality plots.
- `MonocularTracker/ai/openvino_gaze.py`: Optional CPU-friendly gaze adapter.
- `MonocularTracker/calibration_state.json`: Saved calibration model (auto-loaded).

## Run

Preferred entry point is the top-level `run.py` in the project root:

```powershell
python run.py
```

Alternative module form:

```powershell
python -m MonocularTracker.core.app
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

Consolidation note: The separate MonocularEyeAssist app has been removed. All features and improvements now live in MonocularTracker. Requirements were cleaned accordingly (PyQt6 only).

## Calibration Workflow

1. Launch the app; open the Calibration tab.
2. Follow the moving dots; samples are collected per target.
3. Model trains automatically; results are saved to `calibration_state.json`.
4. Start tracking; use dwell-click and settings to tune behavior.

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
