from backend.app import security
from backend.app.models import SakaiCredential, SakaiNotification, User
from backend.app.services import notifications as notif_mod
from upb.notifications import Notification


class FakeClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def login(self, username, password):
        pass


def _make_user(db):
    user = User(email="n@b.c", api_key="key123")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_cred(db, user):
    db.add(
        SakaiCredential(
            user_id=user.id, username="u@ipb.pt", password_enc=security.encrypt("pw")
        )
    )
    db.commit()


def _notif(**kwargs):
    defaults = dict(
        notif_id=1,
        event="annc.new",
        title="Hello",
        site_id=None,
        site_title=None,
        from_user=None,
        from_display_name=None,
        to_user=None,
        url=None,
        ref=None,
        event_date=None,
        formatted_event_date=None,
        body=None,
        body_text=None,
    )
    defaults.update(kwargs)
    return Notification(**defaults)


def test_sync_notifications_stores(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)

    monkeypatch.setattr(notif_mod, "get_sakai_client", lambda db, u: FakeClient("x"))
    monkeypatch.setattr(notif_mod, "fetch_notifications", lambda client: [_notif()])

    count = notif_mod.sync_notifications(db, user)

    assert count == 1
    rows = db.query(SakaiNotification).filter_by(user_id=user.id).all()
    assert len(rows) == 1
    assert rows[0].category == "announcement"
    assert rows[0].title == "Hello"
    assert rows[0].read is False


def test_sync_notifications_is_idempotent(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)

    monkeypatch.setattr(notif_mod, "get_sakai_client", lambda db, u: FakeClient("x"))
    monkeypatch.setattr(notif_mod, "fetch_notifications", lambda client: [_notif(notif_id=2)])

    notif_mod.sync_notifications(db, user)
    notif_mod.sync_notifications(db, user)

    assert db.query(SakaiNotification).filter_by(user_id=user.id).count() == 1


def test_mark_read(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)
    row = SakaiNotification(
        user_id=user.id, notif_id=3, event="annc.new", category="announcement", title="T"
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    cleared = []
    monkeypatch.setattr(notif_mod, "get_sakai_client", lambda db, u: FakeClient("x"))
    monkeypatch.setattr(notif_mod, "clear_notification", lambda client, nid: cleared.append(nid))

    notif_mod.mark_read(db, user, row)

    assert cleared == [3]
    assert row.read is True


def test_mark_read_is_noop_if_already_read(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)
    row = SakaiNotification(
        user_id=user.id, notif_id=4, event="annc.new", category="announcement", title="T", read=True
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    cleared = []
    monkeypatch.setattr(notif_mod, "clear_notification", lambda client, nid: cleared.append(nid))

    notif_mod.mark_read(db, user, row)

    assert cleared == []


def test_list_notifications_api(client, db):
    u = client.post("/api/users", json={"email": "nn@x.y"}).json()
    h = {"X-API-Key": u["api_key"]}

    db.add(
        SakaiNotification(
            user_id=u["id"], notif_id=5, event="annc.new", category="announcement", title="Hi"
        )
    )
    db.commit()

    r = client.get(f"/api/users/{u['id']}/notifications", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Hi"
    assert data[0]["read"] is False


def test_sync_notifications_stores_body(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)

    monkeypatch.setattr(notif_mod, "get_sakai_client", lambda db, u: FakeClient("x"))
    monkeypatch.setattr(
        notif_mod,
        "fetch_notifications",
        lambda client: [_notif(notif_id=9, body="<p>Hello</p>", body_text="Hello")],
    )

    notif_mod.sync_notifications(db, user)

    row = db.query(SakaiNotification).filter_by(user_id=user.id, notif_id=9).one()
    assert row.body == "<p>Hello</p>"
    assert row.body_text == "Hello"
