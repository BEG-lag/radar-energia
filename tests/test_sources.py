"""Parsers of every source, against responses recorded on 2026-11-17."""

from __future__ import annotations

from datetime import date

import pytest

from radar_energia.http import FetchError
from radar_energia.sources import cenace, fuel, gobmx, sidof
from radar_energia.sources.gobmx import ARCHIVES_BY_KEY

from .conftest import fixture_bytes, fixture_json, fixture_text

# ------------------------------------------------------------------ SIDOF


def test_sidof_notes_keep_only_energy_items() -> None:
    record = sidof.parse_notes(fixture_json("sidof-notas-05-11-2026.json"), date(2026, 11, 5))
    assert record is not None
    assert record["source"] == "https://sidof.segob.gob.mx/dof/sidof/notas/05-11-2026"
    assert record["editions"] == ["matutina"]
    assert record["notes_reviewed"] == 11  # titled notes that are not avisos
    [item] = record["items"]
    assert item["id"] == "dof-5803022"
    assert item["issuer"] == "SECRETARIA DE ENERGIA"
    assert item["agencies"] == ["CNE"]
    assert item["subsectors"] == ["gas-natural", "petroliferos"]
    assert item["url"] == "https://dof.gob.mx/nota_detalle.php?codigo=5803022&fecha=05/11/2026"
    assert item["title"].startswith("Acuerdo de la Comisión Nacional de Energía")


def test_sidof_day_without_edition_is_none() -> None:
    assert (
        sidof.parse_notes(fixture_json("sidof-notas-15-11-2026.json"), date(2026, 11, 15)) is None
    )


def test_sidof_fix_series() -> None:
    values = sidof.parse_fix(fixture_json("sidof-fix.json"))
    assert values[date(2026, 11, 17)] == 18.5525
    assert values[date(2026, 11, 13)] == 18.6188
    assert len(values) == 8  # the UDIS row (code 159) is ignored
    assert list(values) == sorted(values)
    assert sidof.fix_record(date(2026, 11, 17), 18.5525)["source"].endswith(
        "/indicadores/17-11-2026"
    )


def test_sidof_urls() -> None:
    assert sidof.fix_url(date(2026, 8, 1), date(2026, 11, 17)).endswith(
        "/indicadores/158/01-08-2026/17-11-2026"
    )


# ------------------------------------------------------------------ CENACE


def test_cenace_daily_statistics() -> None:
    days = cenace.parse(fixture_json("cenace-pend-sin.json"), "SIN")
    assert sorted(days) == [date(2026, 11, 17), date(2026, 11, 18)]
    monterrey = next(r for r in days[date(2026, 11, 17)] if r["zone"] == "MONTERREY")
    assert monterrey == {
        "system": "SIN",
        "zone": "MONTERREY",
        "name": "Monterrey",
        "avg": 603.32,
        "min": 388.62,
        "max": 1410.82,
        "hours": 24,
        "source": "https://ws01.cenace.gob.mx:8082/SWPEND/SIM/SIN/MDA/MONTERREY/2026/11/17/2026/11/17/JSON",
    }


def test_cenace_error_payload_raises() -> None:
    with pytest.raises(FetchError, match="7 dias"):
        cenace.parse({"Message": "No se pueden mostrar datos con un lapso mayor a 7 dias."}, "SIN")


def test_cenace_requests_stay_within_seven_days() -> None:
    spans = cenace.chunks(date(2026, 8, 20), date(2026, 11, 17))
    assert all((end - start).days < cenace.MAX_DAYS for start, end in spans)
    assert spans[0][0] == date(2026, 8, 20)
    assert spans[-1][1] == date(2026, 11, 17)
    assert len(spans) == 13


def test_cenace_zone_codes_have_no_spaces() -> None:
    assert all(" " not in zone.code for zone in cenace.ZONES)


# ------------------------------------------------------------------ fuel prices


def test_fuel_summary_drops_placeholders() -> None:
    summary = fuel.parse(fixture_bytes("fuel-prices.xml"))
    assert summary["stations"] == 42
    diesel = summary["products"]["diesel"]
    assert diesel["excluded"] == 2  # two stations report 0.01
    assert diesel["median"] == 26.99
    assert summary["products"]["regular"]["median"] == 23.95
    assert all(fuel.PLAUSIBLE[0] <= p["p10"] <= p["p90"] for p in summary["products"].values())


def test_fuel_rejects_invalid_xml() -> None:
    with pytest.raises(FetchError):
        fuel.parse(b"<html>maintenance</html")
    with pytest.raises(FetchError):
        fuel.parse(b"<places></places>")


# ------------------------------------------------------------------ gob.mx


def test_gobmx_press_archive() -> None:
    entries = gobmx.parse_archive(
        fixture_text("gobmx-cne-prensa.html"), ARCHIVES_BY_KEY["cne:prensa"]
    )
    assert len(entries) == 9
    first = entries[0]
    assert first["published"] == "2026-11-06T12:25:00-06:00"
    assert first["kind"] == "Comunicado"
    assert first["agency"] == "CNE"
    assert first["url"].startswith("https://www.gob.mx/cne/prensa/cne-aprueba-seis-permisos")
    assert "?" not in first["url"]
    assert first["title"].startswith("CNE aprueba seis permisos para proyectos fotovoltaicos")


def test_gobmx_documents_use_time_date_attribute() -> None:
    entries = gobmx.parse_archive(
        fixture_text("gobmx-cne-documentos.html"), ARCHIVES_BY_KEY["cne:documentos"]
    )
    assert entries[0]["id"] == "gobmx-cne-documentos-sesion-del-mes-de-noviembre-de-2026"
    assert entries[0]["published"] == "2026-11-06T19:42:00-06:00"
    assert entries[0]["kind"] == "Documento"
    kept = [item for e in entries if (item := gobmx.classify_item(e))]
    assert len(kept) < len(entries)  # the privacy notice is housekeeping
    assert all(item["agencies"][0] == "CNE" and item["subsectors"] for item in kept)


def test_gobmx_out_of_order_archive_is_parsed_whole() -> None:
    entries = gobmx.parse_archive(
        fixture_text("gobmx-sener-prensa.html"), ARCHIVES_BY_KEY["sener:prensa"]
    )
    assert entries[0]["published"].startswith("2026-03-17")
    assert entries[1]["published"].startswith("2021-")


def test_gobmx_unreadable_page_yields_nothing() -> None:
    assert gobmx.parse_archive("<html><body>Mantenimiento</body></html>", gobmx.ARCHIVES[0]) == []


def test_gas_lp_latest_pdf() -> None:
    record = gobmx.parse_gas_lp(fixture_text("gobmx-gas-lp.html"))
    assert record == {
        "title": "PRECIOS MÁXIMOS VIGENTES DEL 15 AL 21 DE NOVIEMBRE DE 2026",
        "url": "https://www.gob.mx/cms/uploads/attachment/file/1116604/PRECIOS_MAXIMOS_VIGENTES_DEL_15_al_21_DE_NOVIEMBRE_DE_2026.pdf",
        "page": gobmx.GAS_LP_PAGE,
        "valid_from": "2026-11-15",
        "valid_to": "2026-11-21",
    }


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("PRECIOS MÁXIMOS VIGENTES DEL 25 AL 31 DE OCTUBRE DE 2026", ("2026-10-25", "2026-10-31")),
        (
            "PRECIOS MÁXIMOS VIGENTES DEL 29 DE NOVIEMBRE AL 5 DE DICIEMBRE DE 2026",
            ("2026-11-29", "2026-12-05"),
        ),
        (
            "PRECIOS MÁXIMOS VIGENTES DEL 27 DE DICIEMBRE AL 2 DE ENERO DE 2027",
            ("2026-12-27", "2027-01-02"),
        ),
        ("PRECIOS MÁXIMOS VIGENTES", None),
    ],
)
def test_gas_lp_validity(label: str, expected: tuple[str, str] | None) -> None:
    span = gobmx.validity(label)
    assert (None if span is None else tuple(d.isoformat() for d in span)) == expected
