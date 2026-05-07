import time
from app.rate_limit import InMemoryRateLimiter


def test_allows_under_limit():
    rl = InMemoryRateLimiter(limit_per_min=3)
    for _ in range(3):
        assert rl.check("k") is True


def test_blocks_over_limit():
    rl = InMemoryRateLimiter(limit_per_min=2)
    rl.check("k")
    rl.check("k")
    assert rl.check("k") is False


def test_window_resets():
    rl = InMemoryRateLimiter(limit_per_min=1, _now=lambda: 0.0)
    assert rl.check("k") is True
    assert rl.check("k") is False
    rl._now = lambda: 61.0
    assert rl.check("k") is True
