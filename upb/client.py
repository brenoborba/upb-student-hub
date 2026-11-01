from __future__ import annotations

import re
import threading
import time
from urllib.parse import urljoin

import requests

from upb.ratelimit import RateLimiter

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

LOGGED_IN_RE = re.compile(r'"loggedIn"\s*:\s*true')
LOGGED_OUT_RE = re.compile(r'"loggedIn"\s*:\s*false')

# Global politeness budget for the Sakai host, shared by every SakaiClient (so
# the single-user CLI and the multi-user backend throttle against one bucket).
DEFAULT_REQUESTS_PER_MINUTE = 30
DEFAULT_BURST = 5
DEFAULT_MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 503}

_default_limiter = None
_default_limiter_lock = threading.Lock()


def _default_rate_limiter() -> RateLimiter:
    global _default_limiter
    if _default_limiter is None:
        with _default_limiter_lock:
            if _default_limiter is None:
                _default_limiter = RateLimiter(
                    DEFAULT_REQUESTS_PER_MINUTE / 60.0, DEFAULT_BURST
                )
    return _default_limiter


def _retry_delay(resp, attempt: int) -> float:
    headers = getattr(resp, "headers", None)
    retry_after = headers.get("Retry-After") if headers else None
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except (TypeError, ValueError):
            pass
    return min(2 ** attempt, 30.0)  # exponential backoff 1s, 2s, 4s… capped at 30s


class LoginError(RuntimeError):
    """Raised when authentication against Sakai fails."""


class SakaiClient:
    """A thin HTTP client that keeps the Sakai session (JSESSIONID) alive.

    Every request is rate-limited through a shared token bucket, so load on the
    Sakai host stays bounded no matter how many users are being synced.
    """

    def __init__(
        self,
        base_url: str,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.base_url = base_url.rstrip("/")
        self.rate_limiter = (
            rate_limiter if rate_limiter is not None else _default_rate_limiter()
        )
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
            }
        )

    def login(self, username: str, password: str):
        # Warm the session: some deployments set a cookie on first visit.
        try:
            self.get("portal")
        except requests.RequestException:
            pass

        resp = self.post(
            "portal/xlogin",
            data={"eid": username, "pw": password, "submit": "Log In"},
            allow_redirects=True,
        )

        if "xlogin" in resp.url and "error" in resp.url:
            raise LoginError(
                "Login failed: invalid credentials (or MFA is now required). "
                "Check UPB_USERNAME / UPB_PASSWORD."
            )
        if LOGGED_IN_RE.search(resp.text):
            return resp
        if LOGGED_OUT_RE.search(resp.text) or "xlogin" in resp.url:
            raise LoginError("Login failed: no authenticated session was established.")
        if "/portal" in resp.url and "xlogin" not in resp.url:
            return resp
        raise LoginError(
            "Login status unknown. Re-run with --debug to inspect the page."
        )

    def get(self, path: str, **kwargs):
        return self._request("get", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self._request("post", path, **kwargs)

    def _request(self, method: str, path: str, **kwargs):
        url = urljoin(self.base_url + "/", path)
        for attempt in range(self.max_retries + 1):
            self.rate_limiter.acquire()
            resp = getattr(self.session, method)(url, timeout=30, **kwargs)
            if (
                getattr(resp, "status_code", 200) in RETRYABLE_STATUS
                and attempt < self.max_retries
            ):
                time.sleep(_retry_delay(resp, attempt))
                continue
            return resp
