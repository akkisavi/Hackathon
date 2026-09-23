"""In-memory sliding-window rate limiter (login / forgot-password)."""
from __future__ import annotations

import threading
from collections import defaultdict
from time import time


class SlidingWindowLimiter:
    def __init__(self, max_hits: int, window_s: int):
        self.max_hits = max_hits
        self.window_s = window_s
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Record an attempt. Return True if the request is allowed."""
        now = time()
        with self._lock:
            recent = [t for t in self._hits[key] if now - t < self.window_s]
            if len(recent) >= self.max_hits:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# 5 failed/attempted logins per identity per 15 min; 3 forgot-password per 15 min.
login_limiter = SlidingWindowLimiter(5, 15 * 60)
forgot_limiter = SlidingWindowLimiter(3, 15 * 60)
