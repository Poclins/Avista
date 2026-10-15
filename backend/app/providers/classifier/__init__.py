"""Puerto de clasificación (Módulo E): interfaz + tipo de retorno + adaptadores."""

from app.domain.contracts import ClasificacionPropuesta
from app.providers.classifier.base import Classifier

__all__ = ["Classifier", "ClasificacionPropuesta"]
