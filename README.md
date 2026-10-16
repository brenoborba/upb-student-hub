# upb-student-hub

Log into **UPB.Virtual** (the Sakai LMS at `virtual.ipb.pt`) and extract your
assignments — title, status, open/due dates, description, and attachments — into
a JSON dataset and a subscribable `.ics` calendar feed.

## Requirements

- Python 3.9+

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your credentials
cp .env.example .env
# edit .env and fill in UPB_USERNAME and UPB_PASSWORD
```

## Usage

```bash
python scraper.py
```

This writes two files:

- `assignments.json` — one object per assignment:
  ```json
  {
    "course": "Matemática Aplicada",
    "assignment": "Trabalho 2",
    "open_at": "2026-10-01T09:00:00+01:00",
    "due_at": "2026-11-05T23:55:00+01:00",
    "status": "submitted",
    "status_label": "Entregue",
    "description": "<p>...</p>",
    "description_text": "Instruções...",
    "attachments": [{ "name": "enunciado.pdf", "url": "https://..." }],
    "url": "https://virtual.ipb.pt/portal/site/..."
  }
  ```
- `feed.ics` — one calendar event per assignment (due date), importable into
  Google Calendar / Apple Calendar.

### Useful flags

```bash
python scraper.py --debug            # save raw HTML to ./debug for parser tuning
python scraper.py --delay 1.0        # slow down detail requests
python scraper.py --all-sites        # scrape every enrolled site (not just favorites)
python scraper.py --include-past     # include assignments whose deadline has passed
python scraper.py --json out.json --ics out.ics
```

By default only your **favorite** sites (the top tabs) are scraped, so past
semesters are skipped. Use `--all-sites` to include everything.

By default assignments whose **due date has already passed** are skipped. Use
`--include-past` to keep them.

## Notes

- Dates are normalized to ISO-8601 in the Europe/Lisbon timezone.
- Calendar events span `due − 2h → due` (a 23:55 deadline shows as 21:55–23:55).
  Tweak `EVENT_LEAD_HOURS` in `upb/output.py` to change the lead time.
- Google Calendar can't set per-event colors from a `.ics` file. To get red
  events, import `feed.ics` into a **dedicated calendar** and set that
  calendar's color to red.
- The base URL is configurable via `UPB_BASE_URL` in `.env` (useful if the
  university's domain changes from `ipb.pt` to `upb.pt`).
- The assignment parsers are heuristic (Sakai's HTML is not a stable API). If a
  run misses data, use `--debug` and check the saved HTML in `./debug`.

## Project layout

```
upb-student-hub/
├── scraper.py           # CLI entrypoint
├── upb/
│   ├── client.py        # Sakai login + session
│   ├── sites.py         # discover enrolled courses
│   ├── assignments.py   # list + detail parsing
│   ├── models.py        # data models
│   ├── output.py        # JSON + ICS writers
│   ├── config.py        # .env loading
│   └── utils.py
├── requirements.txt
└── .env.example
```
