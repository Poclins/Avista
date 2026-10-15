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
