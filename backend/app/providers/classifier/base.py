"""Interfaz del clasificador de observaciones (puerto del Módulo E, Capa 2).

Define el contrato que el ``ClassificationService`` (Módulo E) usa para estimar,
a partir del texto de una observación, su ``nivel_estimado`` (1–9), sus dominios
(1–5) y las manifestaciones vinculadas (1–10), devolviendo una
``ClasificacionPropuesta`` que la educadora confirma o corrige (Requirements
3.1, 3.2, 3.3). El tipo de retorno vive en ``app.domain.contracts`` para que
todos los módulos lo importen sin dependencias cruzadas; se re-exporta aquí por
conveniencia de los consumidores.

Las implementaciones (basadas en reglas o LLM) son intercambiables tras esta
interfaz.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.contracts import ClasificacionPropuesta


class Classifier(ABC):
    """Puerto de clasificación automática de una observación (Módulo E)."""

    @abstractmethod
    def classify(self, texto: str) -> ClasificacionPropuesta:
        """Clasifica el texto de una observación.

        Args:
            texto: texto (transcrito o directo) de la observación a clasificar.

        Returns:
            Una ``ClasificacionPropuesta`` con el nivel, los dominios y las
            manifestaciones estimadas. Si el texto está vacío o la confianza es
            baja, marca ``pendiente_clasificacion_manual`` sin descartar el texto
            (Requirement 3.5).
        """


__all__ = ["Classifier", "ClasificacionPropuesta"]
