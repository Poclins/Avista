"""Servicio de clasificación de observaciones (Módulo E, Capa 2).

``ClassificationService`` orquesta el caso de uso del Requirement 3: a partir
del texto de una observación produce una **clasificación propuesta** mediante el
puerto ``Classifier`` (Requirement 3.3) y, por separado, **persiste** los valores
que la educadora confirma o corrige mediante el puerto ``RelationalRepo``
(Requirement 3.4). La propuesta no se persiste hasta que haya una acción humana
explícita (confirmar/corregir).

Aislamiento del módulo (interface-first): este servicio depende **solo** del
dominio del Módulo A (``app.domain``, entidades ORM de ``app.repositories.schema``)
y de las **interfaces** ``Classifier`` (``app.providers.classifier.base``) y
``RelationalRepo`` (``app.repositories.relational.base``). No importa ninguna
implementación concreta de un módulo hermano; en pruebas se inyectan fakes.

Garantía de atomicidad (Requirement 3.6): la persistencia de la clasificación
(nivel estimado + vínculos de manifestaciones) se realiza en una **única
operación transaccional** de ``RelationalRepo.add_all``. Si falla, el repositorio
revierte la transacción y los valores previos de la observación se conservan sin
cambios parciales; el servicio relanza ``PersistenciaError`` con un mensaje en
español.
"""

from __future__ import annotations

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import Dominio
from app.providers.classifier.base import Classifier
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Base,
    Observacion,
    ObservacionManifestacion,
)
from app.services.errors import PersistenciaError


class ClassificationService:
    """Caso de uso de clasificación de observaciones (Requirement 3).

    Args:
        classifier: puerto ``Classifier`` que estima nivel/dominios y vincula
            manifestaciones a partir del texto (Requirements 3.1, 3.2).
        repo: puerto ``RelationalRepo`` para persistir la clasificación
            confirmada o corregida (Requirement 3.4).
    """

    def __init__(self, classifier: Classifier, repo: RelationalRepo) -> None:
        self._classifier = classifier
        self._repo = repo

    # -- Propuesta (sin persistir) -----------------------------------------
    def proponer(self, texto: str) -> ClasificacionPropuesta:
        """Devuelve la clasificación **propuesta** sin persistirla.

        Delega en el ``Classifier`` para estimar nivel, dominios y
        manifestaciones. El resultado se presenta a la educadora para que lo
        confirme o corrija; no se escribe nada en el repositorio hasta entonces
        (Requirement 3.3). Si el texto está vacío o la confianza es baja, el
        ``Classifier`` marca ``pendiente_clasificacion_manual`` sin descartar el
        texto (Requirement 3.5).

        Args:
            texto: texto (directo o transcrito) de la observación.

        Returns:
            La ``ClasificacionPropuesta`` estimada, no persistida.
        """
        return self._classifier.classify(texto)

    # -- Confirmación / corrección (persisten) -----------------------------
    def confirmar(
        self, id_observacion: str, propuesta: ClasificacionPropuesta
    ) -> Observacion:
        """Persiste la clasificación **propuesta** tal como la confirma la educadora.

        Aplica a la observación el ``nivel_estimado`` y los ``manifestaciones``
        de la propuesta (Requirement 3.4). Una propuesta marcada como pendiente
        de clasificación manual no puede confirmarse: no aporta valores a
        persistir.

        Args:
            id_observacion: identificador de la observación a actualizar.
            propuesta: la clasificación propuesta que la educadora confirma.

        Returns:
            La observación persistida con la clasificación aplicada.

        Raises:
            PersistenciaError: si la observación no existe, si la propuesta está
                pendiente de clasificación manual, o si falla la escritura en el
                repositorio (los valores previos se conservan intactos).
        """
        if propuesta.pendiente_clasificacion_manual:
            raise PersistenciaError(
                "No se puede confirmar una clasificación pendiente de "
                "clasificación manual; corríjala antes de guardar."
            )
        return self._persistir(
            id_observacion,
            nivel_estimado=propuesta.nivel_estimado,
            dominios=propuesta.dominios,
            manifestaciones=propuesta.manifestaciones,
        )

    def corregir(
        self,
        id_observacion: str,
        *,
        nivel_estimado: int | None,
        dominios: list[Dominio],
        manifestaciones: list[str],
    ) -> Observacion:
        """Persiste la clasificación **corregida** por la educadora.

        Permite que la educadora ajuste nivel, dominios y manifestaciones antes
        de guardar (Requirement 3.4). Normaliza la propuesta corregida con el
        contrato ``ClasificacionPropuesta`` (validación de rango de nivel 1–9 y
        de los topes 1–5 dominios / 1–10 manifestaciones del Módulo A).

        Args:
            id_observacion: identificador de la observación a actualizar.
            nivel_estimado: nivel corregido (1–9) o ``None``.
            dominios: dominios corregidos (del conjunto cerrado).
            manifestaciones: identificadores de manifestaciones corregidos.

        Returns:
            La observación persistida con la clasificación corregida.

        Raises:
            PersistenciaError: si la observación no existe o si falla la
                escritura en el repositorio (valores previos conservados).
        """
        # Validar la corrección contra el contrato compartido (rango/topes).
        correccion = ClasificacionPropuesta(
            nivel_estimado=nivel_estimado,
            dominios=dominios,
            manifestaciones=manifestaciones,
        )
        return self._persistir(
            id_observacion,
            nivel_estimado=correccion.nivel_estimado,
            dominios=correccion.dominios,
            manifestaciones=correccion.manifestaciones,
        )

    # -- Interno -----------------------------------------------------------
    def _persistir(
        self,
        id_observacion: str,
        *,
        nivel_estimado: int | None,
        dominios: list[Dominio],
        manifestaciones: list[str],
    ) -> Observacion:
        """Aplica y persiste la clasificación de forma atómica (Requirement 3.6).

        Lee la observación existente, construye los vínculos de manifestaciones
        y escribe todo en una **única** operación ``add_all`` del repositorio. Si
        la escritura falla, la transacción se revierte y la observación conserva
        sus valores previos; se relanza ``PersistenciaError`` en español sin
        aplicar cambios parciales.
        """
        observacion = self._repo.get(Observacion, id_observacion)
        if observacion is None:
            raise PersistenciaError(
                f"No existe la observación '{id_observacion}'; "
                "no se persistió ninguna clasificación."
            )
        assert isinstance(observacion, Observacion)

        # Aplicar el nivel estimado a la observación.
        observacion.nivel_estimado = nivel_estimado

        # Construir los vínculos observación↔manifestación (sin duplicados,
        # preservando el orden de entrada).
        vistos: set[str] = set()
        vinculos: list[Base] = []
        for id_manifestacion in manifestaciones:
            if id_manifestacion in vistos:
                continue
            vistos.add(id_manifestacion)
            vinculos.append(
                ObservacionManifestacion(
                    id_observacion=id_observacion,
                    id_manifestacion=id_manifestacion,
                )
            )

        # Persistir observación + vínculos en una sola transacción. Si falla,
        # el repositorio revierte y no se aplican cambios parciales (3.6).
        try:
            self._repo.add_all([observacion, *vinculos])
        except Exception as exc:  # noqa: BLE001 — se traduce a error de dominio
            raise PersistenciaError(
                "No se pudo guardar la clasificación; se conservaron los "
                "valores previos de la observación."
            ) from exc

        persistida = self._repo.get(Observacion, id_observacion)
        assert isinstance(persistida, Observacion)
        return persistida


__all__ = ["ClassificationService"]
