# Changelog

## 1.0.0 (2026-11-17)

First public version.

- Sources verified on 2026-11-17 with a traffic-light status each (`docs/fuentes.md`).
- Pipeline: DOF notes and FIX (SIDOF API), CENACE SW-PEND load zone prices, CNE gasoline and
  diesel station prices, gob.mx archives of CNE, SENER, ASEA and CENACE, and the link to the CNE
  weekly LP gas maximum prices PDF.
- Transparent keyword classifier by subsector and agency; daily JSON files with a JSON Schema.
- Static site in `docs/`: today's radar, market cards with sparklines, pulse by subsector, 30-day
  archive, search, Spanish and English, Atom feeds (all and per subsector).
- 90-day backfill (2026-08-20 to 2026-11-17).
- Scheduled updates at 08:30 and 22:30 Mexico City time; CI with ruff and pytest on Python 3.12 to
  3.14.
