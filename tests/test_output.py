import json

from upb.models import Assignment
from upb.output import _to_dt, write_ics, write_json


def test_to_dt_valid():
    assert _to_dt("2026-11-05T23:55:00+00:00") is not None


def test_to_dt_none():
    assert _to_dt(None) is None


def test_to_dt_invalid():
    assert _to_dt("not a date") is None


def test_write_json(tmp_path):
    a = Assignment(course="Math", title="Trabalho 1")
    path = tmp_path / "out.json"
    write_json([a], str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["course"] == "Math"
    assert data[0]["assignment"] == "Trabalho 1"


def test_write_ics_creates_events(tmp_path):
    a = Assignment(
        course="Math",
        title="Trabalho 1",
        due_at="2026-11-05T23:55:00+00:00",
        description_text="Instruções",
        url="https://x/y",
    )
    path = tmp_path / "feed.ics"
    write_ics([a], str(path))
    text = path.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in text
    assert "BEGIN:VEVENT" in text
    assert "SUMMARY:Math: Trabalho 1" in text
    assert "DTSTART:20261105T215500Z" in text
    assert "DTEND:20261105T235500Z" in text
    assert "DESCRIPTION:Instruções" in text
    assert "URL:https://x/y" in text


def test_write_ics_skips_missing_due(tmp_path):
    a = Assignment(course="Math", title="No due")
    path = tmp_path / "feed.ics"
    write_ics([a], str(path))
    assert "BEGIN:VEVENT" not in path.read_text(encoding="utf-8")


def test_write_ics_empty_course_uses_title_only(tmp_path):
    a = Assignment(course="", title="Trabalho", due_at="2026-11-05T23:55:00+00:00")
    path = tmp_path / "feed.ics"
    write_ics([a], str(path))
    assert "SUMMARY:Trabalho" in path.read_text(encoding="utf-8")
