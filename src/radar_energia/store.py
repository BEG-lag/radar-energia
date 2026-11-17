"""One JSON file per day in ``data/YYYY/MM/YYYY-MM-DD.json``.

Files hold no fetch timestamps and are written in a fixed order, so a run only produces a
git diff when an official source actually changed.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DATA_DIR = Path("data")


def day_path(day: date, root: Path = DATA_DIR) -> Path:
    return root / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.isoformat()}.json"


def new_record(day: date) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "date": day.isoformat(),
        "dof": None,
        "authorities": [],
        "markets": {},
    }


def load(day: date, root: Path = DATA_DIR) -> dict[str, Any] | None:
    path = day_path(day, root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def is_empty(record: dict[str, Any]) -> bool:
    return record.get("dof") is None and not record.get("authorities") and not record.get("markets")


MARKET_ORDER = ("fix", "zonal_prices", "fuel", "gas_lp")


def canonical(record: dict[str, Any]) -> dict[str, Any]:
    """Fixed key order and item order, whatever order the pipeline filled them in."""
    markets = record.get("markets") or {}
    authorities = sorted(
        record.get("authorities") or [], key=lambda i: (i["published"], i["id"]), reverse=True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "date": record["date"],
        "dof": record.get("dof"),
        "authorities": authorities,
        "markets": {key: markets[key] for key in MARKET_ORDER if key in markets},
    }


def dumps(record: dict[str, Any]) -> str:
    return json.dumps(canonical(record), ensure_ascii=False, indent=2) + "\n"


def save(record: dict[str, Any], root: Path = DATA_DIR) -> bool:
    """Write the record; return True only if the file changed."""
    path = day_path(date.fromisoformat(record["date"]), root)
    text = dumps(record)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def iter_records(root: Path = DATA_DIR) -> Iterator[dict[str, Any]]:
    for path in sorted(root.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/*.json")):
        yield json.loads(path.read_text(encoding="utf-8"))
