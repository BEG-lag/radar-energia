from __future__ import annotations

import pytest

from radar_energia.classify import classify, compile_term, fold, is_housekeeping


def test_fold_ignores_case_accents_and_spacing() -> None:
    assert fold("  Energía   ELÉCTRICA ") == "energia electrica"


@pytest.mark.parametrize(
    ("term", "text", "expected"),
    [
        ("eléctric*", "la red electrica nacional", True),
        ("eléctric*", "electronica", False),
        ("CFE", "la cfe informa", True),
        ("CFE", "cfem", False),
        ("gas natural", "gas   natural licuado", True),
        ("ASEA", "nom-em-008-asea-2026", True),
    ],
)
def test_term_matching(term: str, text: str, expected: bool) -> None:
    assert bool(compile_term(term).search(fold(text))) is expected


def test_cne_note_filed_under_sener_is_tagged_cne_only() -> None:
    result = classify(
        "Acuerdo de la Comisión Nacional de Energía por el que se expiden las Disposiciones"
        " Administrativas de Carácter General que regulan la actividad de comercialización de gas"
        " natural, petrolíferos, gas licuado de petróleo y petroquímicos.",
        "SECRETARIA DE ENERGIA",
    )
    assert result.agencies == ("CNE",)
    assert result.subsectors == ("gas-natural", "petroliferos")
    assert "hidrocarburos" not in result.subsectors  # "gas licuado de petróleo" is ignored there
    assert "Comisión Nacional de Energía" in result.matched


def test_sener_issuer_alone_tags_sener_and_general() -> None:
    result = classify(
        "Aviso de consulta pública del Proyecto de Norma Oficial Mexicana PROY-NOM-007-ENER-2026,"
        " Eficiencia energética para sistemas de alumbrado.",
        "SECRETARIA DE ENERGIA",
    )
    assert result.agencies == ("SENER",)
    assert result.subsectors == ("general",)


def test_asea_nom_is_petroliferos() -> None:
    result = classify(
        "Norma Oficial Mexicana de Emergencia NOM-EM-009-ASEA- 2026, Distribución de Gas Licuado"
        " de Petróleo por medio de Auto-tanque y Vehículo de Reparto.",
        "SECRETARIA DE MEDIO AMBIENTE Y RECURSOS NATURALES",
    )
    assert result.subsectors == ("petroliferos",)
    assert result.agencies == ("ASEA",)


@pytest.mark.parametrize(
    ("title", "subsector"),
    [
        (
            "ASEA informa sobre autorización ambiental del Proyecto LNG Amigo en Sonora",
            "gas-natural",
        ),
        ("Listado del Registro de Peritos Mineros vigentes (01/2026).", "mineria"),
        ("CNE aprueba seis permisos para proyectos fotovoltaicos", "renovables"),
        (
            "Acuerdo por el cual se dan a conocer los montos de los estímulos fiscales aplicables a"
            " la enajenación de gasolinas en la región fronteriza",
            "petroliferos",
        ),
        (
            "Tarifas Finales del Suministro Básico de la Comisión Federal de Electricidad",
            "electricidad",
        ),
        (
            "Estatuto Orgánico de la Empresa Pública del Estado, Petróleos Mexicanos.",
            "hidrocarburos",
        ),
    ],
)
def test_subsectors(title: str, subsector: str) -> None:
    assert subsector in classify(title).subsectors


def test_unrelated_titles_are_not_relevant() -> None:
    for title in (
        "Tipo de cambio para solventar obligaciones denominadas en moneda extranjera.",
        "Decreto por el que se expide la Ley de Ingresos de la Federación para el Ejercicio"
        " Fiscal de 2027.",
        "Norma Oficial Mexicana sobre peróxido de hidrógeno en productos de limpieza.",
    ):
        assert not classify(title, "SECRETARIA DE HACIENDA Y CREDITO PUBLICO").relevant


def test_housekeeping_filter() -> None:
    assert is_housekeeping("AVISO DE PRIVACIDAD INTEGRAL DEL FORMULARIO DE CONTACTO CNE")
    assert is_housekeeping("Relación de Bienes Muebles e Inmuebles que componen el Patrimonio")
    assert not is_housekeeping("Sesión del mes de Noviembre de 2026")
