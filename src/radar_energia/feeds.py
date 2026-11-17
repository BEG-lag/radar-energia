"""Atom 1.0 feeds: one with everything and one per subsector.

Deterministic: ``<updated>`` is the newest entry's date, never the build time, so the
files only change when the radar has something new.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from xml.sax.saxutils import escape, quoteattr

from .rules import AGENCIES, SUBSECTORS

SITE_URL = "https://beg-lag.github.io/radar-energia/"
TAG_PREFIX = "tag:beg-lag.github.io,2026:radar-energia/"
SUBSECTOR_LABELS = {s.key: s.label_es for s in SUBSECTORS}
AGENCY_NAMES = {a.key: a.name for a in AGENCIES}
MAX_ENTRIES = 100


def entry_updated(item: dict[str, Any]) -> str:
    if item["source"] == "gobmx":
        return item["published"]
    return f"{item['date']}T07:00:00-06:00"


def entry_summary(item: dict[str, Any]) -> str:
    subsectors = ", ".join(SUBSECTOR_LABELS[s] for s in item["subsectors"])
    if item["source"] == "dof":
        parts = [f"DOF, edición {item['edition']}", item.get("issuer") or "", subsectors]
    else:
        parts = [f"{item['agency']} en gob.mx", item.get("kind", ""), subsectors]
    if item["agencies"]:
        parts.append(" · ".join(item["agencies"]))
    return ". ".join(p for p in parts if p) + "."


def render(
    items: Iterable[dict[str, Any]],
    *,
    title: str,
    subtitle: str,
    self_url: str,
) -> str:
    entries = list(items)[:MAX_ENTRIES]
    updated = max((entry_updated(i) for i in entries), default="2026-11-17T07:00:00-06:00")
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="es-MX">',
        f"  <title>{escape(title)}</title>",
        f"  <subtitle>{escape(subtitle)}</subtitle>",
        f'  <link rel="self" type="application/atom+xml" href={quoteattr(self_url)}/>',
        f'  <link rel="alternate" type="text/html" href="{SITE_URL}"/>',
        f"  <id>{escape(self_url)}</id>",
        f"  <updated>{updated}</updated>",
        "  <author><name>Benjamín Esponda García · PIVOTEK</name>"
        "<uri>https://pivotek.mx</uri></author>",
        '  <generator uri="https://github.com/BEG-lag/radar-energia">radar-energia</generator>',
        "  <rights>Información pública recopilada automáticamente. No constituye asesoría legal."
        " Solo el DOF y las autoridades emisoras son fuente oficial.</rights>",
    ]
    for item in entries:
        lines += [
            "  <entry>",
            f"    <title>{escape(item['title'])}</title>",
            f'    <link rel="alternate" href={quoteattr(item["url"])}/>',
            f"    <id>{TAG_PREFIX}{escape(item['id'])}</id>",
            f"    <updated>{entry_updated(item)}</updated>",
        ]
        lines += [
            f"    <category term={quoteattr(s)} label={quoteattr(SUBSECTOR_LABELS[s])}/>"
            for s in item["subsectors"]
        ]
        lines += [
            f"    <category term={quoteattr(a)} label={quoteattr(AGENCY_NAMES[a])}/>"
            for a in item["agencies"]
        ]
        lines += [f"    <summary>{escape(entry_summary(item))}</summary>", "  </entry>"]
    lines.append("</feed>")
    return "\n".join(lines) + "\n"


def all_feeds(items: list[dict[str, Any]]) -> dict[str, str]:
    """Map of output path (relative to the site root) to Atom XML."""
    feeds = {
        "feed.xml": render(
            items,
            title="radar·energía · todo",
            subtitle="DOF, CNE, SENER, ASEA y CENACE: lo nuevo del sector energético en México,"
            " con liga a la fuente oficial.",
            self_url=f"{SITE_URL}feed.xml",
        )
    }
    for subsector in SUBSECTORS:
        selected = [i for i in items if subsector.key in i["subsectors"]]
        feeds[f"feeds/{subsector.key}.xml"] = render(
            selected,
            title=f"radar·energía · {subsector.label_es}",
            subtitle=f"Publicaciones oficiales clasificadas como {subsector.label_es.lower()}.",
            self_url=f"{SITE_URL}feeds/{subsector.key}.xml",
        )
    return feeds
