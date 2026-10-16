from __future__ import annotations

import re
import time
from datetime import datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from upb.models import Assignment, Attachment
from upb.utils import save_debug

LISBON = ZoneInfo("Europe/Lisbon")

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
]

DATE_TOKEN_RE = re.compile(
    r"(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}\.\d{1,2}\.\d{4})"
    r"(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?"
)

STATUS_MAP = {
    "aberto": "open",
    "aberta": "open",
    "open": "open",
    "não iniciado": "not_started",
    "nao iniciado": "not_started",
    "not started": "not_started",
    "não submetido": "not_started",
    "entregue": "submitted",
    "submetido": "submitted",
    "submitted": "submitted",
    "devolvido": "returned",
    "devolvida": "returned",
    "returned": "returned",
    "classificado": "graded",
    "classificada": "graded",
    "avaliado": "graded",
    "avaliada": "graded",
    "graded": "graded",
    "fechado": "closed",
    "fechada": "closed",
    "closed": "closed",
}

ASSIGN_TOOL_KEYWORDS = ("trabalho", "assign", "tarefa")

DESC_IDS = (
    "assignmentInstructions",
    "assignment_instructions",
    "instructions",
    "assignmentDescription",
    "description",
    "assignmentBody",
)

DESC_CLASS_HINTS = (
    "instruction",
    "description",
    "textpanel",
    "assignment-body",
    "assignment-body-text",
)

INSTRUCTIONS_HEADINGS = ("instructions", "instruções", "instrucoes")


# Sakai's conventional times when a date is shown without an explicit time.
DEFAULT_OPEN_TIME = "00:00"
DEFAULT_DUE_TIME = "23:55"

TIME_RE = re.compile(r"\d{1,2}:\d{2}")

# Sakai renders a built-in "Ajuda" (Help) link on the Assignments tool page,
# e.g. /portal/help/main?help=sakai.assignment. Its URL contains "assignment"
# but is not an assignment, so exclude help-system links from matching.
_HELP_HREF_RE = re.compile(r"/help/|help=", re.I)


def find_dates(text: str) -> list[str]:
    return [m.group(0) for m in DATE_TOKEN_RE.finditer(text)]


def parse_datetime(raw: str, default_time: str | None = None) -> str | None:
    raw = raw.strip().replace("\xa0", " ")
    # If the token has no time component, apply the caller's default (e.g. 23:55
    # for due dates), but never override an explicit time.
    if default_time and not TIME_RE.search(raw):
        raw = f"{raw} {default_time}"
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=LISBON)
        return dt.isoformat(timespec="seconds")
    return None


def first_date(text: str, default_time: str | None = None) -> str | None:
    for raw in find_dates(text):
        parsed = parse_datetime(raw, default_time=default_time)
        if parsed:
            return parsed
    return None


def is_past(iso: str | None, now: datetime | None = None) -> bool:
    """True if the ISO timestamp (e.g. a due date) is before ``now``."""
    if not iso:
        return False
    try:
        due = datetime.fromisoformat(iso)
    except ValueError:
        return False
    if now is None:
        now = datetime.now(LISBON)
    return due < now


def normalize_status(text: str) -> tuple[str | None, str]:
    t = text.strip().lower()
    for key, value in STATUS_MAP.items():
        if key in t:
            return value, text.strip()
    return None, text.strip()


def find_assignments_tool_link(soup: BeautifulSoup, site_id: str) -> str | None:
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/tool/" not in href:
            continue
        haystack = " ".join(
            [
                a.get("title", ""),
                " ".join(a.get("class", [])),
                a.get_text(" ", strip=True),
            ]
        ).lower()
        if any(k in haystack for k in ASSIGN_TOOL_KEYWORDS):
            return href
    return None


def scrape_assignments(
    client,
    sites: dict[str, str],
    delay: float = 0.5,
    debug_dir: str | None = None,
    include_past: bool = False,
) -> list[Assignment]:
    results: list[Assignment] = []
    total = len(sites)

    for idx, (site_id, course) in enumerate(sites.items(), 1):
        print(f"       [{idx}/{total}] {course}")

        try:
            site_html = client.get(f"portal/site/{site_id}").text
        except Exception as exc:  # noqa: BLE001
            print(f"         ! failed to fetch site page: {exc}")
            continue
        save_debug(debug_dir, f"site_{site_id}.html", site_html)

        soup = BeautifulSoup(site_html, "html.parser")
        tool_href = find_assignments_tool_link(soup, site_id)
        if not tool_href:
            print("         - no assignments tool link found")
            continue

        try:
            list_html = client.get(tool_href).text
        except Exception as exc:  # noqa: BLE001
            print(f"         ! failed to fetch assignments list: {exc}")
            continue
        save_debug(debug_dir, f"assignments_{site_id}.html", list_html)

        items = parse_assignment_list(list_html, client.base_url, site_id, course)

        if not include_past:
            before = len(items)
            items = [it for it in items if not is_past(it.due_at)]
            skipped = before - len(items)
            if skipped:
                print(f"         - skipped {skipped} past assignment(s)")

        for n, item in enumerate(items, 1):
            if item.url:
                time.sleep(delay)
                detail_html = ""
                try:
                    detail_html = client.get(item.url).text
                except Exception as exc:  # noqa: BLE001
                    print(f"         ! failed to fetch detail for '{item.title}': {exc}")
                save_debug(debug_dir, f"detail_{site_id}_{n}.html", detail_html)
                if detail_html:
                    item.description, item.description_text, item.attachments = parse_assignment_detail(
                        detail_html, client.base_url
                    )
            results.append(item)

        time.sleep(delay)

    return results


def parse_assignment_list(html: str, base_url: str, site_id: str, course: str) -> list[Assignment]:
    soup = BeautifulSoup(html, "html.parser")
    table = _find_assignments_table(soup)
    if table is None:
        return _parse_list_fallback(soup, base_url, course)

    cols = _map_columns(_find_header_row(table))
    items: list[Assignment] = []

    for row in table.find_all("tr"):
        link = _find_assignment_link(row)
        if link is None:
            continue
        title = link.get_text(" ", strip=True).strip()
        if not title:
            continue
        url = urljoin(base_url, link["href"])
        cells = row.find_all(["th", "td"])
        row_text = row.get_text(" ", strip=True)

        open_at = _cell_date(cells, cols.get("open"), default_time=DEFAULT_OPEN_TIME)
        due_at = _cell_date(cells, cols.get("due"), default_time=DEFAULT_DUE_TIME)
        if cols.get("status") is not None:
            status, status_label = _cell_status(cells, cols.get("status"))
        else:
            status, status_label = normalize_status(row_text)

        if open_at is None and due_at is None:
            raws = find_dates(row_text)
            open_at = parse_datetime(raws[0], default_time=DEFAULT_OPEN_TIME) if raws else None
            due_at = parse_datetime(raws[1], default_time=DEFAULT_DUE_TIME) if len(raws) > 1 else None

        items.append(
            Assignment(
                course=course,
                title=title,
                url=url,
                open_at=open_at,
                due_at=due_at,
                status=status,
                status_label=status_label,
            )
        )

    return items if items else _parse_list_fallback(soup, base_url, course)


def parse_assignment_detail(html: str, base_url: str) -> tuple[str | None, str | None, list[Attachment]]:
    soup = BeautifulSoup(html, "html.parser")
    desc_el = _find_description_el(soup)
    desc_html = desc_el.decode_contents().strip() if desc_el is not None else None
    desc_text = _clean_text(desc_el.get_text("\n")) if desc_el is not None else None
    attachments = _extract_attachments(soup, base_url)
    return desc_html, desc_text, attachments


def _href_matches_assignment(href: str) -> bool:
    h = href.lower()
    if _HELP_HREF_RE.search(h):
        return False
    return "assignment" in h or "submission" in h


def _find_assignments_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        if table.find("a", href=_href_matches_assignment):
            return table
    return None


def _find_header_row(table):
    thead = table.find("thead")
    if thead is not None:
        rows = thead.find_all("tr")
        if rows:
            return rows[0]
    for row in table.find_all("tr"):
        if row.find("th"):
            return row
    return None


def _find_assignment_link(row):
    for a in row.find_all("a", href=True):
        if _href_matches_assignment(a["href"]):
            return a
    return None


def _map_columns(header_row) -> dict[str, int]:
    if header_row is None:
        return {}
    cols: dict[str, int] = {}
    for i, cell in enumerate(header_row.find_all(["th", "td"])):
        t = cell.get_text(" ", strip=True).lower()
        if any(k in t for k in ("título", "titulo", "title", "trabalho", "assignment")):
            cols.setdefault("title", i)
        if any(k in t for k in ("estado", "status", "situação", "situacao")):
            cols.setdefault("status", i)
        if any(k in t for k in ("abertura", "open", "início", "inicio")):
            cols.setdefault("open", i)
        if any(k in t for k in ("limite", "due", "prazo", "entrega", "fecho", "deadline")):
            cols.setdefault("due", i)
    return cols


def _cell_date(cells, idx: int | None, default_time: str | None = None) -> str | None:
    if idx is None or idx >= len(cells):
        return None
    return first_date(cells[idx].get_text(" ", strip=True), default_time=default_time)


def _cell_status(cells, idx: int | None) -> tuple[str | None, str]:
    if idx is None or idx >= len(cells):
        return None, ""
    return normalize_status(cells[idx].get_text(" ", strip=True))


_SKIP_TITLES = {
    "trabalhos", "assignments", "adicionar", "novo", "nova", "new", "add",
    "ver", "edit", "editar", "apagar", "delete", "submeter", "submit",
}


def _parse_list_fallback(soup: BeautifulSoup, base_url: str, course: str) -> list[Assignment]:
    items: list[Assignment] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        if not _href_matches_assignment(a["href"]):
            continue
        title = a.get_text(" ", strip=True).strip()
        if not title or title.lower() in _SKIP_TITLES:
            continue
        url = urljoin(base_url, a["href"])
        if url in seen:
            continue
        seen.add(url)

        row = a.find_parent("tr") or a.find_parent("li") or a.parent
        row_text = row.get_text(" ", strip=True) if row else title
        raws = find_dates(row_text)
        status, status_label = normalize_status(row_text)

        items.append(
            Assignment(
                course=course,
                title=title,
                url=url,
                open_at=parse_datetime(raws[0], default_time=DEFAULT_OPEN_TIME) if raws else None,
                due_at=parse_datetime(raws[1], default_time=DEFAULT_DUE_TIME) if len(raws) > 1 else None,
                status=status,
                status_label=status_label,
            )
        )

    return items


def _find_description_el(soup: BeautifulSoup):
    # Sakai renders the real assignment instructions in a `.textPanel` div
    # immediately after an "Instructions" heading. Prefer that over the generic
    # id/class hints, which otherwise match the boilerplate `.instruction` text.
    for heading in soup.find_all(["h2", "h3", "h4", "h5", "h6"]):
        if heading.get_text(" ", strip=True).lower() in INSTRUCTIONS_HEADINGS:
            panel = heading.find_next_sibling()
            if panel is not None:
                return panel

    for cid in DESC_IDS:
        el = soup.find(id=cid)
        if el is not None:
            return el
    for hint in DESC_CLASS_HINTS:
        el = soup.find(class_=re.compile(hint, re.I))
        if el is not None:
            return el
    return None


def _clean_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _extract_attachments(soup: BeautifulSoup, base_url: str) -> list[Attachment]:
    attachments: list[Attachment] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True).strip()
        is_attachment = (
            "/access/content/" in href
            or "/content/group/" in href
            or "download" in href.lower()
            or bool(re.search(r"\.\w{1,5}$", text))
        )
        if not is_attachment:
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        name = text or url.rstrip("/").split("/")[-1]
        attachments.append(Attachment(name=name, url=url))

    return attachments
