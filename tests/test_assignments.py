from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from bs4 import BeautifulSoup

from upb.assignments import (
    _cell_date,
    _cell_status,
    _clean_text,
    _extract_attachments,
    _find_description_el,
    _href_matches_assignment,
    _map_columns,
    find_assignments_tool_link,
    find_dates,
    first_date,
    is_past,
    normalize_status,
    parse_assignment_detail,
    parse_assignment_list,
    parse_datetime,
    scrape_assignments,
)

LISBON = ZoneInfo("Europe/Lisbon")


# --------------------------------------------------------------------------- #
# Date detection
# --------------------------------------------------------------------------- #
def test_find_dates_iso():
    assert find_dates("2026-10-01 09:00") == ["2026-10-01 09:00"]


def test_find_dates_multiple():
    text = "Abertura 2026-10-01 09:00 limite 2026-11-05 23:55"
    assert find_dates(text) == ["2026-10-01 09:00", "2026-11-05 23:55"]


def test_find_dates_portuguese_formats():
    assert find_dates("01/10/2026") == ["01/10/2026"]
    assert find_dates("01-10-2026") == ["01-10-2026"]
    assert find_dates("01.10.2026") == ["01.10.2026"]


def test_find_dates_none():
    assert find_dates("no dates here") == []


# --------------------------------------------------------------------------- #
# Datetime parsing
# --------------------------------------------------------------------------- #
def test_parse_datetime_iso_with_seconds():
    assert parse_datetime("2026-10-01 09:00:00") == "2026-10-01T09:00:00+01:00"


def test_parse_datetime_iso_without_seconds():
    assert parse_datetime("2026-10-01 09:00") == "2026-10-01T09:00:00+01:00"


def test_parse_datetime_winter_no_dst():
    assert parse_datetime("2026-11-05 23:55:00") == "2026-11-05T23:55:00+00:00"


def test_parse_datetime_default_time_applied():
    assert (
        parse_datetime("2026-10-01", default_time="23:55")
        == "2026-10-01T23:55:00+01:00"
    )


def test_parse_datetime_default_not_override_explicit():
    assert (
        parse_datetime("2026-10-01 09:00", default_time="23:55")
        == "2026-10-01T09:00:00+01:00"
    )


def test_parse_datetime_dmy():
    assert parse_datetime("01-10-2026 09:00:00") == "2026-10-01T09:00:00+01:00"


def test_parse_datetime_slash():
    assert parse_datetime("01/10/2026 09:00") == "2026-10-01T09:00:00+01:00"


def test_parse_datetime_dotted():
    assert parse_datetime("01.10.2026") == "2026-10-01T00:00:00+01:00"


def test_parse_datetime_nbsp():
    assert parse_datetime("2026-10-01\xa009:00") == "2026-10-01T09:00:00+01:00"


def test_parse_datetime_invalid():
    assert parse_datetime("garbage") is None


def test_first_date():
    assert first_date("2026-10-01 09:00") == "2026-10-01T09:00:00+01:00"


def test_first_date_none():
    assert first_date("nothing") is None


# --------------------------------------------------------------------------- #
# is_past
# --------------------------------------------------------------------------- #
def test_is_past_true():
    now = datetime(2026, 6, 1, tzinfo=LISBON)
    assert is_past("2026-01-01T00:00:00+00:00", now=now) is True


def test_is_past_false():
    now = datetime(2026, 6, 1, tzinfo=LISBON)
    assert is_past("2026-12-01T00:00:00+00:00", now=now) is False


def test_is_past_none():
    assert is_past(None) is False


def test_is_past_invalid():
    assert is_past("not-a-date") is False


# --------------------------------------------------------------------------- #
# Status normalization
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text,expected",
    [
        ("Entregue", "submitted"),
        ("Submetido", "submitted"),
        ("Não iniciado", "not_started"),
        ("Aberto", "open"),
        ("Aberta", "open"),
        ("Devolvido", "returned"),
        ("Classificado", "graded"),
        ("Fechado", "closed"),
    ],
)
def test_normalize_status_known(text, expected):
    status, label = normalize_status(text)
    assert status == expected
    assert label == text


def test_normalize_status_unknown():
    status, label = normalize_status("Whatever")
    assert status is None
    assert label == "Whatever"


def test_normalize_status_case_insensitive():
    status, _ = normalize_status("ENTREGUE")
    assert status == "submitted"


# --------------------------------------------------------------------------- #
# Assignment link matching
# --------------------------------------------------------------------------- #
def test_href_matches_assignment_true():
    assert _href_matches_assignment("/portal/site/abc/assignment/123") is True
    assert _href_matches_assignment("/portal/site/abc/submission/123") is True
    assert _href_matches_assignment("https://x/Assignment/1") is True


def test_href_matches_assignment_help_excluded():
    assert _href_matches_assignment("/portal/help/main?help=sakai.assignment") is False
    assert _href_matches_assignment("/portal/help/assignment") is False


def test_href_matches_assignment_false():
    assert _href_matches_assignment("/portal/site/abc/page") is False


# --------------------------------------------------------------------------- #
# Tool link discovery
# --------------------------------------------------------------------------- #
def test_find_assignments_tool_link():
    html = '<a href="/portal/site/abc/tool/xyz" title="Trabalhos">Trabalhos</a>'
    soup = BeautifulSoup(html, "html.parser")
    assert find_assignments_tool_link(soup, "abc") == "/portal/site/abc/tool/xyz"


def test_find_assignments_tool_link_none():
    html = '<a href="/portal/site/abc/page">Página</a>'
    soup = BeautifulSoup(html, "html.parser")
    assert find_assignments_tool_link(soup, "abc") is None


# --------------------------------------------------------------------------- #
# Column mapping + cell extraction
# --------------------------------------------------------------------------- #
def test_map_columns():
    html = (
        "<tr><th>Título</th><th>Estado</th>"
        "<th>Abertura</th><th>Prazo de entrega</th></tr>"
    )
    soup = BeautifulSoup(html, "html.parser")
    assert _map_columns(soup.find("tr")) == {
        "title": 0,
        "status": 1,
        "open": 2,
        "due": 3,
    }


def test_map_columns_none():
    assert _map_columns(None) == {}


def _cells(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all(["th", "td"])


def test_cell_date_within_range():
    cells = _cells("<tr><td>título</td><td>2026-10-01 09:00</td></tr>")
    assert _cell_date(cells, 1) == "2026-10-01T09:00:00+01:00"


def test_cell_date_out_of_range():
    cells = _cells("<tr><td>título</td></tr>")
    assert _cell_date(cells, 5) is None


def test_cell_date_none_index():
    cells = _cells("<tr><td>título</td></tr>")
    assert _cell_date(cells, None) is None


def test_cell_status():
    cells = _cells("<tr><td>Entregue</td></tr>")
    status, label = _cell_status(cells, 0)
    assert status == "submitted"
    assert label == "Entregue"


# --------------------------------------------------------------------------- #
# Assignment list parsing
# --------------------------------------------------------------------------- #
ASSIGNMENT_TABLE_HTML = """
<table>
  <thead>
    <tr>
      <th>Título</th>
      <th>Data de abertura</th>
      <th>Data limite</th>
      <th>Estado</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="/portal/site/abc/assignment/123">Trabalho 1</a></td>
      <td>2026-10-01 09:00</td>
      <td>2026-11-05 23:55</td>
      <td>Entregue</td>
    </tr>
    <tr>
      <td><a href="/portal/site/abc/assignment/124">Trabalho 2</a></td>
      <td>2026-10-02 09:00</td>
      <td>2026-11-06 23:55</td>
      <td>Não iniciado</td>
    </tr>
  </tbody>
</table>
"""


def test_parse_assignment_list_table():
    items = parse_assignment_list(
        ASSIGNMENT_TABLE_HTML, "https://virtual.ipb.pt", "abc", "Matemática"
    )
    assert len(items) == 2

    first = items[0]
    assert first.course == "Matemática"
    assert first.title == "Trabalho 1"
    assert first.url == "https://virtual.ipb.pt/portal/site/abc/assignment/123"
    assert first.open_at == "2026-10-01T09:00:00+01:00"
    assert first.due_at == "2026-11-05T23:55:00+00:00"
    assert first.status == "submitted"
    assert first.status_label == "Entregue"

    second = items[1]
    assert second.title == "Trabalho 2"
    assert second.status == "not_started"


FALLBACK_HTML = """
<ul>
  <li>
    <a href="/portal/site/abc/assignment/200">Trabalho X</a>
    2026-10-01 09:00 - 2026-11-05 23:55
  </li>
</ul>
"""


def test_parse_assignment_list_fallback():
    items = parse_assignment_list(
        FALLBACK_HTML, "https://virtual.ipb.pt", "abc", "Matemática"
    )
    assert len(items) == 1
    it = items[0]
    assert it.title == "Trabalho X"
    assert it.open_at == "2026-10-01T09:00:00+01:00"
    assert it.due_at == "2026-11-05T23:55:00+00:00"


def test_parse_assignment_list_empty():
    items = parse_assignment_list(
        "<html><body>no assignments</body></html>",
        "https://virtual.ipb.pt",
        "abc",
        "Matemática",
    )
    assert items == []


# --------------------------------------------------------------------------- #
# Assignment detail parsing
# --------------------------------------------------------------------------- #
DETAIL_HTML = """
<div>
  <h3>Instruções</h3>
  <div class="textPanel">
    <p>Fazer o trabalho em grupo.</p>
    <p>Entregar até à data limite.</p>
  </div>
  <a href="/access/content/group/abc/enunciado.pdf">enunciado.pdf</a>
  <a href="/access/content/group/abc/solucao.zip">solucao.zip</a>
  <a href="/portal/site/abc">Ir para o site</a>
</div>
"""


def test_parse_assignment_detail():
    desc, text, attachments = parse_assignment_detail(
        DETAIL_HTML, "https://virtual.ipb.pt"
    )
    assert desc is not None and "Fazer o trabalho" in desc
    assert text is not None
    assert "Fazer o trabalho em grupo." in text
    assert "Entregar até à data limite." in text

    assert len(attachments) == 2
    assert attachments[0].name == "enunciado.pdf"
    assert (
        attachments[0].url
        == "https://virtual.ipb.pt/access/content/group/abc/enunciado.pdf"
    )
    assert attachments[1].name == "solucao.zip"


def test_extract_attachments_download_and_extension():
    html = """
    <a href="/portal/site/abc/download?file=1">Ficheiro</a>
    <a href="/portal/site/abc/page">Relatório.pdf</a>
    <a href="/access/content/group/x/f.pdf">f.pdf</a>
    <a href="/access/content/group/x/f.pdf">f.pdf</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    atts = _extract_attachments(soup, "https://virtual.ipb.pt")
    assert len(atts) == 3


# --------------------------------------------------------------------------- #
# Description element + text cleanup
# --------------------------------------------------------------------------- #
def test_find_description_el_by_heading():
    html = "<h3>Instructions</h3><div class='panel'><p>Body</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    el = _find_description_el(soup)
    assert el is not None
    assert el.get("class") == ["panel"]


def test_find_description_el_by_id():
    html = "<div id='assignmentInstructions'><p>Body</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    el = _find_description_el(soup)
    assert el.get("id") == "assignmentInstructions"


def test_find_description_el_none():
    soup = BeautifulSoup("<div><p>nothing</p></div>", "html.parser")
    assert _find_description_el(soup) is None


def test_clean_text():
    text = "  Linha um   \n\n  Linha dois\ttexto  "
    assert _clean_text(text) == "Linha um\nLinha dois texto"


# --------------------------------------------------------------------------- #
# scrape_assignments orchestration (past filtering)
# --------------------------------------------------------------------------- #
class FakeClient:
    base_url = "https://virtual.ipb.pt"

    def __init__(self, pages):
        self.pages = pages

    def get(self, path):
        if path.startswith(self.base_url):
            path = path[len(self.base_url):]
        from types import SimpleNamespace

        return SimpleNamespace(text=self.pages.get(path, ""))


def test_scrape_assignments_filters_past(monkeypatch):
    monkeypatch.setattr("upb.assignments.time.sleep", lambda *a, **k: None)
    pages = {
        "portal/site/abc": (
            '<a href="/portal/site/abc/tool/x" title="Trabalhos">Trabalhos</a>'
        ),
        "/portal/site/abc/tool/x": """
        <ul>
          <li><a href="/portal/site/abc/assignment/1">Trabalho A</a>
              2026-01-01 09:00 - 2026-01-15 23:55</li>
          <li><a href="/portal/site/abc/assignment/2">Trabalho B</a>
              2099-01-01 09:00 - 2099-06-01 23:55</li>
        </ul>
        """,
        "/portal/site/abc/assignment/2": "",
    }
    client = FakeClient(pages)
    items = scrape_assignments(client, {"abc": "Matemática"}, delay=0)
    assert [i.title for i in items] == ["Trabalho B"]


def test_scrape_assignments_include_past(monkeypatch):
    monkeypatch.setattr("upb.assignments.time.sleep", lambda *a, **k: None)
    pages = {
        "portal/site/abc": (
            '<a href="/portal/site/abc/tool/x" title="Trabalhos">Trabalhos</a>'
        ),
        "/portal/site/abc/tool/x": """
        <ul>
          <li><a href="/portal/site/abc/assignment/1">Trabalho A</a>
              2026-01-01 09:00 - 2026-01-15 23:55</li>
          <li><a href="/portal/site/abc/assignment/2">Trabalho B</a>
              2099-01-01 09:00 - 2099-06-01 23:55</li>
        </ul>
        """,
        "/portal/site/abc/assignment/1": "",
        "/portal/site/abc/assignment/2": "",
    }
    client = FakeClient(pages)
    items = scrape_assignments(
        client, {"abc": "Matemática"}, delay=0, include_past=True
    )
    assert [i.title for i in items] == ["Trabalho A", "Trabalho B"]
