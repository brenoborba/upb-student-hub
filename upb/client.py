import re
from urllib.parse import urljoin

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

LOGGED_IN_RE = re.compile(r'"loggedIn"\s*:\s*true')
LOGGED_OUT_RE = re.compile(r'"loggedIn"\s*:\s*false')


class LoginError(RuntimeError):
    """Raised when authentication against Sakai fails."""


class SakaiClient:
    """A thin HTTP client that keeps the Sakai session (JSESSIONID) alive."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
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

        url = urljoin(self.base_url + "/", "portal/xlogin")
        resp = self.session.post(
            url,
            data={"eid": username, "pw": password, "submit": "Log In"},
            allow_redirects=True,
            timeout=30,
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
        url = urljoin(self.base_url + "/", path)
        return self.session.get(url, timeout=30, **kwargs)
