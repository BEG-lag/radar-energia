"""Build the static site in ``docs/`` from the day files in ``data/``.

Today's radar, the market cards and the 30-day archive are rendered here, in Python, so
the page works without JavaScript. ``docs/assets/app.js`` only adds search, filters, the
English toggle and copy buttons. The output is deterministic: it depends on the data, not
on the build time.
"""

from __future__ import annotations

import json
import math
import zlib
from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import Any

from . import __version__, store
from .aggregates import (
    Change,
    flat_items,
    fuel_series,
    last_change,
    month_bounds,
    subsector_counts,
    week_bounds,
    zone_series,
)
from .aggregates import fix_series as get_fix_series
from .dates import MONTHS_ES, WEEKDAYS_ES, long_es
from .feeds import SITE_URL, all_feeds
from .rules import AGENCIES, SUBSECTORS
from .sources import SOURCES
from .sources.cenace import ZONES
from .sources.fuel import PAGE_URL as FUEL_PAGE
from .sources.fuel import PRICES_URL as FUEL_XML

ARCHIVE_DAYS = 30
AUTHORITY_ITEMS = 10
FIX_POINTS = 60
ZONE_POINTS = 30
REPO_URL = "https://github.com/BEG-lag/radar-energia"
SS_LABEL = {s.key: s.label_es for s in SUBSECTORS}
AGENCY_NAME = {a.key: a.name for a in AGENCIES}
EDITION_LABEL = {"matutina": "Matutina", "vespertina": "Vespertina", "extraordinaria": "Extra"}
PRODUCT_LABEL = {"regular": "Gasolina regular", "premium": "Gasolina premium", "diesel": "Diésel"}


def e(value: Any) -> str:
    return escape(str(value), quote=True)


def short_es(day: date) -> str:
    return f"{day.day} {MONTHS_ES[day.month - 1][:3]}"


def time_tag(iso: str, fmt: str = "long") -> str:
    day = date.fromisoformat(iso[:10])
    if fmt == "short":
        text = short_es(day)
    elif fmt == "weekday":
        text = long_es(day, weekday=True)
    else:
        text = long_es(day)
    return f'<time datetime="{e(iso[:10])}" data-fmt="{fmt}">{e(text)}</time>'


def money(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


# ---------------------------------------------------------------- sparklines


def sparkline(values: Sequence[float], label: str, width: int = 132, height: int = 36) -> str:
    """Inline SVG sparkline. Decorative: the numbers are always printed next to it."""
    if len(values) < 2:
        return ""
    low, high = min(values), max(values)
    span = (high - low) or 1.0
    pad = 3
    step = (width - 2 * pad) / (len(values) - 1)
    points = [
        (pad + i * step, pad + (height - 2 * pad) * (1 - (v - low) / span))
        for i, v in enumerate(values)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = f"{pad:.1f},{height - pad:.1f} {line} {points[-1][0]:.1f},{height - pad:.1f}"
    last_x, last_y = points[-1]
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" width="{width}" height="{height}"'
        f' role="img" aria-label="{e(label)}" focusable="false">'
        f'<polygon class="spark-area" points="{area}"/>'
        f'<polyline class="spark-line" points="{line}"/>'
        f'<circle class="spark-dot" cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.6"/></svg>'
    )


def change_badge(change: Change | None, decimals: int = 2, unit: str = "") -> str:
    if change is None or change.delta is None:
        return '<span class="delta flat" data-i18n="mk.first">primera lectura</span>'
    delta = change.delta
    if round(delta, decimals) == 0:
        return '<span class="delta flat"><span aria-hidden="true">=</span> <span data-i18n="mk.nochange">sin cambio</span></span>'
    arrow, cls = ("▲", "up") if delta > 0 else ("▼", "down")
    pct = f" ({change.pct:+.2f}%)" if change.pct is not None else ""
    return (
        f'<span class="delta {cls}"><span aria-hidden="true">{arrow}</span> '
        f"{delta:+,.{decimals}f}{unit}{pct}</span>"
    )


# ---------------------------------------------------------------- item cards


def chips(item: dict[str, Any]) -> str:
    parts = [
        f'<li class="chip ss-{e(s)}" data-i18n="ss.{e(s)}">{e(SS_LABEL[s])}</li>'
        for s in item["subsectors"]
    ]
    parts += [
        f'<li class="chip agency" title="{e(AGENCY_NAME[a])}">{e(a)}</li>' for a in item["agencies"]
    ]
    return f'<ul class="chips" aria-label="Clasificación">{"".join(parts)}</ul>'


def item_card(item: dict[str, Any], show_date: bool = False) -> str:
    if item["source"] == "dof":
        edition = item["edition"]
        origin = (
            '<span class="src src-dof">DOF</span>'
            f'<span class="meta-ed" data-i18n="ed.{e(edition)}">{e(EDITION_LABEL[edition])}</span>'
            f'<span class="meta-iss">{e(item.get("issuer") or "")}</span>'
        )
    else:
        origin = (
            f'<span class="src src-{e(item["agency"].lower())}">{e(item["agency"])}</span>'
            f'<span class="meta-ed">{e(item["kind"])}</span>'
            '<span class="meta-iss">gob.mx</span>'
        )
    when = f'<span class="meta-date">{time_tag(item["date"], "short")}</span>' if show_date else ""
    matched = ", ".join(item.get("matched", []))
    rules = (
        f'<p class="rules"><span data-i18n="item.rules">reglas</span>: {e(matched)}</p>'
        if matched
        else ""
    )
    return (
        '<li class="item">'
        f'<p class="meta">{origin}{when}</p>'
        f'<h3 class="item-title"><a href="{e(item["url"])}" rel="noopener">{e(item["title"])}</a></h3>'
        f"{chips(item)}{rules}</li>"
    )


def item_list(items: Iterable[dict[str, Any]], show_date: bool = False) -> str:
    cards = "".join(item_card(i, show_date) for i in items)
    return f'<ul class="items">{cards}</ul>'


# ---------------------------------------------------------------- sections


def render_dof(records: list[dict[str, Any]], latest: date) -> str:
    today = next((r for r in records if r["date"] == latest.isoformat()), None)
    dof_today = today.get("dof") if today else None
    out: list[str] = []
    if dof_today:
        n_items, reviewed = len(dof_today["items"]), dof_today["notes_reviewed"]
        editions = ", ".join(dof_today["editions"])
        out.append(
            f'<p class="lede"><strong data-i18n="dof.today.count" data-n="{n_items}">'
            f"{n_items} {'publicación' if n_items == 1 else 'publicaciones'} de energía</strong>"
            f' <span data-i18n="dof.today.of" data-n="{reviewed}">de {reviewed} notas revisadas</span>'
            f' <span class="muted">(<span data-i18n="dof.editions">ediciones</span>: {e(editions)})</span>.</p>'
        )
        if dof_today["items"]:
            items = [{**i, "date": latest.isoformat(), "source": "dof"} for i in dof_today["items"]]
            out.append(item_list(items))
        else:
            out.append(
                '<p class="empty" data-i18n="dof.today.none">El DOF de hoy no trae publicaciones'
                " de energía. Abajo, las más recientes.</p>"
            )
    else:
        out.append(
            '<p class="empty" data-i18n="dof.today.noedition">Hoy no hay edición del DOF'
            " (o aún no se publica). Abajo, lo más reciente.</p>"
        )
    if not (dof_today and dof_today["items"]):
        previous = next(
            (
                r
                for r in reversed(records)
                if r["date"] < latest.isoformat() and r.get("dof") and r["dof"]["items"]
            ),
            None,
        )
        if previous:
            items = [
                {**i, "date": previous["date"], "source": "dof"} for i in previous["dof"]["items"]
            ]
            out.append(
                f'<h3 class="sub"><span data-i18n="dof.latest">Último DOF con publicaciones de energía</span>:'
                f" {time_tag(previous['date'], 'weekday')}</h3>"
            )
            out.append(item_list(items))
    return "".join(out)


def render_authorities(items: list[dict[str, Any]], latest: date) -> str:
    recent = [i for i in items if i["source"] == "gobmx"][:AUTHORITY_ITEMS]
    if not recent:
        return '<p class="empty" data-i18n="auth.none">Sin publicaciones recientes.</p>'
    return item_list(recent, show_date=True)


def render_markets(records: list[dict[str, Any]], latest: date) -> str:
    cards: list[str] = []
    wide: list[str] = []
    fix = get_fix_series(records)
    change = last_change(fix)
    if change:
        values = [v for _, v in fix[-FIX_POINTS:]]
        cards.append(
            '<article class="card mk mk-fix">'
            '<h3 class="mk-title"><span data-i18n="mk.fix">Tipo de cambio FIX</span>'
            '<span class="unit">MXN/USD</span></h3>'
            f'<p class="mk-value">{change.value:.4f}</p>'
            f"<p>{change_badge(change, 4)}</p>"
            f"{sparkline(values, f'FIX, últimos {len(values)} datos: mínimo {min(values):.4f}, máximo {max(values):.4f}', 300, 64)}"
            f'<p class="mk-foot"><span data-i18n="mk.fix.pub">Publicado en el DOF el</span> {time_tag(change.date, "short")}.'
            f' <a href="{e(records_value(records, "fix", change.date)["source"])}" rel="noopener" data-i18n="mk.source">Fuente</a></p>'
            "</article>"
        )

    zones = zone_series(records)
    zone_cards: list[str] = []
    operating = None
    for zone in ZONES:
        series = zones.get(f"{zone.system}:{zone.code}")
        if not series:
            continue
        points = [p for p in series["points"] if p[0] <= latest.isoformat()]
        change = last_change(points)
        if not change:
            continue
        operating = change.date
        values = [v for _, v in points[-ZONE_POINTS:]]
        row = zone_row(records, change.date, zone.system, zone.code)
        zone_cards.append(
            '<li class="zone">'
            f'<p class="zone-name">{e(zone.name)} <span class="sys">{e(zone.system)}</span></p>'
            f'<p class="zone-value">${money(change.value)}</p>'
            f"<p>{change_badge(change)}</p>"
            f"{sparkline(values, f'{zone.name}, {len(values)} días: mínimo {min(values):,.0f}, máximo {max(values):,.0f}', 110, 30)}"
            f'<p class="zone-range"><span data-i18n="mk.range">rango horario</span> {money(row["min"], 0)}–{money(row["max"], 0)}'
            f' · <a href="{e(row["source"])}" rel="noopener">JSON</a></p>'
            "</li>"
        )
    if zone_cards:
        wide.append(
            '<article class="card mk mk-zones">'
            '<h3 class="mk-title"><span data-i18n="mk.pz">Precio de zona de carga, MDA</span>'
            '<span class="unit">MXN/MWh</span></h3>'
            f'<p class="mk-note"><span data-i18n="mk.pz.note">Promedio simple de las 24 horas del día de operación</span>'
            f" {time_tag(operating or latest.isoformat(), 'short')}. CENACE, SW-PEND.</p>"
            f'<ul class="zones">{"".join(zone_cards)}</ul></article>'
        )

    fuel = fuel_series(records)
    latest_fuel = next(
        (r["markets"]["fuel"] for r in reversed(records) if r.get("markets", {}).get("fuel")), None
    )
    if latest_fuel:
        rows = []
        for product in ("regular", "premium", "diesel"):
            series = fuel.get(product)
            stats = latest_fuel["products"].get(product)
            if not series or not stats:
                continue
            change = last_change(series)
            values = [v for _, v in series[-60:]]
            rows.append(
                '<li class="zone">'
                f'<p class="zone-name" data-i18n="fuel.{product}">{e(PRODUCT_LABEL[product])}</p>'
                f'<p class="zone-value">${stats["median"]:.2f}</p>'
                f"<p>{change_badge(change)}</p>"
                f"{sparkline(values, f'{PRODUCT_LABEL[product]}, mediana nacional', 110, 30)}"
                f'<p class="zone-range">p10 {stats["p10"]:.2f} · p90 {stats["p90"]:.2f} · '
                f'{stats["stations"]:,} <span data-i18n="fuel.stations">estaciones</span></p></li>'
            )
        first = fuel["regular"][0][0] if fuel.get("regular") else latest.isoformat()
        wide.append(
            '<article class="card mk mk-fuel">'
            '<h3 class="mk-title"><span data-i18n="mk.fuel">Gasolinas y diésel, mediana nacional</span>'
            '<span class="unit">MXN/l</span></h3>'
            f'<p class="mk-note"><span data-i18n="mk.fuel.note">Precios que las estaciones reportan a la CNE. La fuente no guarda histórico: la serie empieza el</span> {time_tag(first, "short")}.'
            f' <a href="{e(FUEL_PAGE)}" rel="noopener" data-i18n="mk.source">Fuente</a> ·'
            f' <a href="{e(FUEL_XML)}" rel="noopener">XML</a></p>'
            f'<ul class="zones">{"".join(rows)}</ul></article>'
        )

    gas_lp = next(
        (r["markets"]["gas_lp"] for r in reversed(records) if r.get("markets", {}).get("gas_lp")),
        None,
    )
    if gas_lp:
        cards.append(
            '<article class="card mk mk-doc">'
            '<h3 class="mk-title"><span data-i18n="mk.gaslp">Gas LP, precios máximos</span>'
            '<span class="unit">CNE</span></h3>'
            f'<p class="doc-title"><a href="{e(gas_lp["url"])}" rel="noopener">{e(gas_lp["title"])}</a> <span class="muted">(PDF)</span></p>'
            f'<p class="mk-note" data-i18n="mk.gaslp.note">Tabla oficial por región y medio de venta. El radar enlaza el PDF vigente; no extrae cifras.</p>'
            f'<p class="mk-foot"><a href="{e(gas_lp["page"])}" rel="noopener" data-i18n="mk.gaslp.all">Todas las semanas</a></p>'
            "</article>"
        )

    manual = [s for s in SOURCES if s.status == "rojo"]
    manual_items = "".join(
        f'<li><a href="{e(s.url)}" rel="noopener" data-en="{e(s.name_en)}">{e(s.name_es)}</a> <span class="muted">({e(s.publisher)})</span>'
        f'<br><span class="why" data-en="{e(s.use_en)}">{e(s.use_es)}</span></li>'
        for s in manual
    )
    cards.append(
        '<article class="card mk mk-manual">'
        '<h3 class="mk-title"><span data-i18n="mk.manual">Consulta manual</span>'
        '<span class="unit pill rojo">ROJO</span></h3>'
        '<p class="mk-note" data-i18n="mk.manual.note">Referencias que no se pueden leer de forma automática y confiable. El radar no las raspa: aquí está la liga oficial.</p>'
        f'<ul class="manual">{manual_items}</ul></article>'
    )
    return "".join(cards + wide)


def records_value(records: list[dict[str, Any]], key: str, day: str) -> dict[str, Any]:
    record = next(r for r in records if r["date"] == day)
    return record["markets"][key]


def zone_row(records: list[dict[str, Any]], day: str, system: str, code: str) -> dict[str, Any]:
    rows = records_value(records, "zonal_prices", day)
    return next(r for r in rows if r["system"] == system and r["zone"] == code)


def render_pulse(items: list[dict[str, Any]], latest: date) -> str:
    blocks = []
    for key, (start, end), label in (
        ("week", week_bounds(latest), "Esta semana"),
        ("month", month_bounds(latest), "Este mes"),
    ):
        counts = subsector_counts(items, start, end)
        top = max(counts.values()) or 1
        bars = "".join(
            f'<li><span class="bar-label" data-i18n="ss.{e(k)}">{e(SS_LABEL[k])}</span>'
            f'<span class="bar"><span class="bar-fill ss-{e(k)}" style="width:{max(v / top * 100, 2 if v else 0):.0f}%"></span></span>'
            f'<span class="bar-n">{v}</span></li>'
            for k, v in counts.items()
        )
        total = sum(1 for i in items if start.isoformat() <= i["date"] <= end.isoformat())
        blocks.append(
            f'<article class="card pulse"><h3 class="mk-title"><span data-i18n="pulse.{key}">{label}</span>'
            f'<span class="unit">{time_tag(start.isoformat(), "short")} <span data-i18n="w.to">a</span> {time_tag(min(end, latest).isoformat(), "short")}</span></h3>'
            f'<p class="pulse-total"><strong>{total}</strong> <span data-i18n="pulse.items" data-n="{total}">'
            f"{'publicación' if total == 1 else 'publicaciones'}</span></p>"
            f'<ul class="bars">{bars}</ul></article>'
        )
    return "".join(blocks)


def render_archive(items: list[dict[str, Any]], latest: date) -> str:
    since = (latest - timedelta(days=ARCHIVE_DAYS - 1)).isoformat()
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if since <= item["date"] <= latest.isoformat():
            groups.setdefault(item["date"], []).append(item)
    out = []
    for day, day_items in groups.items():
        out.append(
            f'<section class="day" aria-labelledby="d-{e(day)}"><h3 class="day-title" id="d-{e(day)}">'
            f'{time_tag(day, "weekday")} <span class="muted">· {len(day_items)}</span></h3>'
            f"{item_list(day_items)}</section>"
        )
    return "".join(out) or '<p class="empty" data-i18n="archive.none">Sin publicaciones.</p>'


def render_feeds() -> str:
    links = [("feed.xml", "Todo el radar", "all")] + [
        (f"feeds/{s.key}.xml", s.label_es, f"ss.{s.key}") for s in SUBSECTORS
    ]
    rows = "".join(
        f'<li><span class="feed-name" data-i18n="{"feed.all" if key == "all" else key}">{e(label)}</span>'
        f' <a class="feed-url" href="{e(path)}">{e(SITE_URL + path)}</a>'
        f' <button type="button" class="copy" data-copy="{e(SITE_URL + path)}" data-i18n="feed.copy">Copiar</button></li>'
        for path, label, key in links
    )
    return f'<ul class="feeds">{rows}</ul>'


def render_sources() -> str:
    rows = "".join(
        f'<tr><td><span class="pill {e(s.status)}">{e(s.status.upper())}</span></td>'
        f'<td><a href="{e(s.url)}" rel="noopener" data-en="{e(s.name_en)}">{e(s.name_es)}</a><br><span class="muted">{e(s.publisher)}</span></td>'
        f'<td data-en="{e(s.use_en)}">{e(s.use_es)}</td></tr>'
        for s in SOURCES
    )
    return (
        '<div class="table-wrap"><table class="sources"><thead><tr>'
        '<th scope="col" data-i18n="src.status">Estado</th>'
        '<th scope="col" data-i18n="src.source">Fuente</th>'
        '<th scope="col" data-i18n="src.use">Uso en el radar</th>'
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def options() -> tuple[str, str]:
    ss = "".join(
        f'<option value="{e(s.key)}" data-i18n="ss.{e(s.key)}">{e(s.label_es)}</option>'
        for s in SUBSECTORS
    )
    ag = "".join(f'<option value="{e(a.key)}">{e(a.key)}</option>' for a in AGENCIES)
    return ss, ag


# ---------------------------------------------------------------- hero radar

RADAR_COLORS = {
    "electricidad": "#cfff45",
    "hidrocarburos": "#ff5d47",
    "gas-natural": "#7fd8ff",
    "petroliferos": "#ffb648",
    "renovables": "#8ff0a4",
    "mineria": "#c9a7ff",
    "general": "#969dab",
}
RADAR_SHORT = {
    "electricidad": "ELEC",
    "hidrocarburos": "HC",
    "gas-natural": "GAS",
    "petroliferos": "PETRO",
    "renovables": "RENOV",
    "mineria": "MIN",
    "general": "GRAL",
}


def radar_svg(items: list[dict[str, Any]], latest: date, days: int = ARCHIVE_DAYS) -> str:
    """Hero graphic drawn from the data: one blip per item of the last ``days`` days.

    The angle is the item's first subsector, the distance from the centre its age.
    """
    size, centre, inner, outer = 360, 180, 26, 150
    keys = [s.key for s in SUBSECTORS]
    sector = 360 / len(keys)
    since = latest - timedelta(days=days - 1)
    parts = [
        f'<svg class="radar" viewBox="0 0 {size} {size}" role="img" aria-labelledby="radar-t">',
        '<title id="radar-t">Radar de los últimos 30 días: cada punto es una publicación,'
        " el ángulo es su subsector y la distancia al centro, su antigüedad.</title>",
        '<defs><linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#cfff45" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#cfff45" stop-opacity="0.35"/></linearGradient></defs>',
    ]
    for r in (outer, outer * 0.75, outer * 0.5, outer * 0.25):
        parts.append(f'<circle cx="{centre}" cy="{centre}" r="{r:.1f}" class="ring"/>')
    for index, key in enumerate(keys):
        angle = math.radians(index * sector - 90)
        x2, y2 = centre + outer * math.cos(angle), centre + outer * math.sin(angle)
        parts.append(
            f'<line x1="{centre}" y1="{centre}" x2="{x2:.1f}" y2="{y2:.1f}" class="spoke"/>'
        )
        mid = math.radians((index + 0.5) * sector - 90)
        lx, ly = centre + (outer + 16) * math.cos(mid), centre + (outer + 16) * math.sin(mid)
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" class="rim" fill="{RADAR_COLORS[key]}">{RADAR_SHORT[key]}</text>'
        )
    parts.append(
        f'<g class="sweep"><path d="M{centre} {centre} L{centre + outer} {centre} '
        f"A{outer} {outer} 0 0 0 {centre + outer * math.cos(math.radians(-40)):.1f} "
        f'{centre + outer * math.sin(math.radians(-40)):.1f} Z" fill="url(#sweep)"/></g>'
    )
    for item in items:
        day = date.fromisoformat(item["date"])
        if not since <= day <= latest:
            continue
        key = item["subsectors"][0]
        jitter = zlib.crc32(item["id"].encode()) % 1000 / 1000
        angle = math.radians((keys.index(key) + 0.12 + 0.76 * jitter) * sector - 90)
        radius = inner + (outer - inner - 6) * ((latest - day).days / max(days - 1, 1))
        x, y = centre + radius * math.cos(angle), centre + radius * math.sin(angle)
        fresh = " fresh" if (latest - day).days <= 1 else ""
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" class="blip{fresh}" fill="{RADAR_COLORS[key]}"/>'
        )
    parts.append(f'<circle cx="{centre}" cy="{centre}" r="4" fill="#cfff45"/></svg>')
    return "".join(parts)


# ---------------------------------------------------------------- data files


def compact(item: dict[str, Any]) -> dict[str, Any]:
    out = {
        "id": item["id"],
        "d": item["date"],
        "src": item["source"],
        "t": item["title"],
        "u": item["url"],
        "ss": item["subsectors"],
        "ag": item["agencies"],
        "m": item.get("matched", []),
    }
    if item["source"] == "dof":
        out["ed"] = item["edition"]
        out["iss"] = item.get("issuer") or ""
    else:
        out["by"] = item["agency"]
        out["k"] = item["kind"]
    return out


def market_json(records: list[dict[str, Any]]) -> dict[str, Any]:
    zones = zone_series(records)
    return {
        "fix": {"unit": "MXN/USD", "points": get_fix_series(records)},
        "zonal_prices": {
            "unit": "MXN/MWh",
            "process": "MDA",
            "statistic": "simple average of hourly prices",
            "zones": list(zones.values()),
        },
        "fuel_median": {"unit": "MXN/l", "products": fuel_series(records)},
    }


def change_json(change: Change | None) -> dict[str, Any] | None:
    if change is None:
        return None
    return {
        "date": change.date,
        "value": change.value,
        "previous_date": change.previous_date,
        "previous": change.previous,
        "delta": None if change.delta is None else round(change.delta, 4),
    }


def latest_json(
    records: list[dict[str, Any]], items: list[dict[str, Any]], latest: date
) -> dict[str, Any]:
    week = week_bounds(latest)
    month = month_bounds(latest)
    record = next((r for r in records if r["date"] == latest.isoformat()), None) or {}
    dof = record.get("dof")
    return {
        "version": __version__,
        "date": latest.isoformat(),
        "dof": None
        if not dof
        else {
            "editions": dof["editions"],
            "notes_reviewed": dof["notes_reviewed"],
            "energy_items": len(dof["items"]),
        },
        "items_total": len(items),
        "week": {
            "start": week[0].isoformat(),
            "end": week[1].isoformat(),
            "by_subsector": subsector_counts(items, *week),
        },
        "month": {
            "start": month[0].isoformat(),
            "end": month[1].isoformat(),
            "by_subsector": subsector_counts(items, *month),
        },
        "fix": change_json(last_change(get_fix_series(records))),
        "zonal_prices": {
            key: change_json(last_change([p for p in z["points"] if p[0] <= latest.isoformat()]))
            for key, z in zone_series(records).items()
        },
        "fuel_median": {k: change_json(last_change(v)) for k, v in fuel_series(records).items()},
    }


def write(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"


# ---------------------------------------------------------------- build


def template() -> str:
    return files("radar_energia").joinpath("templates/index.html").read_text(encoding="utf-8")


def render_page(records: list[dict[str, Any]], items: list[dict[str, Any]], latest: date) -> str:
    ss_options, agency_options = options()
    dof_record = next((r for r in records if r["date"] == latest.isoformat()), {})
    dof = dof_record.get("dof") or {}
    seven = (latest - timedelta(days=6)).isoformat()
    week_items = sum(1 for i in items if seven <= i["date"] <= latest.isoformat())
    fix = last_change(get_fix_series(records))
    slots = {
        "date_iso": latest.isoformat(),
        "date_long": time_tag(latest.isoformat(), "weekday"),
        "count_dof": str(len(dof.get("items", []))),
        "count_week": str(week_items),
        "radar": radar_svg(items, latest),
        "count_total": str(len(items)),
        "fix_value": f"{fix.value:.4f}" if fix else "n/d",
        "dof": render_dof(records, latest),
        "authorities": render_authorities(items, latest),
        "markets": render_markets(records, latest),
        "pulse": render_pulse(items, latest),
        "archive": render_archive(items, latest),
        "feeds": render_feeds(),
        "sources": render_sources(),
        "ss_options": ss_options,
        "agency_options": agency_options,
        "first_date": time_tag(records[0]["date"], "short") if records else "",
        "version": __version__,
    }
    page = template()
    for key, value in slots.items():
        page = page.replace(f"{{{{{key}}}}}", value)
    return page


def build_site(data_dir: Path = store.DATA_DIR, out: Path = Path("docs")) -> dict[str, Any]:
    records = list(store.iter_records(data_dir))
    if not records:
        raise SystemExit("No data files; run `radar-energia backfill` first.")
    latest = date.fromisoformat(records[-1]["date"])
    items = flat_items(records)
    changed = []
    outputs = {
        "index.html": render_page(records, items, latest),
        "data/items.json": dump([compact(i) for i in items]),
        "data/markets.json": dump(market_json(records)),
        "data/latest.json": json.dumps(
            latest_json(records, items, latest), ensure_ascii=False, indent=2
        )
        + "\n",
        **all_feeds(items),
    }
    for relative, text in outputs.items():
        if write(out / relative, text):
            changed.append(relative)
    meta = {
        "schema_version": 1,
        "first_date": records[0]["date"],
        "last_date": latest.isoformat(),
        "days": len(records),
        "items": len(items),
        "dof_items": sum(1 for i in items if i["source"] == "dof"),
        "authority_items": sum(1 for i in items if i["source"] == "gobmx"),
    }
    if write(data_dir / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n"):
        changed.append("data/meta.json")
    return {"latest": latest.isoformat(), "items": len(items), "changed": changed}


__all__ = ["WEEKDAYS_ES", "build_site", "sparkline"]
