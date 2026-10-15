"""Modelos de dominio (POO) de jAImes.

Entidades y enumeraciones que representan el dataset E-1 y las tablas nuevas
(bitácoras, recomendaciones, reportes de dirección). Se implementan como
modelos Pydantic v2 para obtener validación declarativa y reutilizarlos en la
capa de API y de servicios.

Principios de privacidad (Requirement 11): los niños/as se identifican solo
por ``id_nino`` seudónimo; estos modelos no contienen nombres reales ni RUT.

Trazabilidad principal de requisitos:
- 1.4  → ``Observacion.formato_captura`` y ``Observacion.fecha_observacion``.
- 3.1  → ``Observacion.nivel_estimado`` acotado a 1–9 y ``dominios``.
- 4.1  → entidades que mapean las tablas del dataset E-1 y las nuevas.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumeraciones
# ---------------------------------------------------------------------------
class FormatoCaptura(str, Enum):
    """Formato del medio con el que la educadora registra una observación."""

    texto = "texto"
    audio = "audio"
    foto = "foto"
    video = "video"


class Dominio(str, Enum):
    """Los 5 dominios de desarrollo de la ruta E-1."""

    cognitivo = "cognitivo"
    lenguaje_comunicacion = "lenguaje_comunicacion"
    motor_fino = "motor_fino"
    motor_grueso = "motor_grueso"
    socioemocional = "socioemocional"


class DecisionNivel(str, Enum):
    """Decisión determinista de la rúbrica sobre el nivel de un niño/a."""

    AVANZAR = "AVANZAR"
    MANTENER = "MANTENER"
    RETROCEDER = "RETROCEDER"


class EstadoBitacora(str, Enum):
    """Estado del ciclo de vida de una bitácora quincenal."""

    borrador = "borrador"
    aprobada = "aprobada"


class Rol(str, Enum):
    """Roles soportados por la aplicación (Requirement 8)."""

    educadora = "educadora"
    directora = "directora"


# Nivel mínimo y máximo de la ruta de desarrollo (9 niveles).
NIVEL_MIN = 1
NIVEL_MAX = 9


# ---------------------------------------------------------------------------
# Entidades del dataset E-1
# ---------------------------------------------------------------------------
class _Base(BaseModel):
    """Base común: valida en asignación y rechaza campos desconocidos."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class Jardin(_Base):
    """Jardín infantil (tabla ``jardines``)."""

    id_jardin: str
    nombre_fantasia: str
    comuna: str
    region: str
    numero_salas: int = Field(ge=0)
    numero_educadoras: int = Field(ge=0)


class Educadora(_Base):
    """Educadora de párvulos ("tía") (tabla ``educadoras``)."""

    id_educadora: str
    id_jardin: str
    rol: Rol = Rol.educadora
    anios_experiencia: int = Field(ge=0)


class Nino(_Base):
    """Niño/a identificado solo por seudónimo (tabla ``ninos``).

    No incluye nombre real ni RUT por diseño (Requirement 11.1).
    """

    id_nino: str
    id_jardin: str
    fecha_nacimiento: date
    sexo_registrado: str
    sala_grupo: str
    fecha_ingreso: date


class NivelRuta(_Base):
    """Un nivel de la ruta de desarrollo 1–9 (tabla ``ruta_niveles``)."""

    nivel: int = Field(ge=NIVEL_MIN, le=NIVEL_MAX)
    nombre_nivel: str
    edad_min_meses: int = Field(ge=0)
    edad_max_meses: int = Field(ge=0)
    dominios: list[Dominio] = Field(default_factory=list)
    descripcion: str = ""


class Manifestacion(_Base):
    """Manifestación observable de un nivel y dominio (tabla ``manifestaciones``)."""

    id_manifestacion: str
    nivel: int = Field(ge=NIVEL_MIN, le=NIVEL_MAX)
    dominio: Dominio
    texto_observable: str


class Observacion(_Base):
    """Evidencia registrada contra un niño/a (tabla ``observaciones``).

    Captura la fecha y el ``formato_captura`` (Requirement 1.4) y el
    ``nivel_estimado`` acotado a 1–9 junto con sus dominios (Requirement 3.1).
    """

    id_observacion: str
    id_nino: str
    id_educadora: str
    fecha_observacion: date
    formato_captura: FormatoCaptura
    nivel_estimado: int | None = Field(default=None, ge=NIVEL_MIN, le=NIVEL_MAX)
    dominios: list[Dominio] = Field(default_factory=list)
    nota_breve: str = ""
    edad_meses: int | None = Field(default=None, ge=0)
    manifestaciones: list[str] = Field(default_factory=list)


class Bitacora(_Base):
    """Bitácora quincenal generada por el Modelo 2 (tabla ``bitacoras``)."""

    id_bitacora: str
    id_nino: str
    id_educadora: str
    periodo: str
    texto_generado: str
    estado: EstadoBitacora = EstadoBitacora.borrador
    fecha: date


class Recomendacion(_Base):
    """Recomendación de nivel del Modelo 3 (tabla ``recomendaciones``).

    La ``decision`` la calcula la rúbrica determinista; ``argumento_ia`` lo
    redacta el LLM; ``decision_educadora`` registra la decisión humana final.
    """

    id_recomendacion: str
    id_nino: str
    id_educadora: str
    decision: DecisionNivel
    score: float
    dominios_cubiertos: list[Dominio] = Field(default_factory=list)
    dominios_pendientes: list[Dominio] = Field(default_factory=list)
    argumento_ia: str = ""
    version_rubrica: str
    decision_educadora: str | None = None
    fecha: date


class ReporteDireccion(_Base):
    """Reporte agregado por jardín del Modelo 4 (tabla ``reportes_direccion``)."""

    id_reporte: str
    id_jardin: str
    periodo: str
    metricas: dict[str, Any] = Field(default_factory=dict)
    resumen_ejecutivo: str = ""
    fecha: date


__all__ = [
    "FormatoCaptura",
    "Dominio",
    "DecisionNivel",
    "EstadoBitacora",
    "Rol",
    "NIVEL_MIN",
    "NIVEL_MAX",
    "Jardin",
    "Educadora",
    "Nino",
    "NivelRuta",
    "Manifestacion",
    "Observacion",
    "Bitacora",
    "Recomendacion",
    "ReporteDireccion",
]
