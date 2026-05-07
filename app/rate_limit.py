import time
from collections import deque


class InMemoryRateLimiter:
    def __init__(self, *, limit_per_min: int, _now=time.monotonic):
        self.limit = limit_per_min
        self.window = 60.0
        self._buckets: dict[str, deque[float]] = {}
        self._now = _now

    def check(self, key: str) -> bool:
        now = self._now()
        bucket = self._buckets.setdefault(key, deque())
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True
