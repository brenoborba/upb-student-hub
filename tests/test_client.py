from types import SimpleNamespace

import pytest

from upb.client import USER_AGENT, LoginError, SakaiClient
from upb.ratelimit import RateLimiter


def test_client_init_strips_base_url():
    c = SakaiClient("https://virtual.ipb.pt/")
    assert c.base_url == "https://virtual.ipb.pt"
    assert c.session.headers["User-Agent"] == USER_AGENT


def test_client_get_url(monkeypatch):
    c = SakaiClient("https://virtual.ipb.pt")
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return SimpleNamespace(text="")

    monkeypatch.setattr(c.session, "get", fake_get)
    c.get("portal/site/abc")
    assert captured["url"] == "https://virtual.ipb.pt/portal/site/abc"


def _noop_get(*a, **k):
    return SimpleNamespace(text="")


def test_login_invalid_credentials(monkeypatch):
    c = SakaiClient("https://virtual.ipb.pt")
    monkeypatch.setattr(c.session, "get", _noop_get)
    monkeypatch.setattr(
        c.session,
        "post",
        lambda *a, **k: SimpleNamespace(
            url="https://virtual.ipb.pt/portal/xlogin?error=1", text=""
        ),
    )
    with pytest.raises(LoginError, match="invalid credentials"):
        c.login("u", "p")


def test_login_success_logged_in(monkeypatch):
    c = SakaiClient("https://virtual.ipb.pt")
    monkeypatch.setattr(c.session, "get", _noop_get)
    monkeypatch.setattr(
        c.session,
        "post",
        lambda *a, **k: SimpleNamespace(
            url="https://virtual.ipb.pt/portal", text='{"loggedIn": true}'
        ),
    )
    assert c.login("u", "p") is not None


def test_login_logged_out(monkeypatch):
    c = SakaiClient("https://virtual.ipb.pt")
    monkeypatch.setattr(c.session, "get", _noop_get)
    monkeypatch.setattr(
        c.session,
        "post",
        lambda *a, **k: SimpleNamespace(
            url="https://virtual.ipb.pt/portal/xlogin", text='"loggedIn": false'
        ),
    )
    with pytest.raises(LoginError, match="no authenticated session"):
        c.login("u", "p")


def test_login_portal_without_xlogin(monkeypatch):
    c = SakaiClient("https://virtual.ipb.pt")
    monkeypatch.setattr(c.session, "get", _noop_get)
    monkeypatch.setattr(
        c.session,
        "post",
        lambda *a, **k: SimpleNamespace(
            url="https://virtual.ipb.pt/portal", text="<html></html>"
        ),
    )
    assert c.login("u", "p") is not None


def test_login_unknown_status(monkeypatch):
    c = SakaiClient("https://virtual.ipb.pt")
    monkeypatch.setattr(c.session, "get", _noop_get)
    monkeypatch.setattr(
        c.session,
        "post",
        lambda *a, **k: SimpleNamespace(url="https://virtual.ipb.pt/somewhere", text=""),
    )
    with pytest.raises(LoginError, match="unknown"):
        c.login("u", "p")


def test_get_retries_on_503(monkeypatch):
    import upb.client as client_mod

    monkeypatch.setattr(client_mod.time, "sleep", lambda s: None)
    c = SakaiClient("https://virtual.ipb.pt", rate_limiter=RateLimiter(10000.0, 10000.0))

    calls = []

    class Resp:
        def __init__(self, status):
            self.status_code = status
            self.headers = {}

    def fake_get(url, **kwargs):
        calls.append(url)
        return Resp(503 if len(calls) == 1 else 200)

    monkeypatch.setattr(c.session, "get", fake_get)

    resp = c.get("portal/site/x")
    assert resp.status_code == 200
    assert len(calls) == 2


def test_get_respects_retry_after(monkeypatch):
    import upb.client as client_mod

    sleeps = []
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: sleeps.append(s))
    c = SakaiClient("https://virtual.ipb.pt", rate_limiter=RateLimiter(10000.0, 10000.0))

    class Resp:
        def __init__(self, status, retry_after=None):
            self.status_code = status
            self.headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}

    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return Resp(503, retry_after=7) if len(calls) == 1 else Resp(200)

    monkeypatch.setattr(c.session, "get", fake_get)

    resp = c.get("portal/site/x")
    assert resp.status_code == 200
    assert sleeps == [7.0]
