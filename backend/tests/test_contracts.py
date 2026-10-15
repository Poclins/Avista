"""Sonda de contratos del Módulo A (tarea 2.1).

Prueba de humo que importa todas las interfaces de puertos y repositorios y
construye los tipos de retorno compartidos (``ClasificacionPropuesta`` y
``ResultadoRubrica``) con datos de ejemplo, para confirmar que los contratos son
coherentes antes de que arranquen los módulos B–H. Trazabilidad: Requirements
13.1, 13.2, 13.3.

No instancia adaptadores concretos (solo interfaces): verifica que son ABCs con
métodos abstractos y que no pueden instanciarse directamente.
"""

from __future__ import annotations

import inspect
import typing

import pytest
from pydantic import ValidationError

from app.domain.contracts import ClasificacionPropuesta, ResultadoRubrica
from app.domain.models import DecisionNivel, Dominio, FormatoCaptura
from app.providers.classifier.base import Classifier
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.errors import (
    EmbeddingError,
    LlmError,
    ProviderError,
    TranscriptionError,
)
from app.providers.llm.base import LlmProvider
from app.providers.transcription.base import TranscriptionProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.storage.base import StorageRepo
from app.repositories.vector.base import VectorRepo


# ---------------------------------------------------------------------------
# Las interfaces son ABCs con métodos abstractos y no se instancian directo
# ---------------------------------------------------------------------------
PUERTOS = [
    (TranscriptionProvider, "transcribe"),
    (EmbeddingProvider, "embed"),
    (LlmProvider, "generate"),
    (Classifier, "classify"),
    (VectorRepo, "index"),
    (VectorRepo, "search"),
    (StorageRepo, "put"),
    (StorageRepo, "get_url"),
    (RelationalRepo, "add"),
]


@pytest.mark.parametrize("interfaz, metodo", PUERTOS)
def test_puerto_es_abc_con_metodo_abstracto(interfaz: type, metodo: str) -> None:
    """Cada puerto es ABC y expone su método como ``@abstractmethod``."""
    assert inspect.isabstract(interfaz)
    assert metodo in getattr(interfaz, "__abstractmethods__", frozenset())


@pytest.mark.parametrize(
    "interfaz",
    [
        TranscriptionProvider,
        EmbeddingProvider,
        LlmProvider,
        Classifier,
        VectorRepo,
        StorageRepo,
    ],
)
def test_puerto_no_instanciable(interfaz: type) -> None:
    """Las interfaces abstractas no pueden instanciarse directamente."""
    with pytest.raises(TypeError):
        interfaz()  # type: ignore[abstract]


def test_firmas_de_contrato() -> None:
    """Las firmas de los métodos coinciden con el contrato del diseño."""
    assert list(inspect.signature(TranscriptionProvider.transcribe).parameters) == [
        "self",
        "media_ref",
        "formato",
    ]
    assert list(inspect.signature(EmbeddingProvider.embed).parameters) == ["self", "text"]
    assert list(inspect.signature(LlmProvider.generate).parameters) == [
        "self",
        "prompt",
        "context",
    ]
    assert list(inspect.signature(Classifier.classify).parameters) == ["self", "texto"]
    assert list(inspect.signature(VectorRepo.search).parameters) == [
        "self",
        "query_embedding",
        "filtros",
        "k",
    ]
    assert list(inspect.signature(StorageRepo.put).parameters) == ["self", "file"]


# ---------------------------------------------------------------------------
# Excepciones tipadas
# ---------------------------------------------------------------------------
def test_jerarquia_de_excepciones() -> None:
    """Las excepciones de proveedor comparten la raíz ``ProviderError``."""
    for exc in (TranscriptionError, EmbeddingError, LlmError):
        assert issubclass(exc, ProviderError)
        assert issubclass(exc, Exception)


# ---------------------------------------------------------------------------
# Tipos de retorno compartidos — construcción con datos de ejemplo
# ---------------------------------------------------------------------------
def test_clasificacion_propuesta_construccion() -> None:
    """ClasificacionPropuesta se construye con nivel, dominios y manifestaciones."""
    prop = ClasificacionPropuesta(
        nivel_estimado=4,
        dominios=[Dominio.socioemocional, Dominio.lenguaje_comunicacion],
        manifestaciones=["M-021", "M-034"],
        confianza=0.87,
        pendiente_clasificacion_manual=False,
    )
    assert prop.nivel_estimado == 4
    assert Dominio.socioemocional in prop.dominios
    assert prop.manifestaciones == ["M-021", "M-034"]


def test_clasificacion_propuesta_baja_confianza() -> None:
    """Requirement 3.5: baja confianza marca pendiente de clasificación manual."""
    prop = ClasificacionPropuesta(pendiente_clasificacion_manual=True)
    assert prop.pendiente_clasificacion_manual is True
    assert prop.nivel_estimado is None
    assert prop.dominios == []


@pytest.mark.parametrize("nivel", [0, 10])
def test_clasificacion_propuesta_nivel_fuera_de_rango(nivel: int) -> None:
    """Requirement 3.1: nivel_estimado fuera de 1–9 es rechazado."""
    with pytest.raises(ValidationError):
        ClasificacionPropuesta(nivel_estimado=nivel)


def test_clasificacion_propuesta_limites_de_longitud() -> None:
    """1–5 dominios y 1–10 manifestaciones: excederlos es rechazado."""
    with pytest.raises(ValidationError):
        ClasificacionPropuesta(dominios=list(Dominio) + [Dominio.cognitivo])
    with pytest.raises(ValidationError):
        ClasificacionPropuesta(manifestaciones=[f"M-{i:03d}" for i in range(11)])


def test_resultado_rubrica_construccion() -> None:
    """ResultadoRubrica refleja el contrato evaluar(...) del diseño."""
    res = ResultadoRubrica(
        tramo="sala_cuna",
        nucleo="identidad_y_autonomia",
        nivel_actual=3,
        decision=DecisionNivel.MANTENER,
        score=0.6,
        conductas_observables_cubiertas=["c1", "c2", "c3"],
        conductas_observables_pendientes=["c4", "c5"],
        evidencia=["O-010", "O-012"],
        version_rubrica="ia-v1",
    )
    assert res.decision is DecisionNivel.MANTENER
    assert res.score == 0.6
    assert res.evidencia == ["O-010", "O-012"]


@pytest.mark.parametrize("score", [-0.1, 1.5])
def test_resultado_rubrica_score_fuera_de_rango(score: float) -> None:
    """El score debe estar en el rango 0.00–1.00 (Requirement 6.5)."""
    with pytest.raises(ValidationError):
        ResultadoRubrica(
            tramo="transicion",
            nucleo="identidad_y_autonomia",
            nivel_actual=5,
            decision=DecisionNivel.AVANZAR,
            score=score,
            version_rubrica="ia-v1",
        )


def test_formato_captura_reutilizado_en_el_contrato() -> None:
    """El puerto de transcripción reutiliza el enum FormatoCaptura del dominio A."""
    # Con ``from __future__ import annotations`` las anotaciones son cadenas;
    # ``get_type_hints`` las resuelve al objeto real del dominio A.
    hints = typing.get_type_hints(TranscriptionProvider.transcribe)
    assert hints["formato"] is FormatoCaptura
