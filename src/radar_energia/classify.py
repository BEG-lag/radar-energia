"""Deterministic keyword classifier for official titles (rules live in ``rules.py``)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import cache

from .rules import AGENCIES, GENERAL, GOBMX_EXCLUDE, SUBSECTORS


def fold(text: str) -> str:
    """Casefold, strip accents and collapse whitespace for matching."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


@cache
def compile_term(term: str) -> re.Pattern[str]:
    """Compile a rule term (see the module docstring of ``rules``) to a regex."""
    prefix = term.endswith("*")
    body = fold(term[:-1] if prefix else term)
    escaped = r"\s+".join(re.escape(part) for part in body.split())
    tail = "" if prefix else r"(?![\w])"
    return re.compile(rf"(?<![\w]){escaped}{tail}")


def _matches(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if compile_term(term).search(text)]


def _strip(text: str, phrases: tuple[str, ...]) -> str:
    for phrase in phrases:
        text = compile_term(phrase).sub(" ", text)
    return text


@dataclass(frozen=True)
class Classification:
    subsectors: tuple[str, ...]
    agencies: tuple[str, ...]
    matched: tuple[str, ...]
    """Every rule term that matched, in rule order, for transparency on the site."""

    @property
    def relevant(self) -> bool:
        return bool(self.subsectors or self.agencies)


def classify(title: str, issuer: str | None = None) -> Classification:
    """Classify an official title (and optionally its DOF issuer) by subsector and agency."""
    text = fold(title)
    issuer_text = fold(issuer or "")
    matched: list[str] = []

    subsectors: list[str] = []
    for subsector in SUBSECTORS:
        hits = _matches(_strip(text, subsector.ignore), subsector.terms)
        if hits:
            subsectors.append(subsector.key)
            matched.extend(hits)

    agencies: list[str] = []
    for agency in AGENCIES:
        hits = _matches(text, agency.terms)
        by_issuer = bool(issuer_text) and bool(_matches(issuer_text, agency.issuers))
        if agency.key == "SENER" and not hits and "CNE" in _title_agencies(text):
            by_issuer = False  # CNE notes are filed under the SENER in SIDOF
        if hits or by_issuer:
            agencies.append(agency.key)
            matched.extend(h for h in hits if h not in matched)

    if agencies and not subsectors:
        subsectors.append(GENERAL)
    if len(subsectors) > 1 and GENERAL in subsectors:
        subsectors.remove(GENERAL)

    unique = tuple(dict.fromkeys(matched))
    return Classification(tuple(subsectors), tuple(agencies), unique)


def _title_agencies(text: str) -> set[str]:
    return {agency.key for agency in AGENCIES if _matches(text, agency.terms)}


def is_housekeeping(title: str) -> bool:
    """True for gob.mx administrative pages that are not regulatory news."""
    return bool(_matches(fold(title), GOBMX_EXCLUDE))
