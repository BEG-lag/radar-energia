"""Press releases, documents and articles of energy authorities on gob.mx.

gob.mx has no RSS or JSON for these archives (``.rss``/``.json`` variants answer HTTP 500),
but every agency uses the same CMS template: each entry is an ``<article>`` with a
``<time>`` element, an ``<h2>`` title and a link. The parser only relies on those three
elements and skips anything it cannot read, so a template change yields fewer items, never
invented ones. Requests ask for ``text/html``: with ``*/*`` the archive answers with a
JavaScript wrapper instead.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

from ..classify import classify, is_housekeeping
from ..dates import MONTHS_ES
from ..http import PoliteClient
from ..rules import GENERAL

BASE = "https://www.gob.mx"
GAS_LP_PAGE = f"{BASE}/cne/documentos/precios-maximos-aplicables-de-gas-lp-399897"


@dataclass(frozen=True)
class Archive:
    agency: str
    slug: str
    section: str
    kind_es: str

    def url(self, page: int = 1) -> str:
        return f"{BASE}/{self.slug}/es/archivo/{self.section}?idiom=es&order=DESC&page={page}"


ARCHIVES: tuple[Archive, ...] = (
    Archive("CNE", "cne", "prensa", "Comunicado"),
    Archive("CNE", "cne", "documentos", "Documento"),
    Archive("CNE", "cne", "articulos", "Artículo"),
    Archive("SENER", "sener", "prensa", "Comunicado"),
    Archive("SENER", "sener", "articulos", "Artículo"),
    Archive("SENER", "sener", "documentos", "Documento"),
    Archive("ASEA", "asea", "prensa", "Comunicado"),
    Archive("ASEA", "asea", "documentos", "Documento"),
    Archive("CENACE", "cenace", "prensa", "Comunicado"),
)
ARCHIVES_BY_KEY: dict[str, Archive] = {f"{a.slug}:{a.section}": a for a in ARCHIVES}

_ARTICLE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.S | re.I)
_TIME = re.compile(r"<time\b[^>]*\b(?:datetime|date)=\"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", re.I)
_H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
_HREF = re.compile(r"<a\b[^>]*\bhref=\"([^\"]+)\"", re.I)
_TAG = re.compile(r"class=\"tag-presses[^\"]*\"[^>]*>([^<]+)<", re.I)
_DOC_ITEM = re.compile(r"<li class=\"clearfix documents\"[^>]*>(.*?)</li>", re.S | re.I)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _canonical(href: str) -> str:
    parts = urlsplit(urljoin(BASE, html.unescape(href)))
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


def parse_archive(page: str, archive: Archive) -> list[dict[str, Any]]:
    """Every readable entry of one archive page, newest first as published."""
    items: list[dict[str, Any]] = []
    for block in _ARTICLE.findall(page):
        when, title_match = _TIME.search(block), _H2.search(block)
        hrefs = _HREF.findall(block)
        if not (when and title_match and hrefs):
            continue
        title = _text(title_match.group(1))
        url = _canonical(hrefs[-1])
        if not title or not url.startswith(f"{BASE}/{archive.slug}/"):
            continue
        tag = _TAG.search(block)
        published = f"{when.group(1)}T{when.group(2)}:00-06:00"
        path = urlsplit(url).path.strip("/").replace("/es/", "/")
        items.append(
            {
                "id": "gobmx-" + path.replace("/", "-"),
                "agency": archive.agency,
                "section": archive.section,
                "kind": _text(tag.group(1)) if tag else archive.kind_es,
                "title": title,
                "url": url,
                "published": published,
            }
        )
    return items


def classify_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Add subsectors, agencies and matched terms; ``None`` for housekeeping pages."""
    if is_housekeeping(item["title"]):
        return None
    result = classify(item["title"])
    agencies = list(dict.fromkeys([item["agency"], *result.agencies]))
    subsectors = list(result.subsectors) or [GENERAL]
    return {**item, "subsectors": subsectors, "agencies": agencies, "matched": list(result.matched)}


def published_day(item: dict[str, Any]) -> date:
    return date.fromisoformat(item["published"][:10])


def fetch_archive(
    client: PoliteClient, archive: Archive, start: date, end: date, max_pages: int = 6
) -> list[dict[str, Any]]:
    """Entries published between ``start`` and ``end`` (inclusive), classified."""
    found: dict[str, dict[str, Any]] = {}
    for page_number in range(1, max_pages + 1):
        response = client.get_ok(archive.url(page_number), accept="text/html")
        entries = parse_archive(response.text, archive)
        if not entries:
            break
        for entry in entries:
            if start <= published_day(entry) <= end and (item := classify_item(entry)):
                found.setdefault(item["id"], item)
        if min(published_day(entry) for entry in entries) < start:
            break
    return sorted(found.values(), key=lambda i: (i["published"], i["id"]), reverse=True)


_RANGE = re.compile(
    r"DEL\s+(\d{1,2})(?:\s+DE\s+([A-ZÁÉÍÓÚ]+))?(?:\s+DE\s+(\d{4}))?\s+AL\s+(\d{1,2})\s+DE\s+"
    r"([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{4})",
    re.I,
)


def _month(name: str) -> int | None:
    folded = name.lower().replace("á", "a").replace("é", "e")
    for index, month in enumerate(MONTHS_ES, start=1):
        if month.replace("á", "a").replace("é", "e") == folded:
            return index
    return None


def validity(label: str) -> tuple[date, date] | None:
    """``PRECIOS MÁXIMOS VIGENTES DEL 15 AL 21 DE NOVIEMBRE DE 2026`` to its dates."""
    match = _RANGE.search(label)
    if not match:
        return None
    d1, m1, y1, d2, m2, y2 = match.groups()
    end_month = _month(m2)
    if end_month is None:
        return None
    end = date(int(y2), end_month, int(d2))
    start_month = _month(m1) if m1 else end_month
    if start_month is None:
        return None
    start_year = int(y1) if y1 else (end.year - 1 if start_month > end_month else end.year)
    try:
        return date(start_year, start_month, int(d1)), end
    except ValueError:
        return None


def parse_gas_lp(page: str) -> dict[str, Any] | None:
    """The newest weekly PDF of LP gas maximum prices listed on the CNE page.

    Only the official label and link are taken; the prices themselves stay in the PDF.
    """
    for block in _DOC_ITEM.findall(page):
        hrefs = [h for h in _HREF.findall(block) if "/attachment/" in h]
        label = _text(re.sub(r"<a\b.*?</a>", " ", block, flags=re.S))
        if not hrefs or not label:
            continue
        record: dict[str, Any] = {
            "title": label,
            "url": urljoin(BASE, html.unescape(hrefs[0])),
            "page": GAS_LP_PAGE,
        }
        if span := validity(label):
            record["valid_from"], record["valid_to"] = (d.isoformat() for d in span)
        return record
    return None


def fetch_gas_lp(client: PoliteClient) -> dict[str, Any] | None:
    response = client.get_ok(GAS_LP_PAGE + "?idiom=es", accept="text/html")
    return parse_gas_lp(response.text)


def parse_published(value: str) -> datetime:
    return datetime.fromisoformat(value)
