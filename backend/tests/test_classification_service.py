"""Tests del Módulo E — ``ClassificationService`` (tarea 6.2).

Verifican el caso de uso del Requirement 3 en **aislamiento**: solo se usan el
dominio del Módulo A, las entidades ORM del esquema y **fakes** de los puertos
``Classifier`` y ``RelationalRepo``. No se importa ninguna implementación
concreta de un módulo hermano.

Trazabilidad:
- 3.3 → ``proponer`` devuelve la clasificación propuesta **sin** persistir.
- 3.4 → ``confirmar``/``corregir`` persisten los valores vía ``RelationalRepo``.
- 3.6 → ante fallo de persistencia se **conservan los valores previos** sin
  cambios parciales y se devuelve un mensaje de error **en español**.
"""

from __future__ import annotations

import copy
from datetime import date
from typing import Any

import pytest

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import Dominio, FormatoCaptura
from app.providers.classifier.base import Classifier
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Base,
    Observacion,
    ObservacionManifestacion,
)
from app.services.classification_service import ClassificationService
from app.services.errors import PersistenciaError


# ---------------------------------------------------------------------------
# Fakes de los puertos (aislamiento: no se tocan implementaciones hermanas)
# ---------------------------------------------------------------------------
class _StubClassifier(Classifier):
    """``Classifier`` falso que devuelve una propuesta fija y cuenta llamadas."""

    def __init__(self, propuesta: ClasificacionPropuesta) -> None:
        self._propuesta = propuesta
        self.textos: list[str] = []

    def classify(self, texto: str) -> ClasificacionPropuesta:
        self.textos.append(texto)
        return self._propuesta


class _FakeRelationalRepo(RelationalRepo):
    """``RelationalRepo`` en memoria con atomicidad y fallo inyectable.

    Solo implementa lo que ``ClassificationService`` usa (``get`` y
    ``add_all``); el resto de la interfaz se cubre con ``NotImplementedError``
    para dejar claro que el servicio no depende de ellos.

    ``fallar_add_all`` fuerza un error de escritura; la operación es atómica:
    un fallo no deja cambios parciales (Requirement 3.6).
    """

    def __init__(self) -> None:
        self._store: dict[tuple[type, Any], Base] = {}
        self.fallar_add_all = False
        self.add_all_llamadas = 0

    # -- clave primaria por modelo --------------------------------------
    @staticmethod
    def _pk(entity: Base) -> tuple[type, Any]:
        if isinstance(entity, Observacion):
            return (Observacion, entity.id_observacion)
        if isinstance(entity, ObservacionManifestacion):
            return (
                ObservacionManifestacion,
                (entity.id_observacion, entity.id_manifestacion),
            )
        raise NotImplementedError(type(entity))

    # -- siembra directa para preparar el estado inicial ----------------
    def sembrar(self, entity: Base) -> None:
        self._store[self._pk(entity)] = copy.deepcopy(entity)

    def vinculos_de(self, id_observacion: str) -> list[str]:
        return sorted(
            v.id_manifestacion
            for (modelo, _), v in self._store.items()
            if modelo is ObservacionManifestacion
            and v.id_observacion == id_observacion
        )

    # -- API usada por el servicio --------------------------------------
    def get(self, model: type[Base], pk: Any) -> Base | None:
        entity = self._store.get((model, pk))
        return copy.deepcopy(entity) if entity is not None else None

    def add_all(self, entities: list[Base]) -> None:
        self.add_all_llamadas += 1
        if self.fallar_add_all:
            # Falla antes de tocar el almacén → sin cambios parciales.
            raise RuntimeError("fallo simulado de la base de datos")
        # Transacción atómica: se construye el nuevo estado y se aplica de golpe.
        nuevo = dict(self._store)
        for entity in entities:
            nuevo[self._pk(entity)] = copy.deepcopy(entity)
        self._store = nuevo

    # -- resto de la interfaz: no la usa este servicio ------------------
    def add(self, entity: Base) -> Base:  # pragma: no cover
        raise NotImplementedError

    def list(self, model: type[Base], **filters: Any) -> list[Base]:  # pragma: no cover
        raise NotImplementedError

    def delete(self, model: type[Base], pk: Any) -> bool:  # pragma: no cover
        raise NotImplementedError

    def count(self, model: type[Base], **filters: Any) -> int:  # pragma: no cover
        raise NotImplementedError

    def ninos_por_jardin(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def ninos_por_sala(self, id_jardin: str, sala_grupo: str):  # pragma: no cover
        raise NotImplementedError

    def observaciones_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def manifestaciones_de_observacion(self, id_observacion: str):  # pragma: no cover
        raise NotImplementedError

    def bitacoras_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def recomendaciones_de_nino(self, id_nino: str):  # pragma: no cover
        raise NotImplementedError

    def rubrica_vigente(self):  # pragma: no cover
        raise NotImplementedError

    def contar_ninos_por_sala(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    def contar_decisiones(self, id_jardin: str):  # pragma: no cover
        raise NotImplementedError

    # --- Agregaciones periódicas (reporte de dirección, no ejercitadas) ---
    def conteos_nivel_por_sala(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles_por_sala(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def distribucion_niveles_por_dominio(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def contar_observaciones_periodo(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def contar_bitacoras_periodo(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def alertas_retroceso(
        self, id_jardin, fecha_inicio, fecha_fin
    ):  # pragma: no cover
        raise NotImplementedError

    def alertas_inactividad(
        self, id_jardin, fecha_fin, dias: int = 14
    ):  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
def _observacion_sin_clasificar(id_obs: str = "OBS-1") -> Observacion:
    """Observación recién creada, aún sin nivel ni manifestaciones."""
    return Observacion(
        id_observacion=id_obs,
        id_nino="NINO-1",
        id_educadora="EDU-1",
        fecha_observacion=date(2026, 10, 13),
        formato_captura=FormatoCaptura.texto,
        nivel_estimado=None,
        nota_breve="esperó su turno y consoló a un amigo",
        edad_meses=36,
    )


def _propuesta() -> ClasificacionPropuesta:
    return ClasificacionPropuesta(
        nivel_estimado=3,
        dominios=[Dominio.socioemocional],
        manifestaciones=["M-N3-SOC-1", "M-N3-SOC-2"],
        confianza=0.9,
        pendiente_clasificacion_manual=False,
    )


# ---------------------------------------------------------------------------
# 3.3 — proponer devuelve la propuesta SIN persistir
# ---------------------------------------------------------------------------
class TestProponer:
    def test_devuelve_propuesta_sin_persistir(self) -> None:
        """Requirement 3.3: se devuelve la propuesta y no se escribe nada."""
        repo = _FakeRelationalRepo()
        repo.sembrar(_observacion_sin_clasificar())
        clf = _StubClassifier(_propuesta())
        svc = ClassificationService(clf, repo)

        prop = svc.proponer("esperó su turno y consoló a un amigo")

        assert prop == _propuesta()
        assert clf.textos == ["esperó su turno y consoló a un amigo"]
        # Nada persistido: no se llamó a add_all y la observación sigue sin nivel.
        assert repo.add_all_llamadas == 0
        guardada = repo.get(Observacion, "OBS-1")
        assert guardada is not None and guardada.nivel_estimado is None
        assert repo.vinculos_de("OBS-1") == []


# ---------------------------------------------------------------------------
# 3.4 — confirmar persiste la propuesta
# ---------------------------------------------------------------------------
class TestConfirmar:
    def test_confirmar_persiste_valores_propuestos(self) -> None:
        """Requirement 3.4: confirmar escribe nivel + manifestaciones vía repo."""
        repo = _FakeRelationalRepo()
        repo.sembrar(_observacion_sin_clasificar())
        svc = ClassificationService(_StubClassifier(_propuesta()), repo)

        resultado = svc.confirmar("OBS-1", _propuesta())

        assert resultado.nivel_estimado == 3
        guardada = repo.get(Observacion, "OBS-1")
        assert guardada is not None and guardada.nivel_estimado == 3
        assert repo.vinculos_de("OBS-1") == ["M-N3-SOC-1", "M-N3-SOC-2"]

    def test_confirmar_pendiente_falla_sin_persistir(self) -> None:
        """Una propuesta pendiente de clasificación manual no se confirma."""
        repo = _FakeRelationalRepo()
        repo.sembrar(_observacion_sin_clasificar())
        pendiente = ClasificacionPropuesta(pendiente_clasificacion_manual=True)
        svc = ClassificationService(_StubClassifier(pendiente), repo)

        with pytest.raises(PersistenciaError) as exc:
            svc.confirmar("OBS-1", pendiente)

        assert "pendiente" in str(exc.value).lower()
        assert repo.add_all_llamadas == 0
        assert repo.get(Observacion, "OBS-1").nivel_estimado is None

    def test_confirmar_observacion_inexistente_falla(self) -> None:
        """Confirmar sobre una observación que no existe → error en español."""
        repo = _FakeRelationalRepo()
        svc = ClassificationService(_StubClassifier(_propuesta()), repo)

        with pytest.raises(PersistenciaError) as exc:
            svc.confirmar("NO-EXISTE", _propuesta())

        assert "no existe" in str(exc.value).lower()
        assert repo.add_all_llamadas == 0


# ---------------------------------------------------------------------------
# 3.4 — corregir persiste los valores corregidos
# ---------------------------------------------------------------------------
class TestCorregir:
    def test_corregir_persiste_valores_corregidos(self) -> None:
        """Requirement 3.4: corregir persiste los valores ajustados por la educadora."""
        repo = _FakeRelationalRepo()
        repo.sembrar(_observacion_sin_clasificar())
        svc = ClassificationService(_StubClassifier(_propuesta()), repo)

        resultado = svc.corregir(
            "OBS-1",
            nivel_estimado=5,
            dominios=[Dominio.motor_fino, Dominio.cognitivo],
            manifestaciones=["M-N5-MOF-1"],
        )

        assert resultado.nivel_estimado == 5
        guardada = repo.get(Observacion, "OBS-1")
        assert guardada is not None and guardada.nivel_estimado == 5
        assert repo.vinculos_de("OBS-1") == ["M-N5-MOF-1"]

    def test_corregir_sobre_clasificacion_previa_reemplaza_nivel(self) -> None:
        """Corregir aplica el nuevo nivel sobre una observación ya clasificada."""
        repo = _FakeRelationalRepo()
        previa = _observacion_sin_clasificar()
        previa.nivel_estimado = 3
        repo.sembrar(previa)
        svc = ClassificationService(_StubClassifier(_propuesta()), repo)

        svc.corregir(
            "OBS-1",
            nivel_estimado=4,
            dominios=[Dominio.lenguaje_comunicacion],
            manifestaciones=["M-N4-LEN-1"],
        )

        assert repo.get(Observacion, "OBS-1").nivel_estimado == 4

    def test_corregir_nivel_fuera_de_rango_falla_validacion(self) -> None:
        """Un nivel corregido fuera de 1–9 lo rechaza el contrato del Módulo A."""
        repo = _FakeRelationalRepo()
        repo.sembrar(_observacion_sin_clasificar())
        svc = ClassificationService(_StubClassifier(_propuesta()), repo)

        with pytest.raises(Exception):
            svc.corregir(
                "OBS-1",
                nivel_estimado=42,
                dominios=[Dominio.cognitivo],
                manifestaciones=["M-X"],
            )
        # No se tocó el repositorio.
        assert repo.add_all_llamadas == 0


# ---------------------------------------------------------------------------
# 3.6 — fallo de persistencia conserva valores previos + error en español
# ---------------------------------------------------------------------------
class TestFalloDePersistencia:
    def test_fallo_conserva_valores_previos_y_error_espanol(self) -> None:
        """Requirement 3.6: ante fallo de ``RelationalRepo`` no hay cambios parciales."""
        repo = _FakeRelationalRepo()
        previa = _observacion_sin_clasificar()
        previa.nivel_estimado = 2  # valor previo que debe conservarse
        repo.sembrar(previa)
        repo.sembrar(
            ObservacionManifestacion(
                id_observacion="OBS-1", id_manifestacion="M-PREVIA"
            )
        )
        repo.fallar_add_all = True
        svc = ClassificationService(_StubClassifier(_propuesta()), repo)

        with pytest.raises(PersistenciaError) as exc:
            svc.confirmar("OBS-1", _propuesta())

        mensaje = str(exc.value)
        # Mensaje en español, sin filtrar el error crudo del "SDK".
        assert "No se pudo guardar la clasificación" in mensaje
        assert "valores previos" in mensaje
        assert "fallo simulado" not in mensaje

        # Estado previo intacto: nivel y vínculo originales, sin los nuevos.
        guardada = repo.get(Observacion, "OBS-1")
        assert guardada is not None and guardada.nivel_estimado == 2
        assert repo.vinculos_de("OBS-1") == ["M-PREVIA"]

    def test_fallo_al_corregir_tambien_conserva_valores(self) -> None:
        """3.6 también aplica a la corrección: sin cambios parciales ante fallo."""
        repo = _FakeRelationalRepo()
        previa = _observacion_sin_clasificar()
        previa.nivel_estimado = 2
        repo.sembrar(previa)
        repo.fallar_add_all = True
        svc = ClassificationService(_StubClassifier(_propuesta()), repo)

        with pytest.raises(PersistenciaError):
            svc.corregir(
                "OBS-1",
                nivel_estimado=7,
                dominios=[Dominio.cognitivo],
                manifestaciones=["M-N7-COG-1"],
            )

        assert repo.get(Observacion, "OBS-1").nivel_estimado == 2
        assert repo.vinculos_de("OBS-1") == []
