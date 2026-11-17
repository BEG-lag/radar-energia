"""Registry of the sources the radar evaluated (details and evidence in docs/fuentes.md).

``status`` follows the traffic-light scale used in the documentation:

* ``verde``: machine-readable, stable, no account or token. Used automatically.
* ``amarillo``: works without an account but only as HTML or PDF. Used with care (simple,
  template-level parsing that fails soft) or only linked.
* ``rojo``: not usable automatically (CAPTCHA, robots.txt, token, unreachable). The radar
  links it for manual consultation and never scrapes it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    key: str
    name_es: str
    name_en: str
    publisher: str
    url: str
    status: str
    use_es: str
    use_en: str


SOURCES: tuple[Source, ...] = (
    Source(
        "dof",
        "Diario Oficial de la Federación (API SIDOF)",
        "Official Gazette (SIDOF API)",
        "Secretaría de Gobernación",
        "https://sidof.segob.gob.mx/",
        "verde",
        "Automático: índice diario de cada edición, clasificado por subsector.",
        "Automatic: daily table of contents of every edition, classified by subsector.",
    ),
    Source(
        "fix",
        "Tipo de cambio FIX publicado en el DOF (indicadores SIDOF)",
        "FIX exchange rate published in the DOF (SIDOF indicators)",
        "Banco de México, vía DOF",
        "https://sidof.segob.gob.mx/",
        "verde",
        "Automático: serie diaria y variación.",
        "Automatic: daily series and change.",
    ),
    Source(
        "cenace",
        "Precios de zonas de carga del MDA (servicio web SW-PEND)",
        "Day-ahead load zone prices (SW-PEND web service)",
        "CENACE",
        "https://www.cenace.gob.mx/Paginas/SIM/Reportes/PreciosEnergiaSisMEM.aspx",
        "verde",
        "Automático: promedio diario de seis zonas de carga.",
        "Automatic: daily average of six load zones.",
    ),
    Source(
        "gasolinas",
        "Precios de gasolinas y diésel por estación (XML)",
        "Gasoline and diesel prices by station (XML)",
        "CNE",
        "https://www.cne.gob.mx/ConsultaPrecios/GasolinasyDiesel/GasolinasyDiesel.html",
        "verde",
        "Automático: mediana nacional diaria desde el arranque del radar (sin histórico).",
        "Automatic: daily national median since the radar started (no history).",
    ),
    Source(
        "gobmx",
        "Comunicados, documentos y artículos en gob.mx (CNE, SENER, ASEA, CENACE)",
        "Press releases, documents and articles on gob.mx (CNE, SENER, ASEA, CENACE)",
        "gob.mx",
        "https://www.gob.mx/cne/archivo/prensa",
        "amarillo",
        "Automático con cautela: solo título, fecha y liga de cada entrada.",
        "Automatic, with care: only title, date and link of each entry.",
    ),
    Source(
        "gas-lp",
        "Precios máximos de gas LP (PDF semanal)",
        "LP gas maximum prices (weekly PDF)",
        "CNE",
        "https://www.gob.mx/cne/documentos/precios-maximos-aplicables-de-gas-lp-399897",
        "amarillo",
        "Liga automática al PDF vigente; las cifras no se extraen.",
        "Automatic link to the current PDF; figures are not extracted.",
    ),
    Source(
        "ipgn",
        "Índice de referencia de precios de gas natural al mayoreo (IPGN)",
        "Wholesale natural gas reference price index (IPGN)",
        "CNE",
        "https://www.cne.gob.mx/IPGN/",
        "rojo",
        "Consulta manual: la consulta está protegida con reCAPTCHA.",
        "Manual lookup: the query form is protected by reCAPTCHA.",
    ),
    Source(
        "demanda",
        "Demanda del Sistema Eléctrico Nacional",
        "National grid demand",
        "CENACE",
        "https://www.cenace.gob.mx/GraficaDemanda.aspx",
        "rojo",
        "Consulta manual: solo gráfica web, sin servicio documentado.",
        "Manual lookup: web chart only, no documented service.",
    ),
    Source(
        "mezcla",
        "Precio de la mezcla mexicana de exportación",
        "Mexican crude export blend price",
        "Pemex",
        "https://www.pemex.com/",
        "rojo",
        "Consulta manual: robots.txt de pemex.com no permite robots y Banxico SIE pide token.",
        "Manual lookup: pemex.com robots.txt disallows robots and Banxico SIE needs a token.",
    ),
)
