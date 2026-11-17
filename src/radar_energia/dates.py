"""Date helpers. Mexico City has used UTC-6 all year since 2022 (no daylight saving)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MEXICO_CITY = ZoneInfo("America/Mexico_City")

MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def today_mx() -> date:
    return datetime.now(MEXICO_CITY).date()


def day_range(start: date, end: date) -> Iterator[date]:
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def dmy(day: date, sep: str = "-") -> str:
    """``DD-MM-YYYY`` (SIDOF paths) or ``DD/MM/YYYY`` (dof.gob.mx links)."""
    return f"{day.day:02d}{sep}{day.month:02d}{sep}{day.year}"


def parse_dmy(text: str) -> date:
    day, month, year = (int(part) for part in text.split("-"))
    return date(year, month, day)


def long_es(day: date, weekday: bool = False) -> str:
    text = f"{day.day} de {MONTHS_ES[day.month - 1]} de {day.year}"
    return f"{WEEKDAYS_ES[day.weekday()]} {text}" if weekday else text
