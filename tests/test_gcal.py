from unittest.mock import Mock

from upb.gcal import (
    _build_event,
    _list_marked_events,
    _parse_due,
    _stable_id,
    get_or_create_calendar,
    sync_assignments,
)
from upb.models import Assignment


def test_stable_id_is_deterministic():
    a = Assignment(course="Math", title="Trabalho 1")
    b = Assignment(course="Math", title="Trabalho 1")
    assert _stable_id(a) == _stable_id(b)


def test_stable_id_differs_on_title():
    a = Assignment(course="Math", title="Trabalho 1")
    b = Assignment(course="Math", title="Trabalho 2")
    assert _stable_id(a) != _stable_id(b)


def test_parse_due_valid():
    a = Assignment(course="Math", title="T", due_at="2026-11-05T23:55:00+01:00")
    assert _parse_due(a) is not None


def test_parse_due_none():
    assert _parse_due(Assignment(course="Math", title="T")) is None


def test_parse_due_invalid():
    assert _parse_due(Assignment(course="Math", title="T", due_at="not a date")) is None


def test_build_event_fields():
    a = Assignment(
        course="Math",
        title="Trabalho 1",
        due_at="2026-11-05T23:55:00+01:00",
        description_text="Instruções",
        url="https://x/y",
    )
    ev = _build_event(a, lead_hours=2, color_id="11")
    assert ev["summary"] == "Math: Trabalho 1"
    assert ev["colorId"] == "11"
    assert ev["extendedProperties"]["private"]["upbId"] == _stable_id(a)
    assert "Instruções" in ev["description"]
    assert "https://x/y" in ev["description"]
    assert ev["start"]["dateTime"] == "2026-11-05T21:55:00+01:00"
    assert ev["end"]["dateTime"] == "2026-11-05T23:55:00+01:00"


def test_build_event_empty_course_uses_title_only():
    a = Assignment(course="", title="Trabalho", due_at="2026-11-05T23:55:00+01:00")
    assert _build_event(a)["summary"] == "Trabalho"


def test_list_marked_events_parses_and_paginates():
    service = Mock()
    service.events().list.return_value.execute.side_effect = [
        {
            "items": [
                {"id": "evt1", "extendedProperties": {"private": {"upbId": "upb-aaa"}}},
                # no upbId -> must be skipped
                {"id": "evt2", "extendedProperties": {"private": {"other": "x"}}},
            ],
            "nextPageToken": "tok2",
        },
        {
            "items": [
                {"id": "evt3", "extendedProperties": {"private": {"upbId": "upb-bbb"}}},
            ],
        },
    ]

    marked = _list_marked_events(service, "cal-1")

    assert marked == {"upb-aaa": "evt1", "upb-bbb": "evt3"}
    assert service.events().list.call_count == 2
    assert service.events().list.call_args_list[1].kwargs["pageToken"] == "tok2"

    # Regression: the list call must not pass the invalid privateExtendedProperty
    # filter (Google requires `name=value`; passing just the name returns a 400).
    for call in service.events().list.call_args_list:
        assert "privateExtendedProperty" not in call.kwargs


def test_sync_assignments_creates_updates_deletes():
    service = Mock()
    a = Assignment(course="Math", title="A", due_at="2099-01-01T23:55:00+00:00")
    b = Assignment(course="Math", title="B", due_at="2099-01-02T23:55:00+00:00")
    id_a = _stable_id(a)

    # Existing calendar has: an event for "a" (to update) and a stale one (to delete).
    service.events().list.return_value.execute.return_value = {
        "items": [
            {"id": "evt-a", "extendedProperties": {"private": {"upbId": id_a}}},
            {"id": "evt-old", "extendedProperties": {"private": {"upbId": "upb-gone"}}},
        ],
    }

    stats = sync_assignments(service, "cal-1", [a, b])

    assert stats == {"created": 1, "updated": 1, "deleted": 1}
    assert service.events().insert.call_count == 1
    assert service.events().patch.call_count == 1
    assert service.events().delete.call_count == 1

    assert service.events().patch.call_args.kwargs["eventId"] == "evt-a"
    assert service.events().insert.call_args.kwargs["body"]["summary"] == "Math: B"
    assert service.events().delete.call_args.kwargs["eventId"] == "evt-old"


def test_sync_assignments_skips_past():
    service = Mock()
    service.events().list.return_value.execute.return_value = {"items": []}
    past = Assignment(course="Math", title="Past", due_at="2000-01-01T23:55:00+00:00")

    stats = sync_assignments(service, "cal-1", [past])

    assert stats == {"created": 0, "updated": 0, "deleted": 0}
    service.events().insert.assert_not_called()


def test_sync_assignments_skips_missing_due():
    service = Mock()
    service.events().list.return_value.execute.return_value = {"items": []}
    a = Assignment(course="Math", title="NoDue")

    stats = sync_assignments(service, "cal-1", [a])

    assert stats == {"created": 0, "updated": 0, "deleted": 0}
    service.events().insert.assert_not_called()


def test_get_or_create_calendar_returns_existing():
    service = Mock()
    service.calendarList().list.return_value.execute.return_value = {
        "items": [
            {"summary": "Other", "id": "id-other"},
            {"summary": "IPB.Virtual", "id": "id-target"},
        ],
    }

    assert get_or_create_calendar(service, "IPB.Virtual") == "id-target"
    service.calendars().insert.assert_not_called()


def test_get_or_create_calendar_creates_when_missing():
    service = Mock()
    service.calendarList().list.return_value.execute.return_value = {"items": []}
    service.calendars().insert.return_value.execute.return_value = {"id": "id-new"}

    assert get_or_create_calendar(service, "IPB.Virtual") == "id-new"
    service.calendars().insert.assert_called_once()
