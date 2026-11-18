"""End to end update with every source served from recorded fixtures (no network)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx
import jsonschema
import pytest

from radar_energia import store
from radar_energia.http import PoliteClient
from radar_energia.pipeline import update

from .conftest import fixture_bytes, fixture_text

START, TODAY = date(2026, 11, 5), date(2026, 11, 7)


def shifted_cenace(system: str) -> str:
    """The recorded SW-PEND answer (17 and 18 Nov) moved to 6 and 7 Nov for this range."""
    text = fixture_text("cenace-pend-sin.json")
    text = text.replace("2026-11-17", "2026-11-06").replace("2026-11-18", "2026-11-07")
    if system == "BCA":
        payload = json.loads(text.replace('"MONTERREY"', '"MEXICALI"'))
        payload["sistema"] = "BCA"
        payload["Resultados"] = [r for r in payload["Resultados"] if r["zona_carga"] == "MEXICALI"]
        text = json.dumps(payload)
    return text


def handler(fail: set[str] | None = None):
    fail = fail or set()

    def respond(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if any(key in url for key in fail):
            return httpx.Response(500, text="error")
        if "/notas/05-11-2026" in url:
            return httpx.Response(200, content=fixture_bytes("sidof-notas-05-11-2026.json"))
        if "/dof/sidof/notas/" in url:
            return httpx.Response(200, content=fixture_bytes("sidof-notas-15-11-2026.json"))
        if "/indicadores/158/" in url:
            return httpx.Response(200, content=fixture_bytes("sidof-fix.json"))
        if "/SWPEND/SIM/SIN/" in url:
            return httpx.Response(200, text=shifted_cenace("SIN"))
        if "/SWPEND/SIM/BCA/" in url:
            return httpx.Response(200, text=shifted_cenace("BCA"))
        if "/cne/es/archivo/prensa" in url and "page=1" in url:
            return httpx.Response(200, text=fixture_text("gobmx-cne-prensa.html"))
        if "/cne/es/archivo/documentos" in url and "page=1" in url:
            return httpx.Response(200, text=fixture_text("gobmx-cne-documentos.html"))
        if "/archivo/" in url:
            return httpx.Response(200, text="<html><body></body></html>")
        if "publicaciones/prices" in url:
            return httpx.Response(200, content=fixture_bytes("fuel-prices.xml"))
        if "precios-maximos-aplicables-de-gas-lp" in url:
            return httpx.Response(200, text=fixture_text("gobmx-gas-lp.html"))
        return httpx.Response(404)

    return respond


def run(root: Path, fail: set[str] | None = None):
    client = PoliteClient(min_interval=0, retries=0, transport=httpx.MockTransport(handler(fail)))
    with client:
        return update(START, TODAY, TODAY, root=root, client=client)


@pytest.fixture
def data(tmp_path: Path) -> Path:
    report = run(tmp_path)
    assert not report.failed, report.failed
    return tmp_path


def test_update_writes_one_valid_file_per_day(data: Path, schema: dict) -> None:
    days = sorted(p.name for p in data.rglob("*.json"))
    assert days == ["2026-11-05.json", "2026-11-06.json", "2026-11-07.json"]
    for record in store.iter_records(data):
        jsonschema.validate(record, schema)


def test_update_merges_every_source(data: Path) -> None:
    nov5, nov6, nov7 = (store.load(date(2026, 11, d), data) for d in (5, 6, 7))
    assert [i["id"] for i in nov5["dof"]["items"]] == ["dof-5803022"]
    assert nov5["markets"]["fix"]["value"] == 18.6285
    assert nov6["dof"] is None  # the empty SIDOF answer: no edition
    agencies = {(i["agency"], i["section"]) for i in nov6["authorities"]}
    assert agencies == {("CNE", "prensa"), ("CNE", "documentos")}
    zones = [z["zone"] for z in nov6["markets"]["zonal_prices"]]
    assert zones == ["MONTERREY", "GUADALAJARA", "MERIDA", "HERMOSILLO", "MEXICALI"]
    assert set(nov7["markets"]) == {"zonal_prices", "fuel", "gas_lp"}
    assert "fuel" not in nov6["markets"]  # snapshots only belong to the run date


def test_second_run_changes_nothing(data: Path) -> None:
    before = {p: p.read_bytes() for p in data.rglob("*.json")}
    report = run(data)
    assert report.changed == []
    assert {p: p.read_bytes() for p in data.rglob("*.json")} == before


def test_failing_source_keeps_stored_data(data: Path) -> None:
    report = run(data, fail={"/dof/sidof/", "ws01.cenace"})
    assert any(name.startswith("sidof:notas") for name in report.failed)
    assert "cenace:sw-pend" in report.failed
    assert report.changed == []
    nov5 = store.load(date(2026, 11, 5), data)
    assert nov5["dof"]["items"][0]["id"] == "dof-5803022"
    assert nov5["markets"]["fix"]["value"] == 18.6285


def test_store_is_deterministic(tmp_path: Path) -> None:
    record = store.new_record(date(2026, 11, 1))
    record["markets"] = {"gas_lp": {"title": "x", "url": "https://a", "page": "https://b"}}
    record["authorities"] = []
    assert store.save(record, tmp_path)
    assert not store.save(json.loads(store.dumps(record)), tmp_path)
