from __future__ import annotations

import time
from collections import deque
from typing import Deque


class FPSMonitor:
    def __init__(self, window: int = 60) -> None:
        self.window = max(1, int(window))
        self._times: Deque[float] = deque(maxlen=self.window)
        self._last = None  # type: ignore[assignment]

    def tick(self) -> None:
        now = time.perf_counter()
        if self._last is not None:
            self._times.append(now - self._last)
        self._last = now

    def fps(self) -> float:
        if not self._times:
            return 0.0
        avg = sum(self._times) / float(len(self._times))
        if avg <= 0:
            return 0.0
        return 1.0 / avg
