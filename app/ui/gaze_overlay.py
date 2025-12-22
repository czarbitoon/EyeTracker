from __future__ import annotations

"""
Gaze overlay window for Windows.

Creates a borderless, transparent, always-on-top, click-through window that
renders a crosshair at given screen coordinates. No gaze logic lives here.

Methods:
- show()
- hide()
- update(x, y)
- close()

Implementation notes:
- Uses tkinter for simplicity
- Click-through achieved via Win32 extended window styles (WS_EX_LAYERED | WS_EX_TRANSPARENT)
- Transparency via a colorkey on the window using -transparentcolor
"""

import ctypes
import sys
import threading
import tkinter as tk
from typing import Optional, Tuple

# Win32 constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
LWA_COLORKEY = 0x00000001

# Choose a colorkey that won't be used for the crosshair
TRANSPARENT_COLOR = "magenta"


class GazeOverlay:
    def __init__(self, screen_width: int | None = None, screen_height: int | None = None, crosshair_color: str = "red") -> None:
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._crosshair_color = crosshair_color
        self._shown = False
        self._thread: Optional[threading.Thread] = None
        self._pos: Tuple[int, int] = (0, 0)
        self._lock = threading.Lock()
        self._screen_w = screen_width
        self._screen_h = screen_height

    def _ensure_window(self) -> None:
        if self._root is not None:
            return
        root = tk.Tk()
        root.overrideredirect(True)  # borderless
        root.attributes("-topmost", True)  # always-on-top
        try:
            root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        except Exception:
            pass

        # Fullscreen covering window (transparent background)
        # Place at (0,0) covering the primary screen
        screen_w = self._screen_w or root.winfo_screenwidth()
        screen_h = self._screen_h or root.winfo_screenheight()
        root.geometry(f"{screen_w}x{screen_h}+0+0")

        canvas = tk.Canvas(root, width=screen_w, height=screen_h, highlightthickness=0)
        canvas.configure(bg=TRANSPARENT_COLOR)
        canvas.pack(fill=tk.BOTH, expand=True)

        self._root = root
        self._canvas = canvas

        # Make click-through using Win32 extended styles
        try:
            hwnd = ctypes.windll.user32.GetParent(self._root.winfo_id())
            if hwnd == 0:
                hwnd = self._root.winfo_id()
            exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            exstyle |= WS_EX_LAYERED | WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)
            # Set layered window attributes to accept colorkey transparency
            # This improves transparency behavior for some configurations
            ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_COLORKEY)
        except Exception:
            # Non-fatal; window will still be borderless and topmost
            pass

    def _draw_crosshair(self, x: int, y: int) -> None:
        if self._canvas is None:
            return
        c = self._canvas
        c.delete("crosshair")
        size = 12
        # Horizontal and vertical lines
        c.create_line(x - size, y, x + size, y, fill=self._crosshair_color, width=2, tags="crosshair")
        c.create_line(x, y - size, x, y + size, fill=self._crosshair_color, width=2, tags="crosshair")
        # Center dot
        c.create_oval(x - 3, y - 3, x + 3, y + 3, outline=self._crosshair_color, fill=self._crosshair_color, tags="crosshair")

    def show(self) -> None:
        self._ensure_window()
        if self._shown:
            return
        self._shown = True
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def hide(self) -> None:
        self._shown = False
        if self._root is not None:
            try:
                self._root.withdraw()
            except Exception:
                pass

    def update(self, x: int, y: int) -> None:
        with self._lock:
            self._pos = (int(x), int(y))
        # Schedule draw on UI thread
        if self._root is not None:
            try:
                self._root.after(0, self._apply_update)
            except Exception:
                pass

    def _apply_update(self) -> None:
        with self._lock:
            x, y = self._pos
        self._draw_crosshair(x, y)
        if self._shown and self._root is not None:
            try:
                self._root.deiconify()
            except Exception:
                pass

    def close(self) -> None:
        self._shown = False
        try:
            if self._root is not None:
                self._root.destroy()
        except Exception:
            pass
        self._root = None
        self._canvas = None

    def _run_loop(self) -> None:
        if self._root is None:
            return
        try:
            # Keep the window responsive
            self._root.mainloop()
        except Exception:
            pass


if __name__ == "__main__":
    # Minimal manual test
    ov = GazeOverlay()
    ov.show()
    import time
    for i in range(50):
        ov.update(100 + i * 10, 100 + i * 5)
        time.sleep(0.05)
    ov.close()
