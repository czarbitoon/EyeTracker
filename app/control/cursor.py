from __future__ import annotations

"""
OS cursor controller.

This module provides a minimal `CursorController` with no mapping,
smoothing, or detection logic. It simply moves the OS cursor to
an absolute screen position using `pyautogui`.
"""

from typing import Optional

try:
    import pyautogui  # type: ignore
except Exception:
    pyautogui = None  # type: ignore


class CursorController:
    """Minimal OS cursor control.

    - `move(x, y)`: moves cursor to absolute screen position (integers).
    - `freeze()`: disables movement until unfrozen.

    No additional logic is included.
    """

    def __init__(self) -> None:
        self._frozen: bool = False

    def move(self, x: int, y: int) -> None:
        """Move the OS cursor to (x, y) in screen coordinates.

        If the controller is frozen, no movement occurs. If `pyautogui`
        is unavailable, the call is a no-op.
        """
        if self._frozen:
            return
        if pyautogui is None:
            return
        try:
            pyautogui.moveTo(int(x), int(y), duration=0.05)
        except Exception:
            # Swallow exceptions to keep control path simple
            pass

    def freeze(self) -> None:
        """Freeze cursor movement until explicitly unfrozen."""
        self._frozen = True

    def unfreeze(self) -> None:
        """Allow cursor movement again."""
        self._frozen = False
