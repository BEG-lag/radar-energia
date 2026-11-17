"""Aggregates computed from the day files: flat item list, counts and price series."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from . import store
from .rules import SUBSECTORS


def flat_items(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every radar item (DOF notes and authority entries), newest first."""
    items: list[dict[str, Any]] = []
    for record in records:
        day = record["date"]
        dof = record.get("dof") or {}
        for order, note in enumerate(dof.get("items", [])):
            items.append(
                {
                    **note,
                    "date": day,
                    "source": "dof",
                    "sort": f"{day}T07:00:00 {order:03d}",
                }
            )
        for entry in record.get("authorities", []):
            items.append({**entry, "date": day, "source": "gobmx", "sort": entry["published"]})
    items.sort(key=lambda i: (i["date"], i["sort"], i["id"]), reverse=True)
    for item in items:
        del item["sort"]
    return items


def subsector_counts(items: Iterable[dict[str, Any]], start: date, end: date) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        if start.isoformat() <= item["date"] <= end.isoformat():
            counts.update(item["subsectors"])
    return {s.key: counts.get(s.key, 0) for s in SUBSECTORS}


def week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def month_bounds(day: date) -> tuple[date, date]:
    start = day.replace(day=1)
    following = (start + timedelta(days=32)).replace(day=1)
    return start, following - timedelta(days=1)


Series = list[tuple[str, float]]


def fix_series(records: Iterable[dict[str, Any]]) -> Series:
    return [
        (r["date"], r["markets"]["fix"]["value"]) for r in records if "fix" in r.get("markets", {})
    ]


def zone_series(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    zones: dict[str, dict[str, Any]] = {}
    for record in records:
        for row in record.get("markets", {}).get("zonal_prices", []):
            key = f"{row['system']}:{row['zone']}"
            zone = zones.setdefault(
                key,
                {"system": row["system"], "zone": row["zone"], "name": row["name"], "points": []},
            )
            zone["points"].append((record["date"], row["avg"]))
    return zones


def fuel_series(records: Iterable[dict[str, Any]]) -> dict[str, Series]:
    series: dict[str, Series] = {}
    for record in records:
        fuel = record.get("markets", {}).get("fuel")
        if not fuel:
            continue
        for product, values in fuel["products"].items():
            series.setdefault(product, []).append((record["date"], values["median"]))
    return series


@dataclass(frozen=True)
class Change:
    date: str
    value: float
    previous_date: str | None
    previous: float | None

    @property
    def delta(self) -> float | None:
        return None if self.previous is None else self.value - self.previous

    @property
    def pct(self) -> float | None:
        if self.previous in (None, 0):
            return None
        return (self.value - self.previous) / self.previous * 100


def last_change(series: Series, until: str | None = None) -> Change | None:
    points = [p for p in series if until is None or p[0] <= until]
    if not points:
        return None
    day, value = points[-1]
    if len(points) == 1:
        return Change(day, value, None, None)
    prev_day, prev = points[-2]
    return Change(day, value, prev_day, prev)


def stats(root: Path = store.DATA_DIR) -> dict[str, Any]:
    records = list(store.iter_records(root))
    if not records:
        return {"days": 0}
    items = flat_items(records)
    dof_days = [r for r in records if r.get("dof")]
    return {
        "days": len(records),
        "first": records[0]["date"],
        "last": records[-1]["date"],
        "dof_editions_days": len(dof_days),
        "dof_notes_reviewed": sum(r["dof"]["notes_reviewed"] for r in dof_days),
        "dof_items": sum(1 for i in items if i["source"] == "dof"),
        "authority_items": sum(1 for i in items if i["source"] == "gobmx"),
        "fix_days": len(fix_series(records)),
        "zone_days": len({r["date"] for r in records if r.get("markets", {}).get("zonal_prices")}),
        "fuel_snapshots": sum(1 for r in records if r.get("markets", {}).get("fuel")),
        "by_subsector": dict(Counter(s for i in items for s in i["subsectors"]).most_common()),
        "by_agency": dict(Counter(a for i in items for a in i["agencies"]).most_common()),
    }
