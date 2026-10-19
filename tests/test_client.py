from types import SimpleNamespace

import pytest

from upb.client import USER_AGENT, LoginError, SakaiClient


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
