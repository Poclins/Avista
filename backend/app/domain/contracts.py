"""Tipos de retorno compartidos de los puertos (contratos del Módulo A).

Estos modelos Pydantic v2 son parte del **contrato estable** que consumen los
módulos B–H. Se ubican en el dominio (Módulo A) para que cualquier módulo los
importe sin crear dependencias cruzadas entre providers o repositorios
(Requirements 13.1, 13.2, 13.3).

- ``ClasificacionPropuesta`` → salida de ``Classifier.classify`` (Módulo E).
  La clasificación es **propuesta** (no persistida) hasta que la educadora la
  confirme o corrija (Requirement 3.3); si la confianza es baja, se marca como
  **pendiente de clasificación manual** sin descartar el texto (Requirement 3.5).
- ``ResultadoRubrica`` → salida de ``RubricaDecision.evaluar`` (Módulo F). La
  decisión es **determinista** (la rúbrica decide, la IA argumenta); refleja el
  contrato ``evaluar(...)`` del diseño (Requirements 6.2, 6.5).

Reutiliza los enums del dominio (``Dominio``, ``DecisionNivel``) para no
duplicar el conjunto cerrado de valores (Requirement 3.1).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import NIVEL_MAX, NIVEL_MIN, DecisionNivel, Dominio


class _Base(BaseModel):
    """Base común: valida en asignación y rechaza campos desconocidos."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class ClasificacionPropuesta(_Base):
    """Clasificación **propuesta** de una observación (salida del ``Classifier``).

    Representa la estimación automática que se presenta a la educadora para su
    confirmación o corrección, sin persistirse definitivamente (Requirement 3.3).

    Campos (Requirements 3.1, 3.2, 3.5):
    - ``nivel_estimado``: entero 1–9 estimado por el modelo.
    - ``dominios``: entre 1 y 5 dominios del conjunto cerrado.
    - ``manifestaciones``: entre 1 y 10 identificadores de manifestaciones cuyo
      nivel sea igual al ``nivel_estimado`` y cuyo dominio pertenezca a
      ``dominios`` (la coherencia de ese vínculo la garantiza el ``Classifier``).
    - ``confianza``: confianza del modelo en el rango 0.00–1.00.
    - ``pendiente_clasificacion_manual``: bandera de baja confianza (o texto
      vacío) que marca la observación como pendiente de clasificación manual,
      conservando su texto sin descartarlo (Requirement 3.5).

    Cuando ``pendiente_clasificacion_manual`` es ``True``, los campos de
    estimación pueden quedar vacíos o en ``None`` porque la clasificación se
    delega a la educadora.
    """

    nivel_estimado: int | None = Field(default=None, ge=NIVEL_MIN, le=NIVEL_MAX)
    dominios: list[Dominio] = Field(default_factory=list, max_length=5)
    manifestaciones: list[str] = Field(default_factory=list, max_length=10)
    confianza: float = Field(default=0.0, ge=0.0, le=1.0)
    pendiente_clasificacion_manual: bool = False


class ResultadoRubrica(_Base):
    """Resultado determinista de ``RubricaDecision.evaluar`` (Módulo F).

    Refleja el contrato ``evaluar(...)`` del diseño: la **rúbrica decide**, el
    LLM solo argumenta y nunca altera la decisión (Requirements 6.2, 6.5). Dos
    ejecuciones con la misma entrada y la misma ``version_rubrica`` producen
    siempre el mismo resultado.

    Campos:
    - ``tramo``: tramo de sala derivado del rango etario del niño/a
      (Sala Cuna / Nivel Medio / Transición).
    - ``nucleo``: núcleo evaluado (p. ej. ``"identidad_y_autonomia"``).
    - ``nivel_actual``: nivel de progresión actual (1–8) dentro del tramo×núcleo.
    - ``decision``: una de ``AVANZAR`` / ``MANTENER`` / ``RETROCEDER``.
    - ``score``: fracción de cobertura en el rango 0.00–1.00.
    - ``conductas_observables_cubiertas``: conductas del tramo×núcleo×nivel con
      evidencia que las respalda.
    - ``conductas_observables_pendientes``: conductas del tramo×núcleo×nivel sin
      evidencia (una conducta sin evidencia cuenta como pendiente).
    - ``evidencia``: observaciones citadas por su ``id_observacion``.
    - ``version_rubrica``: versión de rúbrica usada para el cálculo.
    """

    tramo: str
    nucleo: str
    nivel_actual: int = Field(ge=1)
    decision: DecisionNivel
    score: float = Field(ge=0.0, le=1.0)
    conductas_observables_cubiertas: list[str] = Field(default_factory=list)
    conductas_observables_pendientes: list[str] = Field(default_factory=list)
    evidencia: list[str] = Field(default_factory=list)
    version_rubrica: str


__all__ = [
    "ClasificacionPropuesta",
    "ResultadoRubrica",
]
