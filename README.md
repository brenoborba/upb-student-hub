# upb-student-hub

Log into **UPB.Virtual** (the Sakai LMS at `virtual.ipb.pt`) and extract your
assignments — title, status, open/due dates, description, and attachments — into
a JSON dataset and a subscribable `.ics` calendar feed.

## Requirements

- Python 3.11+

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

## Google Calendar live sync

Instead of re-importing `feed.ics` by hand, sync directly to Google Calendar
with the API. On each run events are created/updated/deleted to match your
current assignments — colored red, with reminders — so the calendar stays up to
date automatically.

1. Create an **OAuth 2.0 Client ID** in
   [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   (Application type: **Desktop app**).
2. Download it as `credentials.json` into the project root (it is git-ignored).
3. Run:

   ```bash
   python scraper.py --sync-calendar
   ```

   The first run opens a browser to authorize access; the refresh token is
   saved to `token.json` (git-ignored), so later runs are silent.

By default events go into a dedicated calendar named **IPB.Virtual** (created
automatically). Override the target with `UPB_GCAL_CALENDAR_ID` (a specific
calendar ID) or `UPB_GCAL_CALENDAR_NAME` in `.env`. To reuse an existing
calendar, pass `--calendar-id <id>` (find the id under the calendar's Settings →
"Calendar ID").

## Backend (FastAPI)

A multi-user API that stores each student's Sakai credentials (encrypted) and
scrapes + syncs on demand. Lives in `backend/`.

```bash
pip install -r requirements-dev.txt      # includes backend deps
# set ENCRYPTION_KEY in .env (see .env.example)
uvicorn backend.app.main:app --reload    # run from the repo root
```

Interactive docs at `http://127.0.0.1:8000/docs`.

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | liveness |
| POST | `/api/users` | create a user (returns an API key once) |
| PUT | `/api/users/{id}/sakai-credentials` | store encrypted Sakai login |
| PUT | `/api/users/{id}/google-token` | store encrypted Google refresh token |
| POST | `/api/users/{id}/sync` | scrape Sakai + sync Google Calendar |
| GET | `/api/users/{id}/assignments` | list stored assignments |
| GET | `/api/users/{id}/sync-runs` | recent sync status |

Authenticate with the `X-API-Key` header. This is a placeholder auth scheme to
be replaced by Google OAuth sign-in. The database defaults to SQLite
(`upb_hub.db`, git-ignored); set `DATABASE_URL` to a Postgres URL for
production.

Throttling protects the Sakai host under multi-user load: a global token bucket
in `upb/client.py` (~30 req/min, small burst) wraps every Sakai request, sync
jobs are capped at 3 concurrent, and each user has a 15-minute cooldown
(manual syncs bypass it).

## Tests

```bash
# install runtime + test dependencies
pip install -r requirements-dev.txt

# run the unit test suite
pytest
```

Tests live under `tests/` and cover the parsers, models, output writers, and
configuration without touching the network. Run `pytest` on every iteration
before pushing.

A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the suite
automatically on pushes to `main`/`dev` and on every pull request, across
Python 3.11–3.13.

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
│   ├── gcal.py          # Google Calendar API sync (--sync-calendar)
│   ├── config.py        # .env loading
│   └── utils.py
├── requirements.txt
└── .env.example
```
