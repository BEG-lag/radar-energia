"""Validates the committed dataset in data/ (runs in CI and in the scheduled update)."""

from __future__ import annotations

import json
from datetime import date

import jsonschema

from radar_energia import store

from .conftest import ROOT

DATA = ROOT / "data"


def records() -> list[dict]:
    return list(store.iter_records(DATA))


def test_every_day_file_matches_the_schema(schema: dict) -> None:
    validator = jsonschema.Draft202012Validator(schema)
    found = records()
    assert found, "data/ is empty"
    for record in found:
        errors = sorted(validator.iter_errors(record), key=str)
        assert not errors, f"{record['date']}: {errors[0].message}"


def test_files_are_canonical_and_named_after_their_date() -> None:
    for path in sorted(DATA.glob("[0-9]*/[0-9]*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        assert path == store.day_path(date.fromisoformat(record["date"]), DATA)
        assert path.read_text(encoding="utf-8") == store.dumps(record)


def test_item_ids_are_unique() -> None:
    ids = [
        item["id"]
        for record in records()
        for item in [*(record["dof"] or {}).get("items", []), *record["authorities"]]
    ]
    assert len(ids) == len(set(ids))


def test_meta_matches_the_data() -> None:
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    found = records()
    assert meta["first_date"] == found[0]["date"]
    assert meta["last_date"] == found[-1]["date"]
    assert meta["days"] == len(found)
