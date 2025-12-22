from __future__ import annotations

import cv2  # type: ignore
import time
from app.tracking.camera import Camera
from app.tracking.detection import EyeDetector
from app.tracking.smoothing import ButterworthLowPass
from app.tracking.mapping import CursorMapper
from app.control.cursor import CursorController
from app.calibration.monocular import MonocularCalibrator
from app.ui.gaze_overlay import GazeOverlay


def main() -> None:
    cam = Camera()
    detector = EyeDetector()
    # Derive sampling rate from camera target FPS
    sample_rate = float(getattr(cam, "target_fps", 30))
    left_smoother = ButterworthLowPass(sample_rate_hz=sample_rate)
    right_smoother = ButterworthLowPass(sample_rate_hz=sample_rate)
    # Separate Butterworth just for vertical intent (eye openness)
    vertical_smoother = ButterworthLowPass(sample_rate_hz=sample_rate)
    if not cam.start():
        print("Failed to open camera.")
        return

    try:
        last_t = time.perf_counter()
        frames = 0
        fps = 0.0
        mapper = None
        cursor = CursorController()
        overlay = None
        neutral_x = None
        neutral_y = None
        neutral_open = None
        gain_x = 3.0
        gain_y = 2.0
        # Calibration state (explicit user-driven)
        calibrator = MonocularCalibrator()
        CALIB_SEQUENCE = ["center", "left", "right", "up", "down"]
        calib_step = 0
        calibrating = True
        while True:
            ok, frame = cam.read()
            if not ok:
                break

            # Lazy-create mapper with current frame dimensions for visualization
            if mapper is None:
                h0, w0 = frame.shape[:2]
                mapper = CursorMapper(screen_width=int(w0), screen_height=int(h0))

            result = detector.detect(frame)
            # If detection fails or confidence is low, freeze cursor and show PAUSED status
            try:
                if (not result.success) or (getattr(result, "confidence", 0.0) < 0.6):
                    cursor.freeze()
                    try:
                        if overlay is not None:
                            overlay.hide()
                    except Exception:
                        pass
                    # Status: PAUSED – EYE NOT DETECTED (yellow)
                    try:
                        cv2.putText(
                            frame,
                            "STATUS: PAUSED \u2013 EYE NOT DETECTED",
                            (20, 120),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 255),
                            2,
                        )
                    except Exception:
                        pass
                    # Still show frame & handle keys, but skip mapping for this iteration
                    cv2.imshow("Smoothing Test", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:
                        break
                    continue
            except Exception:
                pass
            if result.success:
                try:
                    lx_sx = lx_sy = rx_sx = rx_sy = None
                    if result.left_center is not None:
                        lx, ly = result.left_center
                        lx_sx, lx_sy = left_smoother.filter(float(lx), float(ly))
                        cv2.circle(frame, (int(lx_sx), int(lx_sy)), 5, (0, 255, 0), -1)
                    if result.right_center is not None:
                        rx, ry = result.right_center
                        rx_sx, rx_sy = right_smoother.filter(float(rx), float(ry))
                        cv2.circle(frame, (int(rx_sx), int(rx_sy)), 5, (255, 0, 0), -1)

                    # Vertical intent smoothing from eye openness (right eye for now)
                    try:
                        if getattr(result, "right_openness", None) is not None:
                            eye_open = float(result.right_openness)  # normalized [0,1]
                            smooth_open = vertical_smoother.filter(eye_open, 0.0)[0]
                            # Optional overlay for debugging
                            cv2.putText(
                                frame,
                                f"Open: {smooth_open:.3f}",
                                (20, 60),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (255, 255, 255),
                                1,
                            )
                    except Exception:
                        pass

                    # Average both smoothed eyes
                    if lx_sx is not None and rx_sx is not None and lx_sy is not None and rx_sy is not None:
                        cx = (lx_sx + rx_sx) / 2.0
                        cy = (lx_sy + rx_sy) / 2.0

                        # Step 1 — Capture neutral gaze once (no UI yet)
                        if neutral_x is None or neutral_y is None:
                            neutral_x = cx
                            neutral_y = cy

                        # Step 2 — Use delta vs neutral to remove nose bias
                        dx = cx - float(neutral_x)
                        # Replace vertical delta with openness-based delta
                        # dy = cy - float(neutral_y)
                        try:
                            # smooth_open computed earlier when right_openness available
                            if 'smooth_open' in locals() and (neutral_open is None):
                                neutral_open = float(smooth_open)
                            if 'smooth_open' in locals() and (neutral_open is not None):
                                dy = float(smooth_open) - float(neutral_open)
                            else:
                                dy = 0.0
                        except Exception:
                            dy = 0.0

                        # Step 3 — Scale deltas into normalized screen space (temporary mapping)
                        nx = 0.5 + dx * gain_x / float(frame.shape[1])
                        ny = 0.5 + dy * gain_y / float(frame.shape[0])
                        # Clamp to [0,1]
                        nx = max(0.0, min(1.0, nx))
                        ny = max(0.0, min(1.0, ny))

                        # Visual aids
                        cv2.circle(frame, (int(cx), int(cy)), 5, (200, 200, 0), 1)
                        # Prefer calibrated mapping when available; fallback to simple mapper for display
                        if (not calibrating) and calibrator is not None and calibrator.scale_x is not None and calibrator.scale_y is not None:
                            sx, sy = calibrator.map(dx, dy)
                            try:
                                cv2.putText(frame, f"Mapped: {sx},{sy}", (20, 40),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                            except Exception:
                                pass
                            # After calibration: unfreeze and move OS cursor
                            try:
                                cursor.unfreeze()
                                cursor.move(int(sx), int(sy))
                            except Exception:
                                pass
                            # Update overlay crosshair when tracking active
                            try:
                                if overlay is not None:
                                    overlay.update(int(sx), int(sy))
                            except Exception:
                                pass
                            # Status: TRACKING (green)
                            try:
                                cv2.putText(
                                    frame,
                                    "STATUS: TRACKING",
                                    (20, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7,
                                    (0, 200, 0),
                                    2,
                                )
                            except Exception:
                                pass
                        elif mapper is not None:
                            sx, sy = mapper.map(nx, ny)
                            try:
                                cv2.putText(frame, f"Mapped: {sx},{sy}", (20, 40),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                            except Exception:
                                pass
                except Exception:
                    pass

            # FPS overlay (lightweight, no extra logic)
            frames += 1
            now = time.perf_counter()
            dt = now - last_t
                            # Instruction line (white text)
                            msg = f"CALIBRATION: LOOK {stage.upper()}  PRESS SPACE"
                            try:
                                cv2.putText(frame, msg, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            except Exception:
                                pass
                            # Status: CALIBRATION (STEP X / 5) in blue
                            try:
                                cv2.putText(
                                    frame,
                                    f"STATUS: CALIBRATION (STEP {calib_step + 1} / 5)",
                                    (20, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7,
                                    (255, 0, 0),
                                    2,
                                )
                            except Exception:
                                pass
                        else:
                            # When not calibrating, the TRACKING status is drawn in the mapping branch above.
            try:
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 200, 50), 2)
            except Exception:
                pass

            # Calibration overlay and optional mapping switch
            try:
                h0, w0 = frame.shape[:2]
                # Lazy-create overlay once screen size is known
                if overlay is None:
                    try:
                        overlay = GazeOverlay(screen_width=w0, screen_height=h0)
                        overlay.show()
                    except Exception:
                        overlay = None
                if calibrating:
                    # Always freeze before calibration complete
                    cursor.freeze()
                    stage = CALIB_SEQUENCE[calib_step]
                    msg = f"CALIBRATION: LOOK {stage.upper()}  press SPACE"
                    cv2.putText(frame, msg, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                else:
                    cv2.putText(frame, "TRACKING ACTIVE", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
            except Exception:
                pass

            cv2.imshow("Smoothing Test", frame)
            key = cv2.waitKey(1) & 0xFF
            # Global quit: 'q' freezes cursor and exits
            if key == ord('q'):
                try:
                    cursor.freeze()
                except Exception:
                    pass
                break
            if key == 27:
                break
            # SPACE captures current (dx, dy) for calibration
            if key == ord(' '):
                try:
                    if calibrating and 'dx' in locals() and 'dy' in locals():
                        name = CALIB_SEQUENCE[calib_step]
                        calibrator.add_sample(name, float(dx), float(dy))
                        calib_step += 1
                        if calib_step >= len(CALIB_SEQUENCE):
                            # Attempt compute; if invalid, reset and restart
                            ok = calibrator.compute(screen_width=w0, screen_height=h0)
                            if ok:
                                calibrating = False
                            else:
                                calibrator.reset()
                                calib_step = 0
                except Exception:
                    pass
            # 'S' saves calibration JSON
            if key in (ord('s'), ord('S')):
                try:
                    import os
                    cal_path = os.path.join(os.path.dirname(__file__), 'calibration.json')
                    calibrator.save_json(cal_path)
                    cv2.putText(frame, "Calibration saved", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                except Exception:
                    pass
            # 'L' loads calibration JSON
            if key in (ord('l'), ord('L')):
                try:
                    import os
                    cal_path = os.path.join(os.path.dirname(__file__), 'calibration.json')
                    loaded = MonocularCalibrator.load_json(cal_path)
                    # Replace current calibrator
                    calibrator = loaded
                    # Consider calibration complete if scales present
                    if calibrator.scale_x is not None and calibrator.scale_y is not None:
                        calibrating = False
                        cv2.putText(frame, "Calibration loaded", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                except Exception:
                    pass
            # Press 'c' to re-enter calibration mode
            if key in (ord('c'), ord('C')):
                try:
                    calib_step = 0
                    calibrator.reset()
                    calibrating = True
                except Exception:
                    pass
    finally:
        cam.stop()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            overlay.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
