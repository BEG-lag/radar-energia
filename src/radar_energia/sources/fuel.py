"""Retail gasoline and diesel prices reported by service stations to the CNE.

The CNE page "Precios de gasolinas y diésel" (https://www.cne.gob.mx/ConsultaPrecios/
GasolinasyDiesel/GasolinasyDiesel.html) offers a direct download of one XML with the price
of every station, "actualizado diariamente a las 18:00 hrs". The XML has no date and no
history: each run stores a national summary of the snapshot it read, so the series starts
the day the radar starts.

Some stations report placeholder prices (0.01 MXN). Values outside ``PLAUSIBLE`` are
counted as excluded and left out of the statistics.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from statistics import mean, median, quantiles
from typing import Any

from ..http import FetchError, PoliteClient

PRICES_URL = "https://publicacionexterna.azurewebsites.net/publicaciones/prices"
PAGE_URL = "https://www.cne.gob.mx/ConsultaPrecios/GasolinasyDiesel/GasolinasyDiesel.html"
PLAUSIBLE = (5.0, 60.0)
"""MXN per litre. Wide on purpose: it only drops placeholders and typing errors."""
PRODUCTS = ("regular", "premium", "diesel")


def parse(xml: bytes) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml.lstrip(b"\xef\xbb\xbf"))
    except ET.ParseError as exc:
        raise FetchError(f"Fuel price XML could not be parsed: {exc}") from exc
    places = root.findall("place")
    prices: dict[str, list[float]] = {product: [] for product in PRODUCTS}
    excluded: dict[str, int] = dict.fromkeys(PRODUCTS, 0)
    for place in places:
        for node in place.findall("gas_price"):
            product = node.get("type")
            if product not in prices:
                continue
            try:
                value = float((node.text or "").strip())
            except ValueError:
                excluded[product] += 1
                continue
            if PLAUSIBLE[0] <= value <= PLAUSIBLE[1]:
                prices[product].append(value)
            else:
                excluded[product] += 1
    if not places or not any(prices.values()):
        raise FetchError("Fuel price XML has no stations")
    summary: dict[str, Any] = {
        "stations": len(places),
        "unit": "MXN/l",
        "source": PRICES_URL,
        "products": {},
    }
    for product, values in prices.items():
        if not values:
            continue
        deciles = quantiles(values, n=10, method="inclusive") if len(values) > 1 else values * 9
        summary["products"][product] = {
            "median": round(median(values), 2),
            "mean": round(mean(values), 2),
            "p10": round(deciles[0], 2),
            "p90": round(deciles[-1], 2),
            "stations": len(values),
            "excluded": excluded[product],
        }
    return summary


def fetch(client: PoliteClient) -> dict[str, Any]:
    response = client.get_ok(PRICES_URL, accept="application/xml,text/xml,*/*")
    return parse(response.content)
