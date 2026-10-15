"""Modelos Pydantic v2 de petición/respuesta de la API REST (Módulo G, 9.3).

Estos modelos forman el **contrato público** de la API: validan las entradas de
cada endpoint y dan forma a las salidas JSON, sin filtrar tipos de SQLAlchemy ni
detalles de los servicios de la Capa 2. Reutilizan los enums del dominio
(``app.domain.models``) como única fuente de verdad del conjunto cerrado de
valores (formato de captura, dominios, decisión de nivel, estado de bitácora,
rol), de modo que la validación de la API coincida con la del dominio.

Convención: los modelos de **respuesta** se construyen desde entidades ORM o
desde los objetos de resultado de los servicios mediante los ``from_*``
helpers de ``app.api.mappers``; los modelos de **petición** validan el cuerpo o
los parámetros antes de llegar al servicio.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import (
    NIVEL_MAX,
    NIVEL_MIN,
    DecisionNivel,
    Dominio,
    EstadoBitacora,
    FormatoCaptura,
    Rol,
)


class _ApiModel(BaseModel):
    """Base de los modelos de la API: rechaza campos desconocidos."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Clasificación (compartido por observaciones y PATCH de clasificación)
# ---------------------------------------------------------------------------
class ClasificacionOut(_ApiModel):
    """Clasificación **propuesta** de una observación (salida del clasificador)."""

    nivel_estimado: int | None = Field(default=None, ge=NIVEL_MIN, le=NIVEL_MAX)
    dominios: list[Dominio] = Field(default_factory=list)
    manifestaciones: list[str] = Field(default_factory=list)
    confianza: float = Field(default=0.0, ge=0.0, le=1.0)
    pendiente_clasificacion_manual: bool = False


# ---------------------------------------------------------------------------
# Observaciones
# ---------------------------------------------------------------------------
class ObservacionTextoIn(_ApiModel):
    """Cuerpo JSON para crear una observación de **texto directo**.

    Alternativa a la carga multipart (medio). El ``id_nino`` llega por la ruta;
    aquí van el texto, la educadora de sesión y, opcionalmente, la fecha.
    """

    id_educadora: str = Field(min_length=1)
    texto: str = Field(min_length=1, max_length=50_000)
    fecha_observacion: date | None = None


class ObservacionOut(_ApiModel):
    """Observación creada o listada, con su clasificación propuesta si la hubo."""

    id_observacion: str
    id_nino: str
    id_educadora: str
    fecha_observacion: date
    formato_captura: FormatoCaptura
    nivel_estimado: int | None = None
    nota_breve: str = ""
    duplicado: bool = False
    clasificacion: ClasificacionOut | None = None


# ---------------------------------------------------------------------------
# PATCH /observaciones/{id}/clasificacion
# ---------------------------------------------------------------------------
class ClasificacionConfirmarIn(_ApiModel):
    """Confirmación o corrección de la clasificación de una observación.

    - ``accion="confirmar"``: persiste la propuesta tal cual (los campos de
      clasificación representan la propuesta confirmada por la educadora).
    - ``accion="corregir"``: persiste los valores corregidos por la educadora.

    La validación de rango (nivel 1–9) y de los topes (≤5 dominios,
    ≤10 manifestaciones) la aplica el dominio al construir la propuesta.
    """

    accion: str = Field(pattern="^(confirmar|corregir)$")
    nivel_estimado: int | None = Field(default=None, ge=NIVEL_MIN, le=NIVEL_MAX)
    dominios: list[Dominio] = Field(default_factory=list, max_length=5)
    manifestaciones: list[str] = Field(default_factory=list, max_length=10)


class ObservacionClasificadaOut(_ApiModel):
    """Observación tras confirmar/corregir su clasificación (persistida)."""

    id_observacion: str
    id_nino: str
    id_educadora: str
    fecha_observacion: date
    formato_captura: FormatoCaptura
    nivel_estimado: int | None = None
    nota_breve: str = ""


# ---------------------------------------------------------------------------
# Niños/as (ficha + trayectoria, "Mi sala")
# ---------------------------------------------------------------------------
class NinoOut(_ApiModel):
    """Ficha básica de un niño/a (solo seudónimo, sin nombre real ni RUT)."""

    id_nino: str
    id_jardin: str
    fecha_nacimiento: date
    sexo_registrado: str
    sala_grupo: str
    fecha_ingreso: date


class FichaNinoOut(_ApiModel):
    """Ficha de un niño/a con su trayectoria (observaciones registradas)."""

    nino: NinoOut
    trayectoria: list[ObservacionOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Bitácoras
# ---------------------------------------------------------------------------
class BitacoraGenerarIn(_ApiModel):
    """Cuerpo para generar una bitácora quincenal (período de 14 días)."""

    id_educadora: str = Field(min_length=1)
    fecha_inicio: date
    fecha_fin: date


class BitacoraEditarIn(_ApiModel):
    """PATCH de una bitácora: editar el texto (borrador) o aprobarla.

    - ``accion="editar"``: requiere ``texto`` y solo aplica en estado borrador.
    - ``accion="aprobar"``: cambia el estado a aprobada; ``texto`` se ignora.
    """

    accion: str = Field(pattern="^(editar|aprobar)$")
    texto: str | None = Field(default=None, max_length=50_000)


class BitacoraOut(_ApiModel):
    """Bitácora quincenal (generada, listada o actualizada)."""

    id_bitacora: str
    id_nino: str
    id_educadora: str
    periodo: str
    texto_generado: str
    estado: EstadoBitacora
    fecha: date


# ---------------------------------------------------------------------------
# Recomendaciones de nivel
# ---------------------------------------------------------------------------
class RecomendacionGenerarIn(_ApiModel):
    """Cuerpo para generar una recomendación de nivel de un niño/a."""

    id_educadora: str = Field(min_length=1)
    nivel_actual: int = Field(ge=NIVEL_MIN, le=NIVEL_MAX)
    nucleo: str | None = Field(default=None, min_length=1)


class RecomendacionOut(_ApiModel):
    """Resultado de una recomendación de nivel (la rúbrica decide, la IA argumenta).

    Cuando el niño/a tiene datos insuficientes (<5 observaciones), la
    recomendación no se persiste: ``datos_insuficientes`` es ``True`` y
    ``decision`` queda en ``None`` (Requirement 6.10).
    """

    id_recomendacion: str | None = None
    id_nino: str
    id_educadora: str
    decision: DecisionNivel | None = None
    tramo: str | None = None
    nucleo: str | None = None
    nivel_actual: int | None = None
    score: float | None = None
    conductas_observables_cubiertas: list[str] = Field(default_factory=list)
    conductas_observables_pendientes: list[str] = Field(default_factory=list)
    evidencia: list[str] = Field(default_factory=list)
    version_rubrica: str | None = None
    argumento_ia: str = ""
    argumento_disponible: bool = False
    datos_insuficientes: bool = False
    observaciones_registradas: int = 0
    observaciones_faltantes: int = 0
    persistida: bool = False


class DecisionEducadoraIn(_ApiModel):
    """Decisión humana final sobre una recomendación (Requirement 6.9)."""

    decision_educadora: str = Field(min_length=1)


class RecomendacionDecisionOut(_ApiModel):
    """Recomendación tras registrar la decisión de la educadora."""

    id_recomendacion: str
    id_nino: str
    id_educadora: str
    decision: DecisionNivel
    decision_educadora: str | None = None


# ---------------------------------------------------------------------------
# Reporte de dirección
# ---------------------------------------------------------------------------
class ReporteOut(_ApiModel):
    """Reporte de dirección agregado por jardín y período (Modelo 4)."""

    id_reporte: str
    id_jardin: str
    periodo: str
    metricas: dict = Field(default_factory=dict)
    resumen_ejecutivo: str = ""
    resumen_disponible: bool = False
    fecha: date


# ---------------------------------------------------------------------------
# Ruta de niveles de referencia
# ---------------------------------------------------------------------------
class NivelRutaOut(_ApiModel):
    """Un nivel de la ruta de desarrollo 1–9 (referencia)."""

    nivel: int = Field(ge=NIVEL_MIN, le=NIVEL_MAX)
    nombre_nivel: str
    edad_min_meses: int = Field(ge=0)
    edad_max_meses: int = Field(ge=0)
    dominios: list[Dominio] = Field(default_factory=list)
    descripcion: str = ""


class RutaNivelesOut(_ApiModel):
    """Ruta/rúbrica de referencia: niveles y versión de rúbrica vigente."""

    niveles: list[NivelRutaOut] = Field(default_factory=list)
    version_rubrica: str | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthOut(_ApiModel):
    """Respuesta del health check (salud para API Gateway / demo)."""

    status: str
    app: str
    use_mocks: bool
    environment: str


__all__ = [
    "Rol",
    "ClasificacionOut",
    "ObservacionTextoIn",
    "ObservacionOut",
    "ClasificacionConfirmarIn",
    "ObservacionClasificadaOut",
    "NinoOut",
    "FichaNinoOut",
    "BitacoraGenerarIn",
    "BitacoraEditarIn",
    "BitacoraOut",
    "RecomendacionGenerarIn",
    "RecomendacionOut",
    "DecisionEducadoraIn",
    "RecomendacionDecisionOut",
    "ReporteOut",
    "NivelRutaOut",
    "RutaNivelesOut",
    "HealthOut",
]
