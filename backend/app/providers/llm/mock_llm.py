"""Adaptador **mock** del ``LlmProvider`` (secundario, local/CI).

Deriva texto plausible en español a partir del ``prompt`` y el ``context``, sin
llamar a Bedrock ni a ninguna red, de modo que el Módulo F (bitácoras,
recomendación, reporte) sea verificable en aislamiento (Requirements 5.3, 5.10).

Las salidas son **deterministas**: la misma pareja ``(prompt, context)`` produce
siempre el mismo texto, para que los tests sean reproducibles. El texto imita el
registro sobrio y pedagógico de una educadora (es-CL) e **incorpora fragmentos
del contexto** entregado, reflejando que el LLM real argumenta citando la
evidencia recuperada vía RAG sin inventar datos nuevos.

El mock también simula fallos de forma determinista para poder probar la
traducción a :class:`LlmError` y los plazos del Módulo F: si el ``prompt`` o el
``context`` contienen el marcador ``"__fail__"`` lanza :class:`LlmError`.
"""

from __future__ import annotations

import hashlib

from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider

# Marcador que fuerza un fallo determinista del mock (para tests de fallo/timeout
# del LLM, Requirements 5.4, 6.11).
FAIL_MARKER = "__fail__"

# Aperturas plausibles en español; el índice se elige de forma determinista a
# partir del hash de (prompt+context) para dar variedad estable.
_APERTURAS: tuple[str, ...] = (
    "Durante este período se observa un avance consistente en el niño o niña.",
    "A partir de la evidencia registrada, se describe el siguiente progreso.",
    "Las observaciones del período dan cuenta de los siguientes logros.",
    "Según las notas recopiladas, se aprecia el desarrollo que se detalla.",
    "El registro del período respalda las observaciones que siguen.",
)
_CIERRES: tuple[str, ...] = (
    "Se sugiere mantener el acompañamiento con actividades acordes a su nivel.",
    "Conviene reforzar estas conductas con experiencias cotidianas en la sala.",
    "Se recomienda continuar documentando nuevas evidencias de este avance.",
    "Es oportuno dar continuidad al trabajo pedagógico observado.",
)


def _indice(semilla: str, modulo: int) -> int:
    """Índice determinista en ``[0, modulo)`` derivado de ``semilla``."""
    digest = hashlib.sha256(semilla.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulo


def _resumen_contexto(context: str, max_chars: int = 240) -> str:
    """Compacta el contexto a una sola línea legible, acotada en longitud."""
    plano = " ".join(context.split())
    if len(plano) <= max_chars:
        return plano
    return plano[: max_chars - 1].rstrip() + "…"


class MockLlmProvider(LlmProvider):
    """Implementación mock e intercambiable del puerto LLM.

    No hace llamadas de red; deriva texto en español de forma determinista a
    partir del prompt y el contexto, incorporando fragmentos de este último.
    """

    def generate(self, prompt: str, context: str) -> str:
        if FAIL_MARKER in prompt or FAIL_MARKER in context:
            raise LlmError(
                "No se pudo generar el texto con el modelo de lenguaje "
                "(fallo simulado del proveedor mock)."
            )

        semilla = f"{prompt}\x00{context}"
        apertura = _APERTURAS[_indice(semilla, len(_APERTURAS))]
        cierre = _CIERRES[_indice(semilla + "cierre", len(_CIERRES))]

        partes: list[str] = [apertura]
        contexto = _resumen_contexto(context)
        if contexto:
            # Refleja que el LLM real se funda en la evidencia recuperada (RAG).
            partes.append(f"Evidencia considerada: {contexto}")
        instruccion = " ".join(prompt.split())
        if instruccion:
            partes.append(f"En respuesta a: {instruccion}")
        partes.append(cierre)

        return " ".join(partes)


__all__ = ["MockLlmProvider", "FAIL_MARKER"]
