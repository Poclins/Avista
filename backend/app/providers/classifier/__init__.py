"""Puerto de clasificación (Módulo E): interfaz + tipo de retorno + adaptadores.

Expone la interfaz ``Classifier``, el tipo de retorno compartido
``ClasificacionPropuesta`` (dominio del Módulo A) y los dos adaptadores
intercambiables:

- ``LlmClassifier`` — camino **primario** (LLM vía ``LlmProvider``: Bedrock/Claude).
- ``RuleBasedClassifier`` — camino **secundario/local** (reglas léxicas, sin red).

``build_classifier`` selecciona el adaptador según ``USE_MOCKS`` manteniendo el
contrato estable del puerto (Requirements 10.1, 10.4, 13.5).
"""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import Manifestacion
from app.providers.classifier.base import Classifier
from app.providers.classifier.bedrock_llm import LlmClassifier
from app.providers.classifier.rule_based import RuleBasedClassifier
from app.providers.llm.base import LlmProvider


def build_classifier(
    catalogo: Iterable[Manifestacion],
    *,
    use_mocks: bool = True,
    llm: LlmProvider | None = None,
) -> Classifier:
    """Construye el ``Classifier`` adecuado según el modo de ejecución.

    Args:
        catalogo: manifestaciones del dataset E-1 (dominio del Módulo A) usadas
            para vincular 1–10 manifestaciones coherentes.
        use_mocks: ``True`` (local/CI) → ``RuleBasedClassifier`` (sin red);
            ``False`` (AWS) → ``LlmClassifier`` sobre el ``LlmProvider`` dado.
        llm: proveedor LLM requerido cuando ``use_mocks`` es ``False``.

    Returns:
        Una implementación de ``Classifier`` intercambiable tras la interfaz.

    Raises:
        ValueError: si se pide el camino primario (``use_mocks=False``) sin
            proporcionar un ``LlmProvider``.
    """
    if use_mocks:
        return RuleBasedClassifier(catalogo)
    if llm is None:
        raise ValueError(
            "El clasificador primario (LLM) requiere un LlmProvider; "
            "proporcione 'llm' o use use_mocks=True."
        )
    return LlmClassifier(llm, catalogo)


__all__ = [
    "Classifier",
    "ClasificacionPropuesta",
    "LlmClassifier",
    "RuleBasedClassifier",
    "build_classifier",
]
