"""Command line: ``radar-energia update | backfill | build | reclassify | stats``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from . import __version__, store
from .dates import today_mx


def _date(text: str) -> date:
    return date.fromisoformat(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar-energia", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--data", type=Path, default=store.DATA_DIR, help="data directory")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    upd = sub.add_parser("update", help="re-fetch the last N days (scheduled run)")
    upd.add_argument("--days", type=int, default=4)
    upd.add_argument("--today", type=_date, default=None, help="override today (YYYY-MM-DD)")

    back = sub.add_parser("backfill", help="fetch a longer range, e.g. on day one")
    back.add_argument("--days", type=int, default=90)
    back.add_argument("--today", type=_date, default=None)

    build = sub.add_parser("build", help="rebuild the site in docs/ from data/")
    build.add_argument("--out", type=Path, default=Path("docs"))

    sub.add_parser("reclassify", help="re-apply the keyword rules to stored items")
    sub.add_parser("stats", help="print a summary of the stored data")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command in {"update", "backfill"}:
        from .pipeline import update

        today = args.today or today_mx()
        start = today - timedelta(days=max(args.days, 1) - 1)
        pages = 6 if args.command == "update" else 12
        report = update(start, today, today, root=args.data, max_pages=pages)
        print(f"{args.command} {start}..{today}: {len(report.ok)} source calls ok")
        for name, error in report.failed.items():
            print(f"  failed {name}: {error}")
        print(f"  changed days: {', '.join(report.changed) or 'none'}")
        return 1 if report.failed and not report.ok else 0

    if args.command == "build":
        from .site import build_site

        summary = build_site(args.data, args.out)
        print(f"built {args.out}: {summary}")
        return 0

    if args.command == "reclassify":
        from .reclassify import reclassify

        changed = reclassify(args.data)
        print(f"reclassified, {changed} day files changed")
        return 0

    if args.command == "stats":
        from .aggregates import stats

        for key, value in stats(args.data).items():
            print(f"{key}: {value}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
