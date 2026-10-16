from __future__ import annotations

import json
from datetime import datetime, timedelta

from ics import Calendar, Event

# Each calendar event covers the window [due - EVENT_LEAD_HOURS, due].
EVENT_LEAD_HOURS = 2


def _to_dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def write_json(assignments: list, path: str = "assignments.json") -> None:
    data = [a.to_dict() for a in assignments]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_ics(assignments: list, path: str = "feed.ics") -> None:
    cal = Calendar()
    for a in assignments:
        dt = _to_dt(a.due_at)
        if dt is None:
            continue

        event = Event()
        event.name = f"{a.course}: {a.title}" if a.course else a.title
        event.begin = dt - timedelta(hours=EVENT_LEAD_HOURS)
        event.end = dt

        desc = a.description_text or ""
        if a.url:
            desc = (desc + "\n\n" if desc else "") + a.url
        if desc:
            event.description = desc
        if a.url:
            event.url = a.url

        cal.events.add(event)

    with open(path, "w", encoding="utf-8") as f:
        f.write(cal.serialize())
