"""Sakai bullhorn notifications ("Academic alerts") client.

Sakai exposes notifications as JSON via ``GET /direct/portal/bullhornAlerts.json``
(not the WebAPI ``/api``, which is disabled on many instances). Each alert
carries an ``event`` type, a human title, the course (``siteTitle``), the actor
(``fromDisplayName``), and a ``url`` to the underlying item.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

LISBON = ZoneInfo("Europe/Lisbon")

BULLHORN_ALERTS_PATH = "direct/portal/bullhornAlerts.json"
CLEAR_ALERT_PATH = "direct/portal/clearBullhornAlert"
CLEAR_ALL_PATH = "direct/portal/clearAllBullhornAlerts"

# Map Sakai event prefixes to a coarse category for grouping in the UI.
_CATEGORY_PREFIXES = [
    ("asn.", "assignment"),
    ("annc.", "announcement"),
    ("msg.", "message"),
    ("forums.", "forum"),
    ("forum.", "forum"),
    ("lesson", "lessons"),
    ("profile.", "social"),
    ("friend", "social"),
    ("wall", "social"),
    ("status", "social"),
    ("comment", "social"),
]


@dataclass
class Notification:
    notif_id: Optional[int] = None
    event: Optional[str] = None
    title: Optional[str] = None
    site_id: Optional[str] = None
    site_title: Optional[str] = None
    from_user: Optional[str] = None
    from_display_name: Optional[str] = None
    to_user: Optional[str] = None
    url: Optional[str] = None
    ref: Optional[str] = None
    event_date: Optional[str] = None
    formatted_event_date: Optional[str] = None
    deferred: bool = False

    @property
    def category(self) -> str:
        return classify(self.event)

    def to_dict(self) -> dict:
        return {
            "id": self.notif_id,
            "event": self.event,
            "category": self.category,
            "title": self.title,
            "site_id": self.site_id,
            "site_title": self.site_title,
            "from_user": self.from_user,
            "from_display_name": self.from_display_name,
            "to_user": self.to_user,
            "url": self.url,
            "ref": self.ref,
            "event_date": self.event_date,
            "formatted_event_date": self.formatted_event_date,
            "deferred": self.deferred,
        }


def classify(event: Optional[str]) -> str:
    e = (event or "").lower()
    for prefix, category in _CATEGORY_PREFIXES:
        if e.startswith(prefix):
            return category
    return "other"


def _epoch_to_iso(epoch_second) -> Optional[str]:
    if epoch_second is None:
        return None
    try:
        return datetime.fromtimestamp(int(epoch_second), tz=LISBON).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def parse_alert(raw: dict) -> Notification:
    event_date = raw.get("eventDate") or {}
    return Notification(
        notif_id=raw.get("id"),
        event=raw.get("event"),
        title=raw.get("title"),
        site_id=raw.get("siteId"),
        site_title=raw.get("siteTitle"),
        from_user=raw.get("fromUser"),
        from_display_name=raw.get("fromDisplayName"),
        to_user=raw.get("toUser"),
        url=raw.get("url"),
        ref=raw.get("ref"),
        event_date=_epoch_to_iso(event_date.get("epochSecond")),
        formatted_event_date=raw.get("formattedEventDate"),
        deferred=bool(raw.get("deferred")),
    )


def deduplicate(notifications: list[Notification]) -> list[Notification]:
    """Collapse notifications that point at the same underlying item (``ref``).

    Sakai re-issues an alert each time an item is updated, so one assignment can
    appear multiple times with different alert ids. Keep only the most recent
    alert per ``ref``; alerts without a ``ref`` are always kept. The result is
    ordered most-recent-first by alert id.
    """
    latest: dict[str, Notification] = {}
    unrefed: list[Notification] = []
    for n in notifications:
        if not n.ref:
            unrefed.append(n)
            continue
        current = latest.get(n.ref)
        if current is None or (n.notif_id or 0) > (current.notif_id or 0):
            latest[n.ref] = n
    result = list(latest.values()) + unrefed
    result.sort(key=lambda n: n.notif_id or 0, reverse=True)
    return result


def fetch_notifications(client, dedupe: bool = True) -> list[Notification]:
    """Return the user's current (unread) bullhorn alerts."""
    data = client.get(BULLHORN_ALERTS_PATH).json()
    notifications = [parse_alert(a) for a in data.get("alerts", [])]
    if dedupe:
        notifications = deduplicate(notifications)
    return notifications


def clear_notification(client, notif_id) -> None:
    """Mark a single alert as read (removes it from Sakai's bullhorn)."""
    client.get(CLEAR_ALERT_PATH, params={"id": notif_id})


def clear_all_notifications(client) -> None:
    client.get(CLEAR_ALL_PATH)
