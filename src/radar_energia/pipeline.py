"""Fetch every working source for a date range and merge it into the day files.

A source that fails is logged and skipped: what was stored before stays untouched, so a
temporary outage never erases data and never fails the scheduled run on its own.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from . import store
from .dates import day_range
from .http import FetchError, PoliteClient
from .sources import cenace, fuel, gobmx, sidof

log = logging.getLogger(__name__)


@dataclass
class Report:
    ok: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    changed: list[str] = field(default_factory=list)

    def run(self, name: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            result = func(*args, **kwargs)
        except (FetchError, ValueError, KeyError) as exc:
            log.warning("%s failed: %s", name, exc)
            self.failed[name] = str(exc)[:300]
            return None
        except Exception as exc:  # network stacks raise many types; never abort the run
            log.warning("%s failed unexpectedly: %r", name, exc)
            self.failed[name] = repr(exc)[:300]
            return None
        self.ok.append(name)
        return result


def update(
    start: date,
    end: date,
    today: date,
    *,
    root: Path = store.DATA_DIR,
    client: PoliteClient | None = None,
    max_pages: int = 6,
) -> Report:
    report = Report()
    own_client = client is None
    client = client or PoliteClient()
    records = {day: store.load(day, root) or store.new_record(day) for day in day_range(start, end)}
    try:
        for day in records:
            payload = report.run(f"sidof:notas:{day}", sidof.fetch_notes, client, day)
            if payload is not None:
                records[day]["dof"] = sidof.parse_notes(payload, day)

        fix = report.run("sidof:fix", sidof.fetch_fix, client, start, end)
        if fix is not None:
            for day, value in sidof.parse_fix(fix).items():
                if day in records:
                    records[day]["markets"]["fix"] = sidof.fix_record(day, value)

        zones = report.run("cenace:sw-pend", cenace.fetch, client, start, min(end, today))
        for day, rows in (zones or {}).items():
            if day in records and rows:
                records[day]["markets"]["zonal_prices"] = rows

        for archive in gobmx.ARCHIVES:
            name = f"gobmx:{archive.slug}:{archive.section}"
            items = report.run(name, gobmx.fetch_archive, client, archive, start, end, max_pages)
            by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
            for item in items or []:
                by_day[gobmx.published_day(item)].append(item)
            for day, fresh in by_day.items():
                if day in records:
                    merged = {i["id"]: i for i in records[day]["authorities"]}
                    merged.update({i["id"]: i for i in fresh})
                    records[day]["authorities"] = list(merged.values())

        if today in records:
            summary = report.run("cne:gasolinas-diesel", fuel.fetch, client)
            if summary is not None:
                records[today]["markets"]["fuel"] = summary
            gas_lp = report.run("cne:gas-lp", gobmx.fetch_gas_lp, client)
            if gas_lp is not None:
                records[today]["markets"]["gas_lp"] = gas_lp
    finally:
        if own_client:
            client.close()

    for day, record in records.items():
        if store.is_empty(record) and not store.day_path(day, root).exists():
            continue
        if store.save(record, root):
            report.changed.append(day.isoformat())
    return report
