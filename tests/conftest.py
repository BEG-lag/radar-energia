"""Shared fixtures. Everything runs offline against responses recorded on 2026-11-17."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parent.parent


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_json(name: str) -> dict:
    return json.loads(fixture_text(name))


@pytest.fixture(scope="session")
def schema() -> dict:
    return json.loads((ROOT / "schema" / "day.schema.json").read_text(encoding="utf-8"))
