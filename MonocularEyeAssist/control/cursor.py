from __future__ import annotations

from typing import Tuple

import pyautogui


class Cursor:
    def __init__(self) -> None:
        try:
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0
        except Exception:
            pass

    def move_to(self, x: int, y: int) -> None:
        try:
            pyautogui.moveTo(int(x), int(y), duration=0)
        except Exception:
            pass
