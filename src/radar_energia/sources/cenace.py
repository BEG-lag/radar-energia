"""Day-ahead (MDA) prices of load zones from CENACE's public SW-PEND web service.

``https://ws01.cenace.gob.mx:8082/SWPEND/SIM/{system}/{process}/{zones}/{y}/{m}/{d}/{y}/{m}/{d}/JSON``

No registration. Verified limits: at most 7 days per request (HTTP 400 otherwise) and zone
names with spaces (for example ``VDM CENTRO``) cannot be requested through the URL, so the
radar follows zones whose names have none. Prices are in MXN/MWh, one value per hour.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Any

from ..http import FetchError, PoliteClient

BASE_URL = "https://ws01.cenace.gob.mx:8082/SWPEND/SIM"
MAX_DAYS = 7


@dataclass(frozen=True)
class Zone:
    system: str
    code: str
    name: str


ZONES: tuple[Zone, ...] = (
    Zone("SIN", "MONTERREY", "Monterrey"),
    Zone("SIN", "GUADALAJARA", "Guadalajara"),
    Zone("SIN", "PUEBLA", "Puebla"),
    Zone("SIN", "MERIDA", "Mérida"),
    Zone("SIN", "HERMOSILLO", "Hermosillo"),
    Zone("BCA", "MEXICALI", "Mexicali"),
)


def url(system: str, codes: Iterable[str], start: date, end: date, process: str = "MDA") -> str:
    span = (
        f"{start.year}/{start.month:02d}/{start.day:02d}/{end.year}/{end.month:02d}/{end.day:02d}"
    )
    return f"{BASE_URL}/{system}/{process}/{','.join(codes)}/{span}/JSON"


def chunks(start: date, end: date, size: int = MAX_DAYS) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    day = start
    while day <= end:
        last = min(day + timedelta(days=size - 1), end)
        out.append((day, last))
        day = last + timedelta(days=1)
    return out


def parse(payload: Mapping[str, Any], system: str) -> dict[date, list[dict[str, Any]]]:
    """Daily average, minimum and maximum of the hourly zone price, keyed by operating day."""
    if "Resultados" not in payload:
        raise FetchError(f"SW-PEND answered without results: {payload.get('Message', payload)}")
    names = {zone.code: zone.name for zone in ZONES}
    hourly: dict[tuple[date, str], list[float]] = defaultdict(list)
    for result in payload.get("Resultados") or []:
        code = str(result.get("zona_carga", ""))
        for value in result.get("Valores") or []:
            try:
                hourly[(date.fromisoformat(value["fecha"]), code)].append(float(value["pz"]))
            except (KeyError, TypeError, ValueError):
                continue
    days: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for (day, code), prices in sorted(hourly.items()):
        days[day].append(
            {
                "system": system,
                "zone": code,
                "name": names.get(code, code.title()),
                "avg": round(mean(prices), 2),
                "min": round(min(prices), 2),
                "max": round(max(prices), 2),
                "hours": len(prices),
                "source": url(system, [code], day, day),
            }
        )
    return dict(days)


def fetch(client: PoliteClient, start: date, end: date) -> dict[date, list[dict[str, Any]]]:
    """Zone prices for every operating day between ``start`` and ``end``."""
    by_system: dict[str, list[str]] = defaultdict(list)
    for zone in ZONES:
        by_system[zone.system].append(zone.code)
    order = {(zone.system, zone.code): i for i, zone in enumerate(ZONES)}
    days: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for system, codes in by_system.items():
        for first, last in chunks(start, end):
            response = client.get(url(system, codes, first, last))
            if response.status_code != 200:
                raise FetchError(f"SW-PEND HTTP {response.status_code}: {response.text[:200]}")
            for day, rows in parse(response.json(), system).items():
                days[day].extend(rows)
    return {
        day: sorted(rows, key=lambda r: order.get((r["system"], r["zone"]), 99))
        for day, rows in sorted(days.items())
    }
