"""Esquema relacional SQLAlchemy (Capa 3) de jAImes.

Mapea 1:1 las tablas del dataset E-1 (``jardines``, ``educadoras``, ``ninos``,
``ruta_niveles``, ``manifestaciones``, ``observaciones``,
``observacion_manifestaciones``) más las tablas nuevas que persisten la salida
de los Modelos 2, 3 y 4 (``bitacoras``, ``recomendaciones``,
``rubrica_versiones``, ``reportes_direccion``).

Se usa el estilo declarativo de SQLAlchemy 2.0 (``DeclarativeBase`` + ``Mapped``
+ ``mapped_column``). Los tipos y la nulabilidad siguen el diccionario de datos
E-1 (ver ``docs/MVP_BLUEPRINT.md`` §5):

- Las fechas se guardan como ``Date`` (formato AAAA-MM-DD).
- ``observaciones.nota_breve`` admite vacío/``NULL`` (puede no haber nota).
- ``observaciones.edad_meses`` es derivada → opcional (``NULL`` hasta calcular).
- ``observaciones.nivel_estimado`` es opcional (``NULL`` antes de clasificar).
- Los campos de estructura (criterios de rúbrica, métricas de reporte, listas de
  dominios) se almacenan como ``JSON`` para portar entre SQLite (demo) y
  Postgres (AWS) sin cambiar el modelo.

Las enumeraciones reutilizan las del dominio (``app.domain.models``) para
mantener una única fuente de verdad (Requirement 4.1). Privacidad
(Requirement 11): ``ninos`` se identifica solo por ``id_nino`` seudónimo; no
hay columnas de nombre real ni RUT.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.domain.models import (
    DecisionNivel,
    Dominio,
    EstadoBitacora,
    FormatoCaptura,
    Rol,
)


class Base(DeclarativeBase):
    """Base declarativa común para todas las tablas relacionales."""

    # Un único tipo JSON portable (SQLite usa TEXT; Postgres usa JSON/JSONB).
    type_annotation_map = {dict: JSON, list: JSON}


# ---------------------------------------------------------------------------
# Tablas del dataset E-1
# ---------------------------------------------------------------------------
class Jardin(Base):
    """Jardín infantil (tabla ``jardines``)."""

    __tablename__ = "jardines"

    id_jardin: Mapped[str] = mapped_column(String, primary_key=True)
    nombre_fantasia: Mapped[str] = mapped_column(String, nullable=False)
    comuna: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)
    numero_salas: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_educadoras: Mapped[int] = mapped_column(Integer, nullable=False)

    educadoras: Mapped[list["Educadora"]] = relationship(back_populates="jardin")
    ninos: Mapped[list["Nino"]] = relationship(back_populates="jardin")
    reportes: Mapped[list["ReporteDireccion"]] = relationship(
        back_populates="jardin"
    )


class Educadora(Base):
    """Educadora de párvulos (tabla ``educadoras``)."""

    __tablename__ = "educadoras"

    id_educadora: Mapped[str] = mapped_column(String, primary_key=True)
    id_jardin: Mapped[str] = mapped_column(
        ForeignKey("jardines.id_jardin"), nullable=False
    )
    rol: Mapped[Rol] = mapped_column(
        SAEnum(Rol, name="rol"), nullable=False, default=Rol.educadora_parvulos
    )
    anios_experiencia: Mapped[int] = mapped_column(Integer, nullable=False)

    jardin: Mapped["Jardin"] = relationship(back_populates="educadoras")


class Nino(Base):
    """Niño/a identificado solo por seudónimo (tabla ``ninos``).

    Sin nombre real ni RUT por diseño (Requirement 11.1).
    """

    __tablename__ = "ninos"

    id_nino: Mapped[str] = mapped_column(String, primary_key=True)
    id_jardin: Mapped[str] = mapped_column(
        ForeignKey("jardines.id_jardin"), nullable=False
    )
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    sexo_registrado: Mapped[str] = mapped_column(String, nullable=False)
    sala_grupo: Mapped[str] = mapped_column(String, nullable=False)
    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=False)

    jardin: Mapped["Jardin"] = relationship(back_populates="ninos")
    observaciones: Mapped[list["Observacion"]] = relationship(
        back_populates="nino"
    )


class RutaNivel(Base):
    """Un nivel de la ruta de desarrollo 1–9 (tabla ``ruta_niveles``)."""

    __tablename__ = "ruta_niveles"

    nivel: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_nivel: Mapped[str] = mapped_column(String, nullable=False)
    edad_min_meses: Mapped[int] = mapped_column(Integer, nullable=False)
    edad_max_meses: Mapped[int] = mapped_column(Integer, nullable=False)
    # Lista de dominios asociados al nivel (JSON de valores de Dominio).
    dominios: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")

    manifestaciones: Mapped[list["Manifestacion"]] = relationship(
        back_populates="ruta_nivel"
    )


class Manifestacion(Base):
    """Manifestación observable de un nivel y dominio (tabla ``manifestaciones``)."""

    __tablename__ = "manifestaciones"

    id_manifestacion: Mapped[str] = mapped_column(String, primary_key=True)
    nivel: Mapped[int] = mapped_column(
        ForeignKey("ruta_niveles.nivel"), nullable=False
    )
    dominio: Mapped[Dominio] = mapped_column(
        SAEnum(Dominio, name="dominio"), nullable=False
    )
    texto_observable: Mapped[str] = mapped_column(Text, nullable=False)

    ruta_nivel: Mapped["RutaNivel"] = relationship(
        back_populates="manifestaciones"
    )
    observaciones: Mapped[list["ObservacionManifestacion"]] = relationship(
        back_populates="manifestacion"
    )


class Observacion(Base):
    """Evidencia registrada contra un niño/a (tabla ``observaciones``).

    ``nivel_estimado``, ``nota_breve`` y ``edad_meses`` son opcionales según el
    diccionario E-1: el nivel se asigna al clasificar, la nota puede ir vacía y
    la edad en meses es derivada.
    """

    __tablename__ = "observaciones"

    id_observacion: Mapped[str] = mapped_column(String, primary_key=True)
    id_nino: Mapped[str] = mapped_column(
        ForeignKey("ninos.id_nino"), nullable=False
    )
    id_educadora: Mapped[str] = mapped_column(
        ForeignKey("educadoras.id_educadora"), nullable=False
    )
    fecha_observacion: Mapped[date] = mapped_column(Date, nullable=False)
    formato_captura: Mapped[FormatoCaptura] = mapped_column(
        SAEnum(FormatoCaptura, name="formato_captura"), nullable=False
    )
    nivel_estimado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nota_breve: Mapped[str | None] = mapped_column(Text, nullable=True)
    edad_meses: Mapped[int | None] = mapped_column(Integer, nullable=True)

    nino: Mapped["Nino"] = relationship(back_populates="observaciones")
    manifestaciones: Mapped[list["ObservacionManifestacion"]] = relationship(
        back_populates="observacion"
    )


class ObservacionManifestacion(Base):
    """Vínculo N:M entre observaciones y manifestaciones (PK compuesta)."""

    __tablename__ = "observacion_manifestaciones"

    id_observacion: Mapped[str] = mapped_column(
        ForeignKey("observaciones.id_observacion"), primary_key=True
    )
    id_manifestacion: Mapped[str] = mapped_column(
        ForeignKey("manifestaciones.id_manifestacion"), primary_key=True
    )

    observacion: Mapped["Observacion"] = relationship(
        back_populates="manifestaciones"
    )
    manifestacion: Mapped["Manifestacion"] = relationship(
        back_populates="observaciones"
    )


# ---------------------------------------------------------------------------
# Tablas nuevas (salida de los Modelos 2, 3 y 4)
# ---------------------------------------------------------------------------
class Bitacora(Base):
    """Bitácora quincenal generada por el Modelo 2 (tabla ``bitacoras``)."""

    __tablename__ = "bitacoras"

    id_bitacora: Mapped[str] = mapped_column(String, primary_key=True)
    id_nino: Mapped[str] = mapped_column(
        ForeignKey("ninos.id_nino"), nullable=False
    )
    id_educadora: Mapped[str] = mapped_column(
        ForeignKey("educadoras.id_educadora"), nullable=False
    )
    periodo: Mapped[str] = mapped_column(String, nullable=False)
    texto_generado: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoBitacora] = mapped_column(
        SAEnum(EstadoBitacora, name="estado_bitacora"),
        nullable=False,
        default=EstadoBitacora.borrador,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)


class RubricaVersion(Base):
    """Versión de la rúbrica determinista (tabla ``rubrica_versiones``).

    ``criterios`` guarda el JSON de la configuración (N observaciones, dominios
    requeridos, umbrales). Es la fuente de verdad que referencia cada
    recomendación mediante ``version_rubrica``.
    """

    __tablename__ = "rubrica_versiones"

    version_rubrica: Mapped[str] = mapped_column(String, primary_key=True)
    criterios: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")

    recomendaciones: Mapped[list["Recomendacion"]] = relationship(
        back_populates="rubrica_version"
    )


class Recomendacion(Base):
    """Recomendación de nivel del Modelo 3 (tabla ``recomendaciones``).

    ``decision`` la calcula la rúbrica determinista; ``argumento_ia`` lo redacta
    el LLM; ``decision_educadora`` registra la decisión humana final (puede ser
    ``NULL`` hasta que la educadora resuelva).
    """

    __tablename__ = "recomendaciones"

    id_recomendacion: Mapped[str] = mapped_column(String, primary_key=True)
    id_nino: Mapped[str] = mapped_column(
        ForeignKey("ninos.id_nino"), nullable=False
    )
    id_educadora: Mapped[str] = mapped_column(
        ForeignKey("educadoras.id_educadora"), nullable=False
    )
    decision: Mapped[DecisionNivel] = mapped_column(
        SAEnum(DecisionNivel, name="decision_nivel"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    dominios_cubiertos: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    dominios_pendientes: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    argumento_ia: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version_rubrica: Mapped[str] = mapped_column(
        ForeignKey("rubrica_versiones.version_rubrica"), nullable=False
    )
    decision_educadora: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    rubrica_version: Mapped["RubricaVersion"] = relationship(
        back_populates="recomendaciones"
    )


class ReporteDireccion(Base):
    """Reporte agregado por jardín del Modelo 4 (tabla ``reportes_direccion``)."""

    __tablename__ = "reportes_direccion"

    id_reporte: Mapped[str] = mapped_column(String, primary_key=True)
    id_jardin: Mapped[str] = mapped_column(
        ForeignKey("jardines.id_jardin"), nullable=False
    )
    periodo: Mapped[str] = mapped_column(String, nullable=False)
    metricas: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resumen_ejecutivo: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    jardin: Mapped["Jardin"] = relationship(back_populates="reportes")


__all__ = [
    "Base",
    "Jardin",
    "Educadora",
    "Nino",
    "RutaNivel",
    "Manifestacion",
    "Observacion",
    "ObservacionManifestacion",
    "Bitacora",
    "RubricaVersion",
    "Recomendacion",
    "ReporteDireccion",
]
