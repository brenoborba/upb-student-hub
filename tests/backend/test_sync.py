from upb.models import Assignment as UpbAssignment

from backend.app import security
from backend.app.models import Assignment, GoogleCredential, SakaiCredential, User, utcnow
from backend.app.services import sync as sync_mod


class FakeClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def login(self, username, password):
        self.username = username
        self.password = password


def _make_user(db):
    user = User(email="a@b.c", api_key="key123")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_cred(db, user):
    cred = SakaiCredential(
        user_id=user.id, username="user@ipb.pt", password_enc=security.encrypt("s3cret")
    )
    db.add(cred)
    db.commit()
    return cred


def test_run_sync_scrapes_and_stores(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)

    monkeypatch.setattr(sync_mod, "SakaiClient", FakeClient)
    monkeypatch.setattr(sync_mod, "discover_sites", lambda client, favorites_only=True: {"s1": "Course"})
    monkeypatch.setattr(
        sync_mod,
        "scrape_assignments",
        lambda client, sites, include_past=False: [
            UpbAssignment(course="Course", title="Trabalho 1", due_at="2099-01-01T23:55:00+00:00")
        ],
    )

    run = sync_mod.run_sync(db, user)

    assert run.status == "success"
    assert run.stats == {"assignments": 1, "calendar": None}

    rows = db.query(Assignment).filter_by(user_id=user.id).all()
    assert len(rows) == 1
    assert rows[0].title == "Trabalho 1"
    assert rows[0].course == "Course"


def test_run_sync_syncs_calendar_when_google_token(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)
    db.add(
        GoogleCredential(
            user_id=user.id, refresh_token_enc=security.encrypt("rt-123"), calendar_name="IPB.Virtual"
        )
    )
    db.commit()

    monkeypatch.setattr(sync_mod, "SakaiClient", FakeClient)
    monkeypatch.setattr(sync_mod, "discover_sites", lambda client, favorites_only=True: {"s1": "Course"})
    monkeypatch.setattr(sync_mod, "scrape_assignments", lambda client, sites, include_past=False: [])
    monkeypatch.setattr(sync_mod, "build_credentials_from_refresh_token", lambda rt, cid, csec: "creds")
    monkeypatch.setattr(
        sync_mod,
        "sync_with_credentials",
        lambda creds, assignments, calendar_id="", calendar_name="IPB.Virtual", include_past=False: {
            "created": 0, "updated": 0, "deleted": 0
        },
    )

    run = sync_mod.run_sync(db, user)

    assert run.status == "success"
    assert run.stats["calendar"] == {"created": 0, "updated": 0, "deleted": 0}


def test_run_sync_failure_records_error(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)

    class BoomClient(FakeClient):
        def login(self, username, password):
            raise RuntimeError("login failed")

    monkeypatch.setattr(sync_mod, "SakaiClient", BoomClient)

    run = sync_mod.run_sync(db, user)

    assert run.status == "failed"
    assert "login failed" in (run.error or "")


def test_run_sync_skips_within_cooldown(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)
    user.last_scraped_at = utcnow()
    db.commit()

    monkeypatch.setattr(sync_mod, "SakaiClient", FakeClient)

    def _boom(*a, **k):
        raise AssertionError("scraper should not run during cooldown")

    monkeypatch.setattr(sync_mod, "discover_sites", _boom)
    monkeypatch.setattr(sync_mod, "scrape_assignments", _boom)

    run = sync_mod.run_sync(db, user, force=False)
    assert run.status == "skipped"


def test_run_sync_force_bypasses_cooldown(monkeypatch, db):
    user = _make_user(db)
    _make_cred(db, user)
    user.last_scraped_at = utcnow()
    db.commit()

    monkeypatch.setattr(sync_mod, "SakaiClient", FakeClient)
    monkeypatch.setattr(sync_mod, "discover_sites", lambda client, favorites_only=True: {"s1": "Course"})
    monkeypatch.setattr(sync_mod, "scrape_assignments", lambda client, sites, include_past=False: [])

    run = sync_mod.run_sync(db, user, force=True)
    assert run.status == "success"
