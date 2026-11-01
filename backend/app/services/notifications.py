"""Fetch and store Sakai bullhorn notifications for a user."""
from __future__ import annotations

from sqlalchemy.orm import Session

from upb.notifications import clear_notification, fetch_notifications

from ..models import SakaiNotification, User
from .sync import get_sakai_client


def store_notifications(db: Session, user_id: int, notifications: list) -> None:
    """Upsert notifications by Sakai ``notif_id``, preserving the ``read`` flag."""
    for n in notifications:
        if n.notif_id is None:
            continue
        row = (
            db.query(SakaiNotification)
            .filter_by(user_id=user_id, notif_id=n.notif_id)
            .first()
        )
        if row is None:
            row = SakaiNotification(user_id=user_id, notif_id=n.notif_id)
            db.add(row)
        row.event = n.event or ""
        row.category = n.category
        row.title = n.title
        row.site_id = n.site_id
        row.site_title = n.site_title
        row.from_user = n.from_user
        row.from_display_name = n.from_display_name
        row.to_user = n.to_user
        row.url = n.url
        row.ref = n.ref
        row.event_date = n.event_date
        row.formatted_event_date = n.formatted_event_date
    db.commit()


def sync_notifications(db: Session, user: User) -> int:
    """Fetch the user's notifications and store them; returns the count fetched."""
    client = get_sakai_client(db, user)
    notifications = fetch_notifications(client)
    store_notifications(db, user.id, notifications)
    return len(notifications)


def mark_read(db: Session, user: User, row: SakaiNotification) -> None:
    """Mark a stored notification as read (and clear it from Sakai's bullhorn)."""
    if row.read:
        return
    client = get_sakai_client(db, user)
    clear_notification(client, row.notif_id)
    row.read = True
    db.commit()
