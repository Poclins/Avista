"""Tests unitarios de los modelos de dominio y enums (POO).

Cubren construcción válida, validaciones de rango/formato y los valores de las
enumeraciones. Trazabilidad: Requirements 1.4, 3.1 y 4.1.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.models import (
    Bitacora,
    DecisionNivel,
    Dominio,
    Educadora,
    EstadoBitacora,
    FormatoCaptura,
    Jardin,
    Manifestacion,
    NivelRuta,
    Nino,
    Observacion,
    Recomendacion,
    ReporteDireccion,
    Rol,
)


# ---------------------------------------------------------------------------
# Enumeraciones
# ---------------------------------------------------------------------------
def test_formato_captura_valores() -> None:
    """FormatoCaptura expone exactamente texto, audio, foto y video."""
    assert {f.value for f in FormatoCaptura} == {"texto", "audio", "foto", "video"}


def test_dominio_valores() -> None:
    """Dominio expone los 5 dominios de la ruta E-1."""
    assert {d.value for d in Dominio} == {
        "cognitivo",
        "lenguaje_comunicacion",
        "motor_fino",
        "motor_grueso",
        "socioemocional",
    }


def test_decision_nivel_valores() -> None:
    """DecisionNivel expone las tres decisiones de la rúbrica."""
    assert {d.value for d in DecisionNivel} == {"AVANZAR", "MANTENER", "RETROCEDER"}


def test_estado_bitacora_valores() -> None:
    """EstadoBitacora expone borrador y aprobada."""
    assert {e.value for e in EstadoBitacora} == {"borrador", "aprobada"}


def test_rol_valores() -> None:
    """Rol expone educadora y directora."""
    assert {r.value for r in Rol} == {"educadora", "directora"}


def test_enum_es_str() -> None:
    """Los enums son str-compatibles para serialización directa."""
    assert FormatoCaptura.audio == "audio"
    assert Dominio.cognitivo == "cognitivo"


# ---------------------------------------------------------------------------
# Entidades — construcción válida
# ---------------------------------------------------------------------------
def test_jardin_construccion() -> None:
    jardin = Jardin(
        id_jardin="J-001",
        nombre_fantasia="Los Girasoles",
        comuna="Maipú",
        region="RM",
        numero_salas=4,
        numero_educadoras=8,
    )
    assert jardin.id_jardin == "J-001"
    assert jardin.numero_salas == 4


def test_educadora_rol_por_defecto() -> None:
    educadora = Educadora(id_educadora="E-001", id_jardin="J-001", anios_experiencia=5)
    assert educadora.rol is Rol.educadora


def test_nino_sin_pii() -> None:
    """El modelo Nino se identifica por seudónimo (no admite nombre real)."""
    nino = Nino(
        id_nino="N-001",
        id_jardin="J-001",
        fecha_nacimiento=date(2021, 5, 10),
        sexo_registrado="F",
        sala_grupo="Sala Cuna",
        fecha_ingreso=date(2023, 3, 1),
    )
    assert nino.id_nino == "N-001"
    with pytest.raises(ValidationError):
        Nino(
            id_nino="N-002",
            id_jardin="J-001",
            fecha_nacimiento=date(2021, 5, 10),
            sexo_registrado="M",
            sala_grupo="Sala Cuna",
            fecha_ingreso=date(2023, 3, 1),
            nombre="Pedro",  # type: ignore[call-arg]
        )


def test_nivel_ruta_con_dominios() -> None:
    nivel = NivelRuta(
        nivel=3,
        nombre_nivel="Exploración",
        edad_min_meses=12,
        edad_max_meses=18,
        dominios=[Dominio.motor_grueso, Dominio.cognitivo],
    )
    assert nivel.nivel == 3
    assert Dominio.cognitivo in nivel.dominios


def test_manifestacion_construccion() -> None:
    manif = Manifestacion(
        id_manifestacion="M-010",
        nivel=2,
        dominio=Dominio.lenguaje_comunicacion,
        texto_observable="Balbucea en respuesta a la voz de la educadora.",
    )
    assert manif.dominio is Dominio.lenguaje_comunicacion


def _observacion_valida(**overrides) -> Observacion:
    datos = dict(
        id_observacion="O-001",
        id_nino="N-001",
        id_educadora="E-001",
        fecha_observacion=date(2024, 6, 1),
        formato_captura=FormatoCaptura.audio,
        nivel_estimado=4,
        dominios=[Dominio.socioemocional],
    )
    datos.update(overrides)
    return Observacion(**datos)


def test_observacion_registra_fecha_y_formato() -> None:
    """Requirement 1.4: la observación guarda fecha y formato_captura."""
    obs = _observacion_valida()
    assert obs.fecha_observacion == date(2024, 6, 1)
    assert obs.formato_captura is FormatoCaptura.audio


def test_observacion_nivel_estimado_opcional() -> None:
    """Antes de clasificar, el nivel estimado puede quedar sin asignar."""
    obs = _observacion_valida(nivel_estimado=None, dominios=[])
    assert obs.nivel_estimado is None


def test_bitacora_estado_por_defecto_borrador() -> None:
    """Requirement 5.4: una bitácora recién generada queda en borrador."""
    bit = Bitacora(
        id_bitacora="B-001",
        id_nino="N-001",
        id_educadora="E-001",
        periodo="2024-Q2-1",
        texto_generado="Resumen de evidencia...",
        fecha=date(2024, 6, 15),
    )
    assert bit.estado is EstadoBitacora.borrador


def test_recomendacion_construccion() -> None:
    rec = Recomendacion(
        id_recomendacion="R-001",
        id_nino="N-001",
        id_educadora="E-001",
        decision=DecisionNivel.AVANZAR,
        score=0.82,
        dominios_cubiertos=list(Dominio),
        dominios_pendientes=[],
        version_rubrica="v1",
        fecha=date(2024, 6, 20),
    )
    assert rec.decision is DecisionNivel.AVANZAR
    assert rec.decision_educadora is None


def test_reporte_direccion_metricas_dict() -> None:
    rep = ReporteDireccion(
        id_reporte="RD-001",
        id_jardin="J-001",
        periodo="2024-Q2",
        metricas={"subieron": 3, "mantuvieron": 10, "bajaron": 1},
        fecha=date(2024, 7, 1),
    )
    assert rep.metricas["subieron"] == 3


# ---------------------------------------------------------------------------
# Entidades — validaciones de rango y formato
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("nivel", [1, 5, 9])
def test_observacion_nivel_estimado_valido(nivel: int) -> None:
    """Requirement 3.1: nivel_estimado dentro de 1–9 es aceptado."""
    assert _observacion_valida(nivel_estimado=nivel).nivel_estimado == nivel


@pytest.mark.parametrize("nivel", [0, 10, -1])
def test_observacion_nivel_estimado_fuera_de_rango(nivel: int) -> None:
    """Requirement 3.1: nivel_estimado fuera de 1–9 es rechazado."""
    with pytest.raises(ValidationError):
        _observacion_valida(nivel_estimado=nivel)


def test_observacion_formato_invalido() -> None:
    """Un formato_captura no soportado es rechazado por validación."""
    with pytest.raises(ValidationError):
        _observacion_valida(formato_captura="pdf")


@pytest.mark.parametrize("nivel", [0, 10])
def test_nivel_ruta_fuera_de_rango(nivel: int) -> None:
    with pytest.raises(ValidationError):
        NivelRuta(
            nivel=nivel,
            nombre_nivel="X",
            edad_min_meses=0,
            edad_max_meses=1,
        )


def test_manifestacion_nivel_fuera_de_rango() -> None:
    with pytest.raises(ValidationError):
        Manifestacion(
            id_manifestacion="M-999",
            nivel=12,
            dominio=Dominio.cognitivo,
            texto_observable="texto",
        )


def test_jardin_numeros_negativos_rechazados() -> None:
    with pytest.raises(ValidationError):
        Jardin(
            id_jardin="J-001",
            nombre_fantasia="X",
            comuna="Y",
            region="Z",
            numero_salas=-1,
            numero_educadoras=0,
        )


def test_validate_assignment_mantiene_invariantes() -> None:
    """validate_assignment: reasignar un valor inválido también falla."""
    obs = _observacion_valida()
    with pytest.raises(ValidationError):
        obs.nivel_estimado = 42
