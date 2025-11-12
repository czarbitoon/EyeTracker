"""
Cursor control via pyautogui.

API:
- move_cursor(x, y): instant move

Notes:
- Built-in pyautogui pauses are disabled (PAUSE=0) and FAILSAFE is off.
"""
from __future__ import annotations

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover
    pyautogui = None


class CursorController:
    def __init__(self) -> None:
        if pyautogui:
            try:
                pyautogui.FAILSAFE = False
                pyautogui.PAUSE = 0  # disable built-in delays
            except Exception:
                pass

    def move_to(self, x: int, y: int) -> None:
        if pyautogui is None:
            return
        try:
            pyautogui.moveTo(int(x), int(y), duration=0)
        except Exception:
            pass

    # Public API ------------------------------------------------------
    def move_cursor(self, x: int, y: int) -> None:
        """Instantly move the OS cursor to (x,y)."""
        self.move_to(x, y)
        
