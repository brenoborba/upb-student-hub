import argparse

from upb import gcal
from upb.assignments import scrape_assignments
from upb.client import LoginError, SakaiClient
from upb.config import load_config
from upb.output import write_ics, write_json
from upb.sites import discover_sites


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Scrape UPB.Virtual assignments into JSON + an ICS calendar feed."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="save raw HTML snapshots to ./debug for parser tuning",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="seconds to wait between detail-page requests (default: 0.5)",
    )
    parser.add_argument(
        "--all-sites",
        action="store_true",
        help="scrape every enrolled site (incl. past semesters); default is favorites only",
    )
    parser.add_argument(
        "--include-past",
        action="store_true",
        help="include assignments whose due date has already passed (default: skip them)",
    )
    parser.add_argument("--json", dest="json_out", default="assignments.json")
    parser.add_argument("--ics", dest="ics_out", default="feed.ics")
    parser.add_argument(
        "--sync-calendar",
        action="store_true",
        help="sync assignments to Google Calendar via OAuth2 (instead of only writing .ics)",
    )
    parser.add_argument(
        "--calendar-id",
        default=None,
        help="Google Calendar ID to sync into (overrides UPB_GCAL_CALENDAR_ID / name)",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    client = SakaiClient(cfg.base_url)

    print(f"[1/4] Logging in to {cfg.base_url} ...")
    try:
        client.login(cfg.username, cfg.password)
    except LoginError as exc:
        print(f"       ERROR: {exc}")
        raise SystemExit(1)
    print("       Logged in.")

    print("[2/4] Discovering courses ...")
    debug_dir = "debug" if args.debug else None
    sites = discover_sites(client, favorites_only=not args.all_sites, debug_dir=debug_dir)
    if not sites:
        print("       No courses found. Re-run with --debug to inspect the home page.")
    else:
        scope = "all sites" if args.all_sites else "favorite sites"
        print(f"       Found {len(sites)} course(s) ({scope}):")
        for sid, title in sites.items():
            print(f"         - {title} ({sid})")

    print("[3/4] Scraping assignments ...")
    assignments = scrape_assignments(
        client, sites, delay=args.delay, debug_dir=debug_dir, include_past=args.include_past
    )
    print(f"       Collected {len(assignments)} assignment(s).")

    print("[4/4] Writing output ...")
    write_json(assignments, args.json_out)
    write_ics(assignments, args.ics_out)
    print(f"       Done -> {args.json_out}, {args.ics_out}")

    if args.sync_calendar:
        print("[5/5] Syncing to Google Calendar ...")
        try:
            stats = gcal.sync_to_calendar(
                assignments,
                credentials_path=cfg.gcal_credentials,
                token_path=cfg.gcal_token,
                calendar_id=args.calendar_id or cfg.gcal_calendar_id,
                calendar_name=cfg.gcal_calendar_name,
                include_past=args.include_past,
            )
        except gcal.GcalError as exc:
            print(f"       ERROR: {exc}")
            raise SystemExit(1)
        print(
            f"       Done -> {stats['created']} created, "
            f"{stats['updated']} updated, {stats['deleted']} deleted."
        )


if __name__ == "__main__":
    main()
