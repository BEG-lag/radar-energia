"""Site build and feeds, built from the committed data into a temporary directory."""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from radar_energia.rules import SUBSECTORS
from radar_energia.site import build_site, sparkline

from .conftest import ROOT

ATOM = "{http://www.w3.org/2005/Atom}"
EM_DASH = chr(0x2014)
CREDIT = 'Radar elaborado por Benjamín Esponda García · <a href="https://pivotek.mx">PIVOTEK</a>'
DISCLAIMER = (
    "Información pública recopilada automáticamente. No constituye asesoría legal."
    " Solo el DOF y las autoridades emisoras son fuente oficial."
)


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("build")
    shutil.copytree(ROOT / "data", base / "data")
    build_site(base / "data", base / "docs")
    return base / "docs"


def test_page_has_credit_disclaimer_and_no_third_party_assets(site: Path) -> None:
    html = (site / "index.html").read_text(encoding="utf-8")
    assert CREDIT in html
    assert DISCLAIMER in html
    assert "{{" not in html
    for host in ("googleapis", "cdnjs", "jsdelivr", "unpkg", "googletagmanager", "analytics"):
        assert host not in html
    assert 'lang="es-MX"' in html


def test_committed_site_is_up_to_date(site: Path) -> None:
    for relative in ("index.html", "data/items.json", "data/latest.json", "feed.xml"):
        assert (site / relative).read_text(encoding="utf-8") == (
            ROOT / "docs" / relative
        ).read_text(encoding="utf-8"), f"docs/{relative} is stale: run `uv run radar-energia build`"


def test_items_index(site: Path) -> None:
    items = json.loads((site / "data" / "items.json").read_text(encoding="utf-8"))
    assert items
    assert [i["d"] for i in items] == sorted((i["d"] for i in items), reverse=True)
    for item in items:
        assert item["u"].startswith("https://")
        assert item["src"] in {"dof", "gobmx"}
        assert item["ss"]


def test_feeds_are_valid_atom(site: Path) -> None:
    root = ET.parse(site / "feed.xml").getroot()
    assert root.tag == f"{ATOM}feed"
    entries = root.findall(f"{ATOM}entry")
    assert 0 < len(entries) <= 100
    ids = [e.findtext(f"{ATOM}id") for e in entries]
    assert len(ids) == len(set(ids))
    assert root.findtext(f"{ATOM}updated") == max(e.findtext(f"{ATOM}updated") for e in entries)
    for entry in entries:
        assert entry.find(f"{ATOM}link").get("href").startswith("https://")
    for subsector in SUBSECTORS:
        feed = ET.parse(site / "feeds" / f"{subsector.key}.xml").getroot()
        for entry in feed.findall(f"{ATOM}entry"):
            terms = {c.get("term") for c in entry.findall(f"{ATOM}category")}
            assert subsector.key in terms


def test_build_is_deterministic(site: Path, tmp_path: Path) -> None:
    shutil.copytree(ROOT / "data", tmp_path / "data")
    summary = build_site(tmp_path / "data", site)
    assert summary["changed"] == []


def test_sparkline() -> None:
    assert sparkline([1.0], "x") == ""
    svg = sparkline([1.0, 3.0, 2.0], "serie")
    assert svg.startswith("<svg")
    assert 'aria-label="serie"' in svg
    assert "polyline" in svg


def test_no_em_dash_in_authored_files() -> None:
    authored = [
        *ROOT.glob("*.md"),
        *(ROOT / "docs").glob("*.md"),
        *(ROOT / "docs" / "assets").glob("*.[cjs]*"),
        *(ROOT / "src").rglob("*.py"),
        *(ROOT / "src").rglob("*.html"),
        *(ROOT / "tests").glob("*.py"),
        *(ROOT / "scripts").glob("*"),
        *(ROOT / ".github").rglob("*.yml"),
    ]
    offenders = [p.name for p in authored if EM_DASH in p.read_text(encoding="utf-8")]
    assert offenders == []
