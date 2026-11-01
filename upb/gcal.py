"""Google Calendar sync for UPB assignments.

Replaces the static ``feed.ics`` export with a live, idempotent sync: for each
assignment we create/update a calendar event (red, with reminders) and delete
events whose assignment has disappeared (e.g. submitted, removed, or past when
``include_past=False``). Events are matched across runs via a stable id stored
in the event's private extended properties.

Google API client libraries are imported lazily so the rest of the package
imports and runs without them installed.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta

# Keep the same visible window as the .ics export (see upb/output.py).
EVENT_LEAD_HOURS = 2

# Google Calendar colorId for "tomato" (red).
RED_COLOR_ID = "11"

# Reminders are relative to the event *start* (due - EVENT_LEAD_HOURS).
REMINDER_OVERRIDES = [
    {"method": "popup", "minutes": 1440},  # ~1 day before the deadline
    {"method": "popup", "minutes": 120},  # ~2h before the deadline window
]

SCOPES = ["https://www.googleapis.com/auth/calendar"]

DEFAULT_CALENDAR_NAME = "IPB.Virtual"

_EXTENDED_PROPERTY = "upbId"


class GcalError(RuntimeError):
    """Raised when Google Calendar sync cannot proceed."""


def _stable_id(assignment) -> str:
    key = f"{assignment.course or ''}\x00{assignment.title or ''}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"upb-{digest}"


def stable_id(assignment) -> str:
    """Public stable identifier for an assignment, shared by sync and storage."""
    return _stable_id(assignment)


def _parse_due(assignment):
    if not assignment.due_at:
        return None
    try:
        return datetime.fromisoformat(assignment.due_at)
    except ValueError:
        return None


def _build_event(assignment, lead_hours: int = EVENT_LEAD_HOURS, color_id: str = RED_COLOR_ID) -> dict:
    """Build a Calendar API event body for an assignment (assumes a valid due date)."""
    due = _parse_due(assignment)
    start = due - timedelta(hours=lead_hours)

    title = f"{assignment.course}: {assignment.title}" if assignment.course else assignment.title
    desc = assignment.description_text or ""
    if assignment.url:
        desc = (desc + "\n\n" if desc else "") + assignment.url

    event = {
        "summary": title,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": due.isoformat()},
        "colorId": color_id,
        "reminders": {"useDefault": False, "overrides": REMINDER_OVERRIDES},
        "extendedProperties": {"private": {_EXTENDED_PROPERTY: _stable_id(assignment)}},
    }
    if desc:
        event["description"] = desc
    return event


def _import_google():
    try:
        from google.auth.transport.requests import Request  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from googleapiclient.discovery import build  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise GcalError(
            "Google Calendar support is not installed. Run "
            "`pip install google-api-python-client google-auth-oauthlib`."
        ) from exc
    return Request, Credentials, build, InstalledAppFlow


def get_credentials(credentials_path: str, token_path: str, scopes=None):
    """Load (and refresh, or authorize) OAuth credentials, persisting to ``token_path``."""
    Request, Credentials, _build, InstalledAppFlow = _import_google()
    scopes = scopes or SCOPES

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise GcalError(
                    f"OAuth client credentials not found at '{credentials_path}'. "
                    "Create an OAuth 2.0 Client ID (Desktop app) in Google Cloud "
                    "Console and save it as credentials.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


def build_service(creds):
    _Request, _Credentials, build, _InstalledAppFlow = _import_google()
    return build("calendar", "v3", credentials=creds)


def build_credentials_from_refresh_token(refresh_token: str, client_id: str, client_secret: str, scopes=None):
    """Build OAuth credentials from a stored refresh token (no interactive flow)."""
    _Request, Credentials, _build, _InstalledAppFlow = _import_google()
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes or SCOPES,
    )


def get_or_create_calendar(service, name: str) -> str:
    """Return the id of a secondary calendar named ``name``, creating it if needed."""
    page_token = None
    while True:
        resp = service.calendarList().list(pageToken=page_token).execute()
        for entry in resp.get("items", []):
            if entry.get("summary") == name:
                return entry["id"]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    created = service.calendars().insert(body={"summary": name}).execute()
    return created["id"]


def _list_marked_events(service, calendar_id: str) -> dict:
    """Return {upbId: eventId} for every event we previously created in the calendar."""
    marked: dict[str, str] = {}
    page_token = None
    while True:
        resp = (
            service.events()
            .list(
                calendarId=calendar_id,
                singleEvents=True,
                pageToken=page_token,
            )
            .execute()
        )
        for item in resp.get("items", []):
            private = (item.get("extendedProperties", {}) or {}).get("private", {}) or {}
            upb_id = private.get(_EXTENDED_PROPERTY)
            if upb_id:
                marked[upb_id] = item["id"]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return marked


def sync_assignments(service, calendar_id: str, assignments, lead_hours: int = EVENT_LEAD_HOURS,
                     color_id: str = RED_COLOR_ID, include_past: bool = False) -> dict:
    """Create/update/delete calendar events to match ``assignments``.

    Returns ``{"created": int, "updated": int, "deleted": int}``.
    """
    now = datetime.now().astimezone()
    wanted: dict[str, object] = {}
    for a in assignments:
        due = _parse_due(a)
        if due is None:
            continue
        if not include_past and due < now:
            continue
        wanted[_stable_id(a)] = a

    existing = _list_marked_events(service, calendar_id)

    created = updated = deleted = 0
    for upb_id, a in wanted.items():
        body = _build_event(a, lead_hours=lead_hours, color_id=color_id)
        if upb_id in existing:
            service.events().patch(calendarId=calendar_id, eventId=existing[upb_id], body=body).execute()
            updated += 1
        else:
            service.events().insert(calendarId=calendar_id, body=body).execute()
            created += 1

    for upb_id, event_id in existing.items():
        if upb_id not in wanted:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            deleted += 1

    return {"created": created, "updated": updated, "deleted": deleted}


def sync_with_credentials(creds, assignments, calendar_id: str = "",
                          calendar_name: str = DEFAULT_CALENDAR_NAME,
                          lead_hours: int = EVENT_LEAD_HOURS, include_past: bool = False) -> dict:
    """Sync ``assignments`` using already-built OAuth ``creds``."""
    service = build_service(creds)
    target = calendar_id or get_or_create_calendar(service, calendar_name)
    return sync_assignments(service, target, assignments, lead_hours=lead_hours, include_past=include_past)


def sync_to_calendar(assignments, credentials_path: str, token_path: str,
                     calendar_id: str = "", calendar_name: str = DEFAULT_CALENDAR_NAME,
                     lead_hours: int = EVENT_LEAD_HOURS, include_past: bool = False) -> dict:
    """End-to-end sync from credential files: authorize, resolve calendar, then sync."""
    creds = get_credentials(credentials_path, token_path)
    return sync_with_credentials(
        creds, assignments, calendar_id=calendar_id, calendar_name=calendar_name,
        lead_hours=lead_hours, include_past=include_past,
    )
