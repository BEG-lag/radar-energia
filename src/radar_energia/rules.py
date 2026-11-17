"""Keyword rules that decide what the radar shows and how it is classified.

Everything here is plain data so that anyone can read, audit and change the rules
without touching the matching code (``classify.py``).

How a term matches a title (and, for agencies, the issuing body in the DOF):

* Case and accents are ignored: ``energia`` matches ``Energía``.
* A term ending in ``*`` matches words that *start* with it: ``eléctric*`` matches
  ``eléctrica``, ``eléctrico`` and ``eléctricas``.
* Any other term must match whole words: ``CFE`` does not match ``CFEM``.
* Multi-word terms match as a phrase, with any amount of whitespace between words.

Subsectors are not exclusive: a title can belong to several. ``ignore`` lists phrases
that are removed from the title before testing that subsector, so that, for example,
"gas licuado de petróleo" counts as petrolíferos and not as hidrocarburos.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Subsector:
    key: str
    label_es: str
    label_en: str
    terms: tuple[str, ...]
    ignore: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class Agency:
    key: str
    name: str
    terms: tuple[str, ...]
    """Terms searched in the title."""
    issuers: tuple[str, ...] = field(default=())
    """Issuing-body names as SIDOF writes them (matched as whole phrases)."""


SUBSECTORS: tuple[Subsector, ...] = (
    Subsector(
        "electricidad",
        "Electricidad",
        "Electricity",
        (
            "eléctric*",
            "electricidad",
            "termoeléctric*",
            "Red Nacional de Transmisión",
            "Redes Generales de Distribución",
            "suministro básico",
            "generación distribuida",
            "autoabasto",
            "cogeneración",
            "CFE",
            "CENACE",
            "Centro Nacional de Control de Energía",
        ),
    ),
    Subsector(
        "hidrocarburos",
        "Hidrocarburos",
        "Hydrocarbons",
        (
            "hidrocarburo*",
            "petróleo*",
            "petroler*",
            "Pemex",
            "exploración y extracción",
            "yacimiento*",
            "CNH",
        ),
        ignore=("gas licuado de petróleo",),
    ),
    Subsector(
        "gas-natural",
        "Gas natural",
        "Natural gas",
        (
            "gas natural",
            "gasoducto*",
            "CENAGAS",
            "GNL",
            "LNG",
            "licuefacción",
            "regasificación",
            "temporada abierta",
            "Sistrangas",
        ),
    ),
    Subsector(
        "petroliferos",
        "Petrolíferos",
        "Petroleum products",
        (
            "petrolífero*",
            "petroquímic*",
            "gasolina*",
            "diésel",
            "diesel",
            "turbosina",
            "combustóleo",
            "combustible*",
            "gas licuado de petróleo",
            "gas LP",
            "gas L.P.",
            "estación de servicio",
            "estaciones de servicio",
            "expendio al público",
        ),
    ),
    Subsector(
        "renovables",
        "Renovables",
        "Renewables",
        (
            "renovable*",
            "energía limpia",
            "energías limpias",
            "fotovoltaic*",
            "energía solar",
            "paneles solares",
            "eólic*",
            "geotérmic*",
            "geotermia",
            "geotermoeléctric*",
            "hidroeléctric*",
            "minihidráulic*",
            "transición energética",
            "bioenergético*",
            "biocombustible*",
            "biogás",
            "biomasa",
            "hidrógeno verde",
            "hidrógeno de bajas emisiones",
            "almacenamiento de energía",
        ),
    ),
    Subsector(
        "mineria",
        "Minería",
        "Mining",
        (
            "minería",
            "minero",
            "mineros",
            "minera",
            "mineras",
            "minerometalúrgic*",
            "metalúrgic*",
            "litio",
            "carbón mineral",
            "Servicio Geológico Mexicano",
        ),
    ),
    Subsector(
        "general",
        "Energía (general)",
        "Energy (general)",
        (
            "energía",
            "energías",
            "energétic*",
            "SENER",
            "CNE",
        ),
    ),
)
"""Ordered from the most specific to the most general. ``general`` is only kept when no
other subsector matched (see ``classify.classify``)."""

GENERAL = "general"

AGENCIES: tuple[Agency, ...] = (
    Agency(
        "SENER",
        "Secretaría de Energía",
        ("Secretaría de Energía", "SENER"),
        ("SECRETARIA DE ENERGIA",),
    ),
    Agency(
        "CNE",
        "Comisión Nacional de Energía",
        ("Comisión Nacional de Energía", "CNE"),
        ("COMISION NACIONAL DE ENERGIA",),
    ),
    Agency(
        "ASEA",
        "Agencia de Seguridad, Energía y Ambiente",
        (
            "Agencia Nacional de Seguridad Industrial y de Protección al Medio Ambiente"
            " del Sector Hidrocarburos",
            "ASEA",
        ),
        ("AGENCIA NACIONAL DE SEGURIDAD INDUSTRIAL Y DE PROTECCION AL MEDIO AMBIENTE",),
    ),
    Agency(
        "CENACE",
        "Centro Nacional de Control de Energía",
        ("Centro Nacional de Control de Energía", "CENACE"),
        ("CENTRO NACIONAL DE CONTROL DE ENERGIA",),
    ),
    Agency(
        "CENAGAS",
        "Centro Nacional de Control del Gas Natural",
        ("Centro Nacional de Control del Gas Natural", "CENAGAS"),
        ("CENTRO NACIONAL DE CONTROL DEL GAS NATURAL",),
    ),
    Agency(
        "CFE",
        "Comisión Federal de Electricidad",
        ("Comisión Federal de Electricidad", "CFE"),
        ("COMISION FEDERAL DE ELECTRICIDAD",),
    ),
    Agency(
        "Pemex",
        "Petróleos Mexicanos",
        ("Petróleos Mexicanos", "Pemex"),
        ("PETROLEOS MEXICANOS",),
    ),
)
"""Energy authorities and state companies the radar tags.

The CNE is a deconcentrated body of the SENER, so SIDOF files its DOF notes under the
issuer "SECRETARIA DE ENERGIA". When the title names the CNE, the note is tagged CNE and
the issuer alone does not add SENER (``classify.classify``)."""

GOBMX_EXCLUDE: tuple[str, ...] = (
    "aviso de privacidad",
    "bienes muebles",
    "comité de ética",
    "comités de ética",
    "código de ética",
    "igualdad laboral",
    "austeridad republicana",
    "directorio",
)
"""Administrative housekeeping on gob.mx that is not regulatory news. Titles containing
any of these phrases are left out of the authorities feed."""
