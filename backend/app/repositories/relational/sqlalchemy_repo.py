"""Implementación SQLAlchemy del :class:`RelationalRepo`.

Adaptador concreto portable entre SQLite (demo/tests) y Postgres/pgvector
(AWS). No expone tipos de SQLAlchemy en su contrato público: recibe y devuelve
entidades ORM del esquema E-1 y estructuras de datos planas, de modo que los
servicios dependan solo de la interfaz (Requirement 4.4).

Gestión de sesión: el repositorio recibe una ``sessionmaker`` y abre una sesión
corta por operación (patrón "unit of work" por método). Esto mantiene el
contrato simple y seguro para la demo; cuando haga falta transaccionar varias
operaciones juntas, se puede introducir un método de contexto más adelante sin
romper a los consumidores.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Base,
    Bitacora,
    Manifestacion,
    Nino,
    Observacion,
    ObservacionManifestacion,
    Recomendacion,
    RubricaVersion,
)


class SqlAlchemyRelationalRepo(RelationalRepo):
    """Repositorio relacional respaldado por SQLAlchemy ORM."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    # --- CRUD genérico -----------------------------------------------------
    def add(self, entity: Base) -> Base:
        with self._session_factory() as session:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def add_all(self, entities: list[Base]) -> None:
        with self._session_factory() as session:
            for entity in entities:
                session.merge(entity)
            session.commit()

    def get(self, model: type[Base], pk: Any) -> Base | None:
        with self._session_factory() as session:
            entity = session.get(model, pk)
            if entity is not None:
                session.expunge(entity)
            return entity

    def list(self, model: type[Base], **filters: Any) -> list[Base]:
        with self._session_factory() as session:
            stmt = select(model)
            for attr, value in filters.items():
                stmt = stmt.where(getattr(model, attr) == value)
            result = list(session.scalars(stmt).all())
            for entity in result:
                session.expunge(entity)
            return result

    def delete(self, model: type[Base], pk: Any) -> bool:
        with self._session_factory() as session:
            entity = session.get(model, pk)
            if entity is None:
                return False
            session.delete(entity)
            session.commit()
            return True

    def count(self, model: type[Base], **filters: Any) -> int:
        with self._session_factory() as session:
            stmt = select(func.count()).select_from(model)
            for attr, value in filters.items():
                stmt = stmt.where(getattr(model, attr) == value)
            return int(session.scalar(stmt) or 0)

    # --- Consultas base de dominio ----------------------------------------
    def ninos_por_jardin(self, id_jardin: str) -> list[Nino]:
        return self.list(Nino, id_jardin=id_jardin)  # type: ignore[return-value]

    def ninos_por_sala(self, id_jardin: str, sala_grupo: str) -> list[Nino]:
        return self.list(  # type: ignore[return-value]
            Nino, id_jardin=id_jardin, sala_grupo=sala_grupo
        )

    def observaciones_de_nino(self, id_nino: str) -> list[Observacion]:
        with self._session_factory() as session:
            stmt = (
                select(Observacion)
                .where(Observacion.id_nino == id_nino)
                .order_by(Observacion.fecha_observacion.asc())
            )
            result = list(session.scalars(stmt).all())
            for obs in result:
                session.expunge(obs)
            return result

    def manifestaciones_de_observacion(
        self, id_observacion: str
    ) -> list[Manifestacion]:
        with self._session_factory() as session:
            stmt = (
                select(Manifestacion)
                .join(
                    ObservacionManifestacion,
                    ObservacionManifestacion.id_manifestacion
                    == Manifestacion.id_manifestacion,
                )
                .where(
                    ObservacionManifestacion.id_observacion == id_observacion
                )
            )
            result = list(session.scalars(stmt).all())
            for manif in result:
                session.expunge(manif)
            return result

    def bitacoras_de_nino(self, id_nino: str) -> list[Bitacora]:
        with self._session_factory() as session:
            stmt = (
                select(Bitacora)
                .where(Bitacora.id_nino == id_nino)
                .order_by(Bitacora.fecha.asc())
            )
            result = list(session.scalars(stmt).all())
            for bit in result:
                session.expunge(bit)
            return result

    def recomendaciones_de_nino(self, id_nino: str) -> list[Recomendacion]:
        with self._session_factory() as session:
            stmt = (
                select(Recomendacion)
                .where(Recomendacion.id_nino == id_nino)
                .order_by(Recomendacion.fecha.asc())
            )
            result = list(session.scalars(stmt).all())
            for rec in result:
                session.expunge(rec)
            return result

    def rubrica_vigente(self) -> RubricaVersion | None:
        with self._session_factory() as session:
            stmt = (
                select(RubricaVersion)
                .order_by(RubricaVersion.vigente_desde.desc())
                .limit(1)
            )
            version = session.scalars(stmt).first()
            if version is not None:
                session.expunge(version)
            return version

    # --- Agregaciones para el reporte de dirección (Modelo 4) -------------
    def contar_ninos_por_sala(self, id_jardin: str) -> dict[str, int]:
        with self._session_factory() as session:
            stmt = (
                select(Nino.sala_grupo, func.count())
                .where(Nino.id_jardin == id_jardin)
                .group_by(Nino.sala_grupo)
            )
            return {sala: int(n) for sala, n in session.execute(stmt).all()}

    def distribucion_niveles(self, id_jardin: str) -> dict[int, int]:
        with self._session_factory() as session:
            stmt = (
                select(Observacion.nivel_estimado, func.count())
                .join(Nino, Nino.id_nino == Observacion.id_nino)
                .where(
                    Nino.id_jardin == id_jardin,
                    Observacion.nivel_estimado.is_not(None),
                )
                .group_by(Observacion.nivel_estimado)
            )
            return {
                int(nivel): int(n) for nivel, n in session.execute(stmt).all()
            }

    def contar_decisiones(self, id_jardin: str) -> dict[str, int]:
        with self._session_factory() as session:
            stmt = (
                select(Recomendacion.decision, func.count())
                .join(Nino, Nino.id_nino == Recomendacion.id_nino)
                .where(Nino.id_jardin == id_jardin)
                .group_by(Recomendacion.decision)
            )
            conteo: Counter[str] = Counter(
                {"AVANZAR": 0, "MANTENER": 0, "RETROCEDER": 0}
            )
            for decision, n in session.execute(stmt).all():
                # ``decision`` llega como enum DecisionNivel; usamos su valor.
                clave = decision.value if hasattr(decision, "value") else str(decision)
                conteo[clave] = int(n)
            return dict(conteo)

    # --- Agregaciones periódicas del reporte de dirección (Modelo 4) ------
    def conteos_nivel_por_sala(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[str, int]]:
        with self._session_factory() as session:
            # Pre-sembrar todas las salas del jardín con conteos en cero para
            # que el reporte liste salas sin movimiento (Requirement 7.7).
            salas = session.scalars(
                select(Nino.sala_grupo)
                .where(Nino.id_jardin == id_jardin)
                .distinct()
            ).all()
            resultado: dict[str, dict[str, int]] = {
                sala: {"subieron": 0, "mantuvieron": 0, "bajaron": 0}
                for sala in salas
            }

            # Observaciones con nivel dentro del período, por niño/a y sala,
            # ordenadas por fecha para derivar nivel al inicio y al cierre.
            stmt = (
                select(
                    Nino.id_nino,
                    Nino.sala_grupo,
                    Observacion.fecha_observacion,
                    Observacion.nivel_estimado,
                )
                .join(Nino, Nino.id_nino == Observacion.id_nino)
                .where(
                    Nino.id_jardin == id_jardin,
                    Observacion.nivel_estimado.is_not(None),
                    Observacion.fecha_observacion >= fecha_inicio,
                    Observacion.fecha_observacion <= fecha_fin,
                )
                .order_by(
                    Nino.id_nino,
                    Observacion.fecha_observacion.asc(),
                )
            )

            # Acumula primera y última observación con nivel por niño/a.
            por_nino: dict[str, dict[str, Any]] = {}
            for id_nino, sala, _fecha, nivel in session.execute(stmt).all():
                registro = por_nino.get(id_nino)
                if registro is None:
                    por_nino[id_nino] = {
                        "sala": sala,
                        "inicio": int(nivel),
                        "cierre": int(nivel),
                    }
                else:
                    registro["cierre"] = int(nivel)

            for registro in por_nino.values():
                sala = registro["sala"]
                conteo = resultado.setdefault(
                    sala, {"subieron": 0, "mantuvieron": 0, "bajaron": 0}
                )
                if registro["cierre"] > registro["inicio"]:
                    conteo["subieron"] += 1
                elif registro["cierre"] < registro["inicio"]:
                    conteo["bajaron"] += 1
                else:
                    conteo["mantuvieron"] += 1
            return resultado

    def distribucion_niveles_por_sala(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[int, int]]:
        with self._session_factory() as session:
            stmt = (
                select(
                    Nino.sala_grupo,
                    Observacion.nivel_estimado,
                    func.count(),
                )
                .join(Nino, Nino.id_nino == Observacion.id_nino)
                .where(
                    Nino.id_jardin == id_jardin,
                    Observacion.nivel_estimado.is_not(None),
                    Observacion.fecha_observacion >= fecha_inicio,
                    Observacion.fecha_observacion <= fecha_fin,
                )
                .group_by(Nino.sala_grupo, Observacion.nivel_estimado)
            )
            resultado: dict[str, dict[int, int]] = {}
            for sala, nivel, n in session.execute(stmt).all():
                resultado.setdefault(sala, {})[int(nivel)] = int(n)
            return resultado

    def distribucion_niveles_por_dominio(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, dict[int, int]]:
        with self._session_factory() as session:
            # El dominio se deriva de las manifestaciones vinculadas a cada
            # observación (tabla puente → manifestaciones.dominio).
            stmt = (
                select(
                    Manifestacion.dominio,
                    Observacion.nivel_estimado,
                    func.count(),
                )
                .select_from(Observacion)
                .join(Nino, Nino.id_nino == Observacion.id_nino)
                .join(
                    ObservacionManifestacion,
                    ObservacionManifestacion.id_observacion
                    == Observacion.id_observacion,
                )
                .join(
                    Manifestacion,
                    Manifestacion.id_manifestacion
                    == ObservacionManifestacion.id_manifestacion,
                )
                .where(
                    Nino.id_jardin == id_jardin,
                    Observacion.nivel_estimado.is_not(None),
                    Observacion.fecha_observacion >= fecha_inicio,
                    Observacion.fecha_observacion <= fecha_fin,
                )
                .group_by(Manifestacion.dominio, Observacion.nivel_estimado)
            )
            resultado: dict[str, dict[int, int]] = {}
            for dominio, nivel, n in session.execute(stmt).all():
                clave = (
                    dominio.value if hasattr(dominio, "value") else str(dominio)
                )
                resultado.setdefault(clave, {})[int(nivel)] = int(n)
            return resultado

    def contar_observaciones_periodo(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, Any]:
        with self._session_factory() as session:
            stmt = (
                select(Observacion.id_educadora, func.count())
                .join(Nino, Nino.id_nino == Observacion.id_nino)
                .where(
                    Nino.id_jardin == id_jardin,
                    Observacion.fecha_observacion >= fecha_inicio,
                    Observacion.fecha_observacion <= fecha_fin,
                )
                .group_by(Observacion.id_educadora)
            )
            por_educadora: dict[str, int] = {}
            total = 0
            for id_educadora, n in session.execute(stmt).all():
                por_educadora[id_educadora] = int(n)
                total += int(n)
            return {"total": total, "por_educadora": por_educadora}

    def contar_bitacoras_periodo(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> dict[str, Any]:
        with self._session_factory() as session:
            stmt = (
                select(Bitacora.id_educadora, func.count())
                .join(Nino, Nino.id_nino == Bitacora.id_nino)
                .where(
                    Nino.id_jardin == id_jardin,
                    Bitacora.fecha >= fecha_inicio,
                    Bitacora.fecha <= fecha_fin,
                )
                .group_by(Bitacora.id_educadora)
            )
            por_educadora: dict[str, int] = {}
            total = 0
            for id_educadora, n in session.execute(stmt).all():
                por_educadora[id_educadora] = int(n)
                total += int(n)
            return {"total": total, "por_educadora": por_educadora}

    def alertas_retroceso(
        self, id_jardin: str, fecha_inicio: date, fecha_fin: date
    ) -> list[str]:
        with self._session_factory() as session:
            # Observaciones con nivel del jardín dentro del período, ordenadas
            # por niño/a y fecha para derivar el nivel asignado (al inicio).
            stmt = (
                select(
                    Observacion.id_nino,
                    Observacion.fecha_observacion,
                    Observacion.nivel_estimado,
                )
                .join(Nino, Nino.id_nino == Observacion.id_nino)
                .where(
                    Nino.id_jardin == id_jardin,
                    Observacion.nivel_estimado.is_not(None),
                    Observacion.fecha_observacion >= fecha_inicio,
                    Observacion.fecha_observacion <= fecha_fin,
                )
                .order_by(
                    Observacion.id_nino,
                    Observacion.fecha_observacion.asc(),
                )
            )
            nivel_asignado: dict[str, int] = {}
            con_retroceso: set[str] = set()
            for id_nino, _fecha, nivel in session.execute(stmt).all():
                nivel = int(nivel)
                if id_nino not in nivel_asignado:
                    # Nivel al inicio del período = nivel asignado de referencia.
                    nivel_asignado[id_nino] = nivel
                elif nivel < nivel_asignado[id_nino]:
                    con_retroceso.add(id_nino)
            return sorted(con_retroceso)

    def alertas_inactividad(
        self, id_jardin: str, fecha_fin: date, dias: int = 14
    ) -> list[str]:
        with self._session_factory() as session:
            # Ventana (fecha_fin - dias, fecha_fin]: inicio exclusivo.
            inicio_ventana = fecha_fin - timedelta(days=dias)
            # Niños/as del jardín con al menos una observación en la ventana.
            activos_stmt = (
                select(Observacion.id_nino)
                .join(Nino, Nino.id_nino == Observacion.id_nino)
                .where(
                    Nino.id_jardin == id_jardin,
                    Observacion.fecha_observacion > inicio_ventana,
                    Observacion.fecha_observacion <= fecha_fin,
                )
                .distinct()
            )
            activos = set(session.scalars(activos_stmt).all())
            todos = session.scalars(
                select(Nino.id_nino).where(Nino.id_jardin == id_jardin)
            ).all()
            return sorted(id_nino for id_nino in todos if id_nino not in activos)


__all__ = ["SqlAlchemyRelationalRepo"]
