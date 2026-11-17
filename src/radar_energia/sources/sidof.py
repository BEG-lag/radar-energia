"""DOF tables of contents and the FIX exchange rate from the public SIDOF API.

Documented (unofficially) in https://github.com/BEG-lag/mcp-dof/blob/main/docs/api.md.
No account or token. ``Accept: application/json`` alone returns HTTP 406, so the client
sends ``*/*``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from ..classify import classify
from ..dates import dmy, parse_dmy
from ..http import FetchError, PoliteClient

BASE_URL = "https://sidof.segob.gob.mx/dof/sidof"
FIX_CODE = 158
"""``codTipoIndicador`` of the FIX exchange rate (DÓLAR) in SIDOF."""

EDITIONS: tuple[tuple[str, str], ...] = (
    ("NotasMatutinas", "matutina"),
    ("NotasVespertinas", "vespertina"),
    ("NotasExtraordinarias", "extraordinaria"),
)


def notes_url(day: date) -> str:
    return f"{BASE_URL}/notas/{dmy(day)}"


def fix_url(start: date, end: date) -> str:
    return f"{BASE_URL}/indicadores/{FIX_CODE}/{dmy(start)}/{dmy(end)}"


def official_url(note_id: int, day: date) -> str:
    return f"https://dof.gob.mx/nota_detalle.php?codigo={note_id}&fecha={dmy(day, '/')}"


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return None if value in {"", "null", "None"} else value
    return value


def _int(value: Any) -> int | None:
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def fetch_notes(client: PoliteClient, day: date) -> dict[str, Any]:
    response = client.get_ok(notes_url(day))
    payload = response.json()
    if payload.get("response") != "OK":
        raise FetchError(f"SIDOF answered {payload.get('response')!r} for {day}")
    return payload


def parse_notes(payload: Mapping[str, Any], day: date) -> dict[str, Any] | None:
    """Energy-related notes of one date, or ``None`` when no edition was published.

    Untitled rows (agency headers) and avisos judiciales y generales are skipped: avisos
    only carry codes such as ``Aviso REF:581596`` as titles.
    """
    editions: list[str] = []
    reviewed = 0
    items: list[dict[str, Any]] = []
    for key, edition in EDITIONS:
        rows = [row for row in payload.get(key) or [] if _clean(row.get("titulo"))]
        if not rows:
            continue
        editions.append(edition)
        rows.sort(key=lambda row: (float(_clean(row.get("orden")) or 0), _int(row.get("codNota"))))
        for row in rows:
            note_id = _int(row.get("codNota"))
            branch = _clean(row.get("codOrgaUno"))
            if note_id is None or _clean(row.get("tipoNota")) == "AVISO" or branch == "AV":
                continue
            reviewed += 1
            title = " ".join(_clean(row["titulo"]).split())
            issuer = _clean(row.get("codOrgaDos"))
            result = classify(title, issuer)
            if not result.relevant:
                continue
            raw_day = _clean(row.get("fecha"))
            note_day = datetime.strptime(raw_day, "%d-%m-%Y").date() if raw_day else day
            items.append(
                {
                    "id": f"dof-{note_id}",
                    "dof_id": note_id,
                    "edition": edition,
                    "issuer": issuer,
                    "title": title,
                    "url": official_url(note_id, note_day),
                    "subsectors": list(result.subsectors),
                    "agencies": list(result.agencies),
                    "matched": list(result.matched),
                }
            )
    if not editions:
        return None
    return {
        "source": notes_url(day),
        "editions": editions,
        "notes_reviewed": reviewed,
        "items": items,
    }


def fetch_fix(client: PoliteClient, start: date, end: date) -> dict[str, Any]:
    response = client.get_ok(fix_url(start, end))
    payload = response.json()
    if payload.get("response") != "OK":
        raise FetchError(f"SIDOF indicators answered {payload.get('response')!r}")
    return payload


def parse_fix(payload: Mapping[str, Any]) -> dict[date, float]:
    """FIX values keyed by their DOF publication date.

    The FIX published on a date is the rate Banco de México determined the business day
    before, as the DOF note itself says.
    """
    values: dict[date, float] = {}
    for row in payload.get("ListaIndicadores") or []:
        if _int(row.get("codTipoIndicador")) != FIX_CODE:
            continue
        raw = str(row.get("valor", "")).replace("%", "").replace(",", "").strip()
        try:
            values[parse_dmy(row["fecha"])] = float(raw)
        except (KeyError, ValueError):
            continue
    return dict(sorted(values.items()))


def fix_record(day: date, value: float) -> dict[str, Any]:
    return {
        "value": value,
        "unit": "MXN/USD",
        "source": f"{BASE_URL}/indicadores/{dmy(day)}",
    }
