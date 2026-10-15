"""Tests del ``LlmProvider`` — adaptadores Bedrock (primario) y mock (tarea 7.1).

Verifican el contrato del Módulo F en aislamiento, sin llamar a AWS real: el
adaptador Bedrock recibe un **cliente boto3 ``bedrock-runtime`` falso** por
inyección. Cubren (Requirements 5.3, 5.10, 5.4, 6.11):

- Intercambiabilidad (LSP): ambos adaptadores son ``LlmProvider``.
- Mock determinista que devuelve texto en español e incorpora el contexto.
- Adaptador Bedrock: arma la petición Claude, extrae el texto de la respuesta y
  **traduce cualquier fallo del SDK o respuesta inválida a ``LlmError``**.
"""

from __future__ import annotations

import io
import json

import pytest

from app.providers.errors import LlmError, ProviderError
from app.providers.llm.base import LlmProvider
from app.providers.llm.bedrock_llm import BedrockLlmProvider
from app.providers.llm.mock_llm import FAIL_MARKER, MockLlmProvider


# ===========================================================================
# Doble de prueba del cliente boto3 ``bedrock-runtime`` (sin red ni credenciales)
# ===========================================================================
class _FakeBedrockRuntime:
    """Bedrock Runtime falso: devuelve un texto fijo con el formato de Claude 3."""

    def __init__(self, texto: str = "Texto generado de prueba en español.") -> None:
        self._texto = texto
        self.llamadas: list[dict] = []

    def invoke_model(self, **kwargs: object) -> dict:
        self.llamadas.append(dict(kwargs))
        payload = {
            "content": [{"type": "text", "text": self._texto}],
            "stop_reason": "end_turn",
        }
        return {"body": io.BytesIO(json.dumps(payload).encode("utf-8"))}


class _FakeBedrockVacio:
    """Bedrock Runtime falso que devuelve una respuesta sin texto útil."""

    def invoke_model(self, **kwargs: object) -> dict:
        return {"body": io.BytesIO(json.dumps({"content": []}).encode("utf-8"))}


class _FakeBedrockFailing:
    """Bedrock Runtime falso que lanza en cada invocación (simula fallo del SDK)."""

    def __init__(self) -> None:
        self.calls = 0

    def invoke_model(self, **kwargs: object) -> dict:
        self.calls += 1
        raise RuntimeError("fallo del SDK de AWS (p. ej. timeout o cuota)")


# ===========================================================================
# Intercambiabilidad (LSP)
# ===========================================================================
def test_ambos_adaptadores_son_el_puerto() -> None:
    assert issubclass(MockLlmProvider, LlmProvider)
    assert issubclass(BedrockLlmProvider, LlmProvider)
    assert isinstance(MockLlmProvider(), LlmProvider)
    assert isinstance(
        BedrockLlmProvider(bedrock_runtime_client=_FakeBedrockRuntime()), LlmProvider
    )


@pytest.mark.parametrize(
    "provider",
    [
        MockLlmProvider(),
        BedrockLlmProvider(bedrock_runtime_client=_FakeBedrockRuntime()),
    ],
)
def test_generate_devuelve_texto_no_vacio(provider: LlmProvider) -> None:
    """Ambos adaptadores devuelven una cadena no vacía tras la interfaz."""
    salida = provider.generate("Redacta una bitácora.", "Observación O-010.")
    assert isinstance(salida, str)
    assert salida.strip() != ""


# ===========================================================================
# Adaptador mock
# ===========================================================================
def test_mock_es_determinista() -> None:
    prov = MockLlmProvider()
    prompt, context = "Redacta la bitácora del período.", "Observaciones O-1, O-2."
    assert prov.generate(prompt, context) == prov.generate(prompt, context)


def test_mock_distingue_entradas_distintas() -> None:
    prov = MockLlmProvider()
    a = prov.generate("prompt uno", "contexto uno")
    b = prov.generate("prompt dos", "contexto dos")
    assert a != b


def test_mock_devuelve_espanol() -> None:
    """La salida está en español (contiene marcas idiomáticas inequívocas)."""
    prov = MockLlmProvider()
    texto = prov.generate(
        "Redacta un resumen del avance.",
        "La niña apiló tres cubos y nombró los colores.",
    ).lower()
    marcas_es = ("se ", "ñ", "ó", "á", "é", "evidencia", "según", "niñ")
    assert any(m in texto for m in marcas_es)


def test_mock_incorpora_el_contexto() -> None:
    """El mock funda la salida en el contexto (refleja el RAG del LLM real)."""
    prov = MockLlmProvider()
    context = "La niña compartió los materiales y esperó su turno."
    texto = prov.generate("Redacta la bitácora.", context)
    assert "compartió los materiales" in texto


def test_mock_fallo_simulado_lanza_llm_error() -> None:
    prov = MockLlmProvider()
    with pytest.raises(LlmError):
        prov.generate(f"instrucción {FAIL_MARKER}", "contexto")
    with pytest.raises(LlmError):
        prov.generate("instrucción", f"contexto {FAIL_MARKER}")


# ===========================================================================
# Adaptador Bedrock (AWS)
# ===========================================================================
def test_bedrock_devuelve_el_texto_del_modelo() -> None:
    fake = _FakeBedrockRuntime("La niña demostró autonomía al vestirse.")
    prov = BedrockLlmProvider(bedrock_runtime_client=fake, model_id="claude-test")
    texto = prov.generate("Redacta la bitácora.", "Evidencia O-010.")
    assert texto == "La niña demostró autonomía al vestirse."
    assert len(fake.llamadas) == 1


def test_bedrock_envia_prompt_y_contexto_y_modelo() -> None:
    """La petición usa el model_id configurado e incluye prompt y contexto."""
    fake = _FakeBedrockRuntime()
    prov = BedrockLlmProvider(bedrock_runtime_client=fake, model_id="mi-modelo")
    prov.generate("INSTRUCCION-UNICA", "CONTEXTO-UNICO")
    llamada = fake.llamadas[0]
    assert llamada["modelId"] == "mi-modelo"
    cuerpo = json.loads(llamada["body"])
    texto_enviado = cuerpo["messages"][0]["content"][0]["text"]
    assert "INSTRUCCION-UNICA" in texto_enviado
    assert "CONTEXTO-UNICO" in texto_enviado


def test_bedrock_traduce_fallo_del_sdk_a_llm_error() -> None:
    fake = _FakeBedrockFailing()
    prov = BedrockLlmProvider(bedrock_runtime_client=fake)
    with pytest.raises(LlmError) as exc:
        prov.generate("Redacta la bitácora.", "Evidencia O-010.")
    assert fake.calls == 1
    assert "modelo de lenguaje" in str(exc.value)
    # No se filtra el detalle crudo del SDK en el mensaje al usuario.
    assert "SDK" not in str(exc.value)


def test_bedrock_respuesta_vacia_lanza_llm_error() -> None:
    prov = BedrockLlmProvider(bedrock_runtime_client=_FakeBedrockVacio())
    with pytest.raises(LlmError):
        prov.generate("Redacta la bitácora.", "Evidencia O-010.")


def test_llm_error_es_provider_error() -> None:
    """``LlmError`` comparte la raíz tipada del Módulo A (Requirement 13.2)."""
    assert issubclass(LlmError, ProviderError)
