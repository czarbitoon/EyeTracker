from __future__ import annotations

import cv2  # type: ignore
from app.tracking.camera import Camera
from app.tracking.detection import EyeDetector


def main() -> None:
    cam = Camera()
    detector = EyeDetector()
    if not cam.start():
        print("Failed to open camera.")
        return

    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                break

            result = detector.detect(frame)
            if result.success:
                for (x, y) in result.eye_centers:
                    try:
                        cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
                    except Exception:
                        pass

            cv2.imshow("Detection Test", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        cam.stop()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


if __name__ == "__main__":
    main()
