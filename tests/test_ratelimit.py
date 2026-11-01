import time as _time

import pytest

from upb.ratelimit import RateLimiter


def test_raises_on_nonpositive_rate():
    with pytest.raises(ValueError):
        RateLimiter(0)


def test_burst_is_immediate():
    limiter = RateLimiter(rate=1000.0, capacity=3.0)
    start = _time.monotonic()
    for _ in range(3):
        limiter.acquire()
    assert _time.monotonic() - start < 0.5


def test_refills_over_time(monkeypatch):
    import upb.ratelimit as rl

    clock = {"t": 0.0}
    monkeypatch.setattr(rl.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(rl.time, "sleep", lambda s: None)

    limiter = RateLimiter(rate=10.0, capacity=2.0)
    limiter.acquire()  # 2 -> 1
    limiter.acquire()  # 1 -> 0

    clock["t"] = 0.2  # +2 tokens at rate 10/s
    limiter.acquire()  # succeeds without sleeping
