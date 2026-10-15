"""Interfaz del repositorio relacional (puerto de la Capa 3).

Define el contrato que la lógica de negocio (servicios) usa para persistir y
consultar las entidades del dataset E-1 y las tablas nuevas. Los servicios
dependen de esta abstracción, nunca de SQLAlchemy directamente, cumpliendo el
Requirement 4.4 (sin acoplamiento al SDK) y el principio DIP.

La interfaz es deliberadamente pequeña y orientada a capacidades (ISP):
- CRUD genérico por entidad (``add``/``get``/``list``/``delete``).
- Consultas base que los servicios necesitan (observaciones por niño/sala,
  bitácoras/recomendaciones por niño, etc.).
- Agregaciones para el reporte de dirección (Modelo 4).

Las entidades que entran y salen son las ORM de :mod:`app.repositories.schema`.
Las implementaciones concretas gestionan la sesión/transacción internamente.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from app.repositories.schema import (
    Base,
    Bitacora,
    Educadora,
    Jardin,
    Manifestacion,
    Nino,
    Observacion,
    ObservacionManifestacion,
    Recomendacion,
    ReporteDireccion,
    RubricaVersion,
    RutaNivel,
)


class RelationalRepo(ABC):
    """Puerto de acceso a la base relacional.

    Métodos CRUD genéricos más consultas y agregaciones de dominio. Las
    implementaciones deben ser intercambiables (LSP): el comportamiento
    observable no debe depender de SQLite vs Postgres.
    """

    # --- CRUD genérico -----------------------------------------------------
    @abstractmethod
    def add(self, entity: Base) -> Base:
        """Inserta (o fusiona) una entidad y devuelve la persistida."""

    @abstractmethod
    def add_all(self, entities: list[Base]) -> None:
        """Inserta un lote de entidades en una sola transacción."""

    @abstractmethod
    def get(self, model: type[Base], pk: Any) -> Base | None:
        """Recupera una entidad por su clave primaria, o ``None``."""

    @abstractmethod
    def list(self, model: type[Base], **filters: Any) -> list[Base]:
        """Lista entidades de un modelo, con filtros de igualdad opcionales."""

    @abstractmethod
    def delete(self, model: type[Base], pk: Any) -> bool:
        """Elimina por clave primaria. Devuelve ``True`` si existía."""

    @abstractmethod
    def count(self, model: type[Base], **filters: Any) -> int:
        """Cuenta entidades de un modelo con filtros de igualdad opcionales."""

    # --- Consultas base de dominio ----------------------------------------
    @abstractmethod
    def ninos_por_jardin(self, id_jardin: str) -> list[Nino]:
        """Niños/as de un jardín."""

    @abstractmethod
    def ninos_por_sala(self, id_jardin: str, sala_grupo: str) -> list[Nino]:
        """Niños/as de una sala concreta de un jardín ("Mi sala")."""

    @abstractmethod
    def observaciones_de_nino(self, id_nino: str) -> list[Observacion]:
        """Observaciones de un niño/a ordenadas por fecha ascendente."""

    @abstractmethod
    def manifestaciones_de_observacion(
        self, id_observacion: str
    ) -> list[Manifestacion]:
        """Manifestaciones vinculadas a una observación (vía tabla puente)."""

    @abstractmethod
    def bitacoras_de_nino(self, id_nino: str) -> list[Bitacora]:
        """Bitácoras de un niño/a ordenadas por fecha ascendente."""

    @abstractmethod
    def recomendaciones_de_nino(self, id_nino: str) -> list[Recomendacion]:
        """Recomendaciones de un niño/a ordenadas por fecha ascendente."""

    @abstractmethod
    def rubrica_vigente(self) -> RubricaVersion | None:
        """Versión de rúbrica más reciente por ``vigente_desde``, o ``None``."""

    # --- Agregaciones para el reporte de dirección (Modelo 4) -------------
    @abstractmethod
    def contar_ninos_por_sala(self, id_jardin: str) -> dict[str, int]:
        """Cuenta niños/as por sala en un jardín."""

    @abstractmethod
    def distribucion_niveles(self, id_jardin: str) -> dict[int, int]:
        """Distribución de ``nivel_estimado`` de las observaciones del jardín.

        Devuelve ``{nivel: conteo}`` considerando solo observaciones con nivel
        asignado (no clasificadas se omiten).
        """

    @abstractmethod
    def contar_decisiones(self, id_jardin: str) -> dict[str, int]:
        """Cuenta recomendaciones por decisión (AVANZAR/MANTENER/RETROCEDER).

        Agrega sobre los niños/as del jardín dado. Devuelve un dict con las
        tres claves de decisión (0 si no hay).
        """

    # --- Agregaciones periódicas del reporte de dirección (Modelo 4) ------
    # Estas consultas aceptan un período ``[fecha_inicio, fecha_fin]`` (ambas
    # inclusivas) y las consume el ``DirectorReportService`` del Módulo G vía
    # esta interfaz. Toda la lógica de agregación vive aquí (Requirement 7.8):
    # el LLM nunca infiere estas métricas.

    @abstractmethod
    def conteos_nivel_por_sala(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[str, int]]:
        """Conteo de niños/as que subieron/mantuvieron/bajaron por sala.

        Para cada niño/a del jardín, compara su ``nivel_estimado`` al cierre del
        período (última observación con nivel dentro del período) contra el del
        inicio (primera observación con nivel dentro del período). Cada niño/a
        se cuenta en **exactamente una** de las tres categorías
        (``subieron``/``mantuvieron``/``bajaron``); los niños/as sin
        observaciones con nivel dentro del período se omiten (Requirement 7.1).

        Devuelve ``{sala_grupo: {"subieron": n, "mantuvieron": n, "bajaron": n}}``
        con una entrada por sala del jardín (ceros si no hubo movimiento).
        """

    @abstractmethod
    def distribucion_niveles_por_sala(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[int, int]]:
        """Distribución de niveles observados por sala dentro del período.

        Devuelve ``{sala_grupo: {nivel: conteo}}`` contando las observaciones
        con ``nivel_estimado`` asignado cuya fecha cae en el período
        (Requirement 7.3).
        """

    @abstractmethod
    def distribucion_niveles_por_dominio(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[int, int]]:
        """Distribución de niveles observados por dominio dentro del período.

        El dominio de cada observación se deriva de las manifestaciones
        vinculadas (tabla puente → ``manifestaciones.dominio``). Devuelve
        ``{dominio: {nivel: conteo}}`` (Requirement 7.3).
        """

    @abstractmethod
    def contar_observaciones_periodo(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, Any]:
        """Conteo de observaciones del jardín en el período (Requirement 7.3).

        Devuelve ``{"total": n, "por_educadora": {id_educadora: n, ...}}``.
        """

    @abstractmethod
    def contar_bitacoras_periodo(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, Any]:
        """Conteo de bitácoras del jardín en el período (Requirement 7.3).

        Devuelve ``{"total": n, "por_educadora": {id_educadora: n, ...}}``.
        """

    @abstractmethod
    def alertas_retroceso(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> list[str]:
        """``id_nino`` con señal de retroceso en el período (Requirement 7.3).

        Un niño/a entra en la alerta si tiene una o más observaciones con
        ``nivel_estimado`` por debajo de su nivel asignado dentro del período,
        donde el nivel asignado es el nivel al inicio del período (primera
        observación con nivel dentro del período).
        """

    @abstractmethod
    def alertas_inactividad(
        self, id_jardin: str, fecha_fin: date, dias: int = 14
    ) -> list[str]:
        """``id_nino`` sin observaciones en los últimos ``dias`` del período.

        Devuelve los niños/as del jardín sin ninguna observación registrada en
        la ventana ``(fecha_fin - dias, fecha_fin]`` (Requirement 7.3). Por
        defecto son los últimos 14 días previos a la ``fecha_fin``.
        """


__all__ = [
    "RelationalRepo",
    # Re-exporta los modelos ORM por conveniencia de los consumidores.
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
