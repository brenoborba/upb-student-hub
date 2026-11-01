"""Per-user sync: scrape Sakai, persist assignments, and mirror to Google Calendar.

Throttling strategy (protects the Sakai host under multi-user load):

1. a global token bucket around every Sakai HTTP request (``upb.client``),
2. a concurrency cap on simultaneous scrapes (this module),
3. a per-user minimum sync interval; manual syncs bypass it via ``force=True``.
"""
from __future__ import annotations

import logging
import threading

from sqlalchemy.orm import Session

from upb.assignments import scrape_assignments
from upb.client import SakaiClient
from upb.gcal import (
    DEFAULT_CALENDAR_NAME,
    build_credentials_from_refresh_token,
    stable_id,
    sync_with_credentials,
)
from upb.sites import discover_sites

from .. import security
from ..config import get_settings
from ..models import Assignment, GoogleCredential, SakaiCredential, SyncRun, User, utcnow

logger = logging.getLogger(__name__)

MIN_SYNC_INTERVAL_SECONDS = 15 * 60  # 15 minutes
MAX_CONCURRENT_SYNCS = 3

_sync_slots = threading.BoundedSemaphore(MAX_CONCURRENT_SYNCS)


def upsert_assignments(db: Session, user_id: int, assignments: list) -> None:
    """Replace the user's stored assignments with a fresh snapshot."""
    db.query(Assignment).filter_by(user_id=user_id).delete()
    for a in assignments:
        db.add(
            Assignment(
                user_id=user_id,
                stable_id=stable_id(a),
                course=a.course,
                title=a.title,
                open_at=a.open_at,
                due_at=a.due_at,
                status=a.status,
                status_label=a.status_label,
                description_text=a.description_text,
                url=a.url,
                attachments=[{"name": x.name, "url": x.url} for x in (a.attachments or [])],
            )
        )


def _skipped_run(db: Session, user: User, seconds_remaining: float) -> SyncRun:
    run = SyncRun(
        user_id=user.id,
        status="skipped",
        stats={"reason": "cooldown", "seconds_remaining": int(seconds_remaining)},
        finished_at=utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def run_sync(db: Session, user: User, include_past: bool = False, force: bool = False) -> SyncRun:
    """Scrape Sakai for ``user``, store results, and (optionally) sync Google Calendar."""
    if not force and user.last_scraped_at is not None:
        age = (utcnow() - user.last_scraped_at).total_seconds()
        if age < MIN_SYNC_INTERVAL_SECONDS:
            return _skipped_run(db, user, MIN_SYNC_INTERVAL_SECONDS - age)

    run = SyncRun(user_id=user.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        cred = db.query(SakaiCredential).filter_by(user_id=user.id).one()
        with _sync_slots:
            client = SakaiClient(cred.base_url)
            client.login(cred.username, security.decrypt(cred.password_enc))
            sites = discover_sites(client, favorites_only=True)
            assignments = scrape_assignments(client, sites, include_past=include_past)

        upsert_assignments(db, user.id, assignments)

        stats: dict = {"assignments": len(assignments), "calendar": None}
        gcred = db.query(GoogleCredential).filter_by(user_id=user.id).first()
        if gcred is not None:
            settings = get_settings()
            creds = build_credentials_from_refresh_token(
                security.decrypt(gcred.refresh_token_enc),
                settings.google_client_id,
                settings.google_client_secret,
            )
            stats["calendar"] = sync_with_credentials(
                creds,
                assignments,
                calendar_id=gcred.calendar_id or "",
                calendar_name=gcred.calendar_name or DEFAULT_CALENDAR_NAME,
                include_past=include_past,
            )

        user.last_scraped_at = utcnow()
        run.status = "success"
        run.stats = stats
        run.finished_at = utcnow()
        db.commit()
    except Exception as exc:  # noqa: BLE001 - record any sync failure for the user
        logger.exception("sync failed for user %s", user.id)
        db.rollback()
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = utcnow()
        db.add(run)
        db.commit()

    db.refresh(run)
    return run
