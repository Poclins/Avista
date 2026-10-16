"""Tests del **nivel general** derivado del promedio por núcleo (tarea 18.4).

El nivel de progresión sigue siendo **por núcleo** (fuente de verdad,
Requirement 21); el nivel general es un valor **derivado** = promedio de los
niveles de los distintos núcleos con nivel asignado (Requirement 25).

Cubren:
- Promedio de varios núcleos (incluido redondeo a 2 decimales) — Req 25.2.
- Un solo núcleo (el promedio es el propio nivel) — Req 25.2.
- Núcleos sin nivel (``None``) se descartan del promedio.
- Sin ningún núcleo con nivel asignado → "no disponible" sin error — Req 25.4.
- Determinismo e independencia del orden de las claves — Req 25.
- Derivación desde ``ResultadoRubrica`` para la ficha — Req 25.3.

Trazabilidad: Requirements 21, 25.
"""

from __future__ import annotations

import pytest

from app.domain.contracts import NivelGeneral, ResultadoRubrica
from app.domain.models import DecisionNivel
from app.domain.rubrica import RubricaDecision


# ---------------------------------------------------------------------------
# derivar_nivel_general: promedio por núcleo (Requirement 25.2)
# ---------------------------------------------------------------------------
def test_promedio_de_varios_nucleos() -> None:
    """El nivel general es el promedio de los niveles de los distintos núcleos."""
    res = RubricaDecision.derivar_nivel_general(
        {"identidad_y_autonomia": 4, "lenguaje": 6}
    )
    assert isinstance(res, NivelGeneral)
    assert res.disponible is True
    assert res.nivel_general == 5.0  # (4 + 6) / 2
    assert res.nucleos_considerados == 2
    assert res.niveles_por_nucleo == {"identidad_y_autonomia": 4, "lenguaje": 6}


def test_promedio_se_redondea_a_dos_decimales() -> None:
    """Un promedio no exacto se expone redondeado a 2 decimales."""
    res = RubricaDecision.derivar_nivel_general(
        {"a": 3, "b": 4, "c": 4}
    )
    # (3 + 4 + 4) / 3 = 3.666... → 3.67
    assert res.nivel_general == 3.67
    assert res.nucleos_considerados == 3


def test_un_solo_nucleo_el_promedio_es_el_propio_nivel() -> None:
    """Con un único núcleo asignado, el nivel general es ese mismo nivel."""
    res = RubricaDecision.derivar_nivel_general({"identidad_y_autonomia": 5})
    assert res.disponible is True
    assert res.nivel_general == 5.0
    assert res.nucleos_considerados == 1


def test_niveles_none_se_descartan_del_promedio() -> None:
    """Los núcleos sin nivel asignado (None) no entran en el promedio."""
    res = RubricaDecision.derivar_nivel_general(
        {"identidad_y_autonomia": 4, "lenguaje": None, "motor": 8}  # type: ignore[dict-item]
    )
    assert res.nivel_general == 6.0  # (4 + 8) / 2, 'lenguaje' descartado
    assert res.nucleos_considerados == 2
    assert "lenguaje" not in res.niveles_por_nucleo


# ---------------------------------------------------------------------------
# Caso borde: ningún núcleo con nivel asignado (Requirement 25.4)
# ---------------------------------------------------------------------------
def test_sin_nucleos_asignados_no_disponible_sin_error() -> None:
    """Sin núcleos con nivel asignado: no disponible, sin lanzar error."""
    res = RubricaDecision.derivar_nivel_general({})
    assert res.disponible is False
    assert res.nivel_general is None
    assert res.nucleos_considerados == 0
    assert res.niveles_por_nucleo == {}


def test_todos_los_niveles_none_no_disponible() -> None:
    """Si todas las entradas son None, el nivel general no está disponible."""
    res = RubricaDecision.derivar_nivel_general(
        {"identidad_y_autonomia": None, "lenguaje": None}  # type: ignore[dict-item]
    )
    assert res.disponible is False
    assert res.nivel_general is None
    assert res.nucleos_considerados == 0


# ---------------------------------------------------------------------------
# Determinismo (Requirement 25)
# ---------------------------------------------------------------------------
def test_determinismo_independiente_del_orden_de_las_claves() -> None:
    """El resultado no depende del orden de inserción de los núcleos."""
    a = RubricaDecision.derivar_nivel_general({"x": 2, "y": 6, "z": 7})
    b = RubricaDecision.derivar_nivel_general({"z": 7, "x": 2, "y": 6})
    assert a.model_dump() == b.model_dump()


def test_derivacion_no_altera_los_niveles_por_nucleo() -> None:
    """El nivel general es derivado: conserva el detalle por núcleo intacto."""
    entrada = {"identidad_y_autonomia": 3, "lenguaje": 5}
    res = RubricaDecision.derivar_nivel_general(entrada)
    # El desglose por núcleo (fuente de verdad) se preserva junto al derivado.
    assert res.niveles_por_nucleo == entrada
    assert res.nivel_general == 4.0


# ---------------------------------------------------------------------------
# Conveniencia para la ficha: desde ResultadoRubrica (Requirement 25.3)
# ---------------------------------------------------------------------------
def _resultado(nucleo: str, nivel: int) -> ResultadoRubrica:
    return ResultadoRubrica(
        tramo="sala_cuna",
        nucleo=nucleo,
        nivel_actual=nivel,
        decision=DecisionNivel.MANTENER,
        score=0.5,
        version_rubrica="test-v1",
    )


def test_nivel_general_desde_resultados() -> None:
    """La ficha deriva el nivel general promediando el nivel_actual por núcleo."""
    resultados = [
        _resultado("identidad_y_autonomia", 4),
        _resultado("lenguaje", 6),
    ]
    res = RubricaDecision.nivel_general_desde_resultados(resultados)
    assert res.disponible is True
    assert res.nivel_general == 5.0
    assert res.niveles_por_nucleo == {"identidad_y_autonomia": 4, "lenguaje": 6}


def test_nivel_general_desde_resultados_sin_resultados() -> None:
    """Sin resultados por núcleo, el nivel general no está disponible."""
    res = RubricaDecision.nivel_general_desde_resultados([])
    assert res.disponible is False
    assert res.nivel_general is None


def test_nivel_general_desde_resultados_nucleo_duplicado_prevalece_el_ultimo() -> None:
    """Si un núcleo se repite, prevalece el último resultado (determinista)."""
    resultados = [
        _resultado("identidad_y_autonomia", 3),
        _resultado("identidad_y_autonomia", 7),  # prevalece
    ]
    res = RubricaDecision.nivel_general_desde_resultados(resultados)
    assert res.nucleos_considerados == 1
    assert res.nivel_general == 7.0


# ---------------------------------------------------------------------------
# Modelo NivelGeneral
# ---------------------------------------------------------------------------
def test_modelo_nivel_general_por_defecto_no_disponible() -> None:
    """Un NivelGeneral por defecto representa 'no disponible'."""
    res = NivelGeneral()
    assert res.disponible is False
    assert res.nivel_general is None
    assert res.nucleos_considerados == 0
    assert res.niveles_por_nucleo == {}


def test_modelo_nivel_general_rechaza_campos_desconocidos() -> None:
    """El modelo rechaza campos extra (extra='forbid')."""
    with pytest.raises(Exception):
        NivelGeneral(desconocido=1)  # type: ignore[call-arg]
