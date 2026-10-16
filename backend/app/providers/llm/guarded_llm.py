"""Decorador del ``LlmProvider`` con resguardo de datos sensibles (Transversal).

Envuelve **cualquier** implementación de :class:`~app.providers.llm.base.LlmProvider`
(Bedrock primaria o mock secundaria) y aplica la
:class:`~app.core.despersonalizacion.GuardiaDespersonalizacion` sobre el
``prompt`` y el ``context`` **antes** de delegar en ``generate``. Si el contenido
contiene datos directamente identificatorios (nombre real, RUT, dirección o dato
de contacto), bloquea el envío al LLM, registra el evento y levanta
:class:`~app.core.despersonalizacion.DatosSensiblesError` (Requirements 11.2,
11.3).

Por qué un decorador (patrón envoltorio):

- **DIP/LSP**: expone el mismo puerto ``LlmProvider``, por lo que es
  intercambiable y los servicios (``BitacoraService``, ``RecommendationService``,
  ``DirectorReportService``) no cambian ni saben que están protegidos.
- **DRY / punto único**: el contenedor de DI cablea el guardia **una sola vez**
  alrededor del proveedor activo, de modo que **todos** los caminos de
  invocación al LLM quedan cubiertos sin duplicar la validación en cada servicio
  (Requirement 11.3 como control transversal).
- **OCP**: cambiar o endurecer la detección no obliga a tocar los adaptadores de
  LLM ni los servicios.
"""

from __future__ import annotations

from app.core.despersonalizacion import GuardiaDespersonalizacion
from app.providers.llm.base import LlmProvider


class GuardedLlmProvider(LlmProvider):
    """``LlmProvider`` que exige contenido despersonalizado antes de generar.

    Args:
        inner: proveedor LLM real al que se delega la generación.
        guardia: guardia de despersonalización; si se omite, se usa una
            instancia por defecto.
    """

    def __init__(
        self,
        inner: LlmProvider,
        guardia: GuardiaDespersonalizacion | None = None,
    ) -> None:
        self._inner = inner
        self._guardia = guardia or GuardiaDespersonalizacion()

    def generate(self, prompt: str, context: str) -> str:
        """Valida y delega: bloquea si hay datos sensibles (11.3).

        Raises:
            DatosSensiblesError: si ``prompt`` o ``context`` contienen datos
                directamente identificatorios. En ese caso **no** se invoca al
                proveedor subyacente: el dato nunca llega al LLM.
            LlmError: propagada desde el proveedor subyacente si la generación
                real falla.
        """
        # Bloquea ANTES de delegar: el dato no permitido no se transmite al LLM.
        self._guardia.exigir_despersonalizado(prompt, context)
        return self._inner.generate(prompt, context)


__all__ = ["GuardedLlmProvider"]
