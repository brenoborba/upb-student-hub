import pytest

from upb import client as client_module
from upb.ratelimit import RateLimiter


@pytest.fixture(autouse=True)
def _fast_default_rate_limiter(monkeypatch):
    """Replace the shared Sakai rate limiter with an unlimited one in tests."""
    monkeypatch.setattr(
        client_module,
        "_default_rate_limiter",
        lambda: RateLimiter(10000.0, 10000.0),
    )
