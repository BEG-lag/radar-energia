"""Re-apply the keyword rules to every stored item after ``rules.py`` changes.

Only stored items can be reclassified. DOF notes that the old rules left out were never
stored; run ``radar-energia backfill`` to pick those up under broader rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import store
from .classify import classify
from .sources.gobmx import classify_item

_FIELDS = ("subsectors", "agencies", "matched")


def _dof_item(item: dict[str, Any]) -> dict[str, Any] | None:
    result = classify(item["title"], item.get("issuer"))
    if not result.relevant:
        return None
    return {
        **item,
        "subsectors": list(result.subsectors),
        "agencies": list(result.agencies),
        "matched": list(result.matched),
    }


def reclassify(root: Path = store.DATA_DIR) -> int:
    changed = 0
    for record in store.iter_records(root):
        if record.get("dof"):
            record["dof"]["items"] = [
                fresh for item in record["dof"]["items"] if (fresh := _dof_item(item))
            ]
        record["authorities"] = [
            fresh
            for item in record["authorities"]
            if (fresh := classify_item({k: v for k, v in item.items() if k not in _FIELDS}))
        ]
        if store.save(record, root):
            changed += 1
    return changed
