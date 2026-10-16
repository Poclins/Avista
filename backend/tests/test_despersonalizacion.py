"""Tests del resguardo de datos sensibles — despersonalización (Transversal).

Verifican el control transversal del Requirement 11:

- La :class:`GuardiaDespersonalizacion` detecta nombre real, RUT, dirección y
  datos de contacto, y NO marca el ``id_nino`` seudónimo ni el texto pedagógico
  limpio (11.1, 11.2).
- El decorador :class:`GuardedLlmProvider` **bloquea** el envío al LLM cuando el
  prompt o el contexto contienen datos no permitidos, **registra** el evento sin
  volcar el valor sensible y levanta :class:`DatosSensiblesError`; cuando el
  contenido está limpio, delega en el proveedor subyacente (11.3).
- El contenedor de DI envuelve el ``LlmProvider`` activo con el guardia, de modo
  que todos los servicios (bitácora, recomendación, reporte) quedan protegidos.
- El manejador HTTP traduce ``DatosSensiblesError`` a 422 en español sin filtrar
  el dato detectado.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import registrar_manejadores_errores
from app.core.container import Container, reset_container
from app.core.despersonalizacion import (
    DatosSensiblesError,
    GuardiaDespersonalizacion,
)
from app.providers.llm.base import LlmProvider
from app.providers.llm.guarded_llm import GuardedLlmProvider


# ===========================================================================
# Dobles de prueba
# ===========================================================================
class _LlmEspia(LlmProvider):
    """``LlmProvider`` espía: registra si ``generate`` fue invocado."""

    def __init__(self) -> None:
        self.invocado = False
        self.ultimo: tuple[str, str] | None = None

    def generate(self, prompt: str, context: str) -> str:
        self.invocado = True
        self.ultimo = (prompt, context)
        return "texto generado"


# ===========================================================================
# GuardiaDespersonalizacion — detección por categoría
# ===========================================================================
@pytest.fixture()
def guardia() -> GuardiaDespersonalizacion:
    return GuardiaDespersonalizacion()


def test_texto_pedagogico_limpio_no_tiene_datos_sensibles(guardia):
    texto = (
        "El niño/a N-00042 apiló tres cubos, nombró los colores y esperó su "
        "turno durante la actividad. Evidencia: O-010, O-011."
    )
    assert guardia.inspeccionar(texto).hay_datos_sensibles is False


def test_id_nino_seudonimo_no_es_dato_sensible(guardia):
    # Varios formatos del id_nino seudónimo no deben disparar ninguna categoría.
    for id_nino in ("N-00042", "N00042", "NINO_0001", "nino-0123"):
        assert guardia.inspeccionar(f"Observación del {id_nino}.").categorias == ()


@pytest.mark.parametrize(
    "texto",
    [
        "El RUT del niño es 12.345.678-5.",
        "RUT 12345678-K registrado en la ficha.",
        "9.876.543 - 2",
    ],
)
def test_detecta_rut(guardia, texto):
    assert "rut" in guardia.inspeccionar(texto).categorias


@pytest.mark.parametrize(
    "texto",
    [
        "Nombre: Juan Pérez",
        "El niño Mateo González jugó en el patio.",
        "apellido Fernández Soto",
    ],
)
def test_detecta_nombre_real_etiquetado(guardia, texto):
    assert "nombre" in guardia.inspeccionar(texto).categorias


@pytest.mark.parametrize(
    "texto",
    [
        "Vive en Av. Las Flores 123.",
        "Dirección: Pasaje Los Olivos 45",
        "calle Larga 1200, comuna de prueba",
    ],
)
def test_detecta_direccion(guardia, texto):
    assert "direccion" in guardia.inspeccionar(texto).categorias


@pytest.mark.parametrize(
    "texto",
    [
        "Contacto: apoderado@correo.cl",
        "Teléfono +56 9 1234 5678",
        "llamar al 912345678",
    ],
)
def test_detecta_contacto(guardia, texto):
    assert "contacto" in guardia.inspeccionar(texto).categorias


def test_detecta_varias_categorias_a_la_vez(guardia):
    texto = "Nombre: Juan Pérez, RUT 12.345.678-5, fono +56 9 1234 5678."
    categorias = set(guardia.inspeccionar(texto).categorias)
    assert {"nombre", "rut", "contacto"} <= categorias


def test_exigir_despersonalizado_lanza_y_registra_sin_volcar_el_dato(guardia, caplog):
    with caplog.at_level(logging.WARNING, logger="jaimes.privacidad"):
        with pytest.raises(DatosSensiblesError) as exc:
            guardia.exigir_despersonalizado("Nombre: Juan Pérez", "contexto")

    # El mensaje al usuario no incluye el valor sensible detectado.
    assert "Juan Pérez" not in str(exc.value)
    assert "nombre" in exc.value.categorias
    # Se registró el EVENTO con la categoría, pero NO el valor sensible.
    registros = " ".join(r.getMessage() for r in caplog.records)
    assert "bloqueado" in registros.lower()
    assert "nombre" in registros
    assert "Juan Pérez" not in registros


def test_exigir_despersonalizado_no_lanza_con_texto_limpio(guardia):
    # No debe levantar nada: el texto solo usa id_nino seudónimo.
    guardia.exigir_despersonalizado(
        "Redacta la bitácora del niño/a N-00042.",
        "Evidencia O-010, O-011 del período.",
    )


# ===========================================================================
# GuardedLlmProvider — decorador transversal
# ===========================================================================
def test_decorador_es_el_puerto_llm():
    assert issubclass(GuardedLlmProvider, LlmProvider)
    assert isinstance(GuardedLlmProvider(_LlmEspia()), LlmProvider)


def test_decorador_delega_cuando_el_contenido_esta_limpio():
    espia = _LlmEspia()
    guarded = GuardedLlmProvider(espia)
    salida = guarded.generate(
        "Redacta la bitácora del niño/a N-00042.", "Evidencia O-010."
    )
    assert salida == "texto generado"
    assert espia.invocado is True


def test_decorador_bloquea_dato_en_el_prompt_y_no_invoca_al_llm():
    espia = _LlmEspia()
    guarded = GuardedLlmProvider(espia)
    with pytest.raises(DatosSensiblesError):
        guarded.generate("Resume lo del niño Mateo González.", "Evidencia O-010.")
    # El dato NUNCA llegó al proveedor subyacente (Requirement 11.3).
    assert espia.invocado is False


def test_decorador_bloquea_dato_en_el_contexto_y_no_invoca_al_llm():
    espia = _LlmEspia()
    guarded = GuardedLlmProvider(espia)
    with pytest.raises(DatosSensiblesError):
        guarded.generate("Redacta la bitácora.", "RUT 12.345.678-5 del apoderado.")
    assert espia.invocado is False


# ===========================================================================
# Cableado en el contenedor de DI — todos los servicios quedan protegidos
# ===========================================================================
def test_container_envuelve_el_llm_con_el_guardia():
    reset_container()
    try:
        container = Container()  # USE_MOCKS=true por defecto
        assert isinstance(container.llm_provider, GuardedLlmProvider)
        # El proveedor protegido bloquea datos sensibles end-to-end.
        with pytest.raises(DatosSensiblesError):
            container.llm_provider.generate(
                "Resume lo del niño Mateo González.", "ctx"
            )
    finally:
        reset_container()


# ===========================================================================
# Manejador HTTP — 422 en español sin filtrar el dato
# ===========================================================================
def test_handler_http_traduce_datos_sensibles_a_422_sin_filtrar(caplog):
    app = FastAPI()
    registrar_manejadores_errores(app)

    @app.get("/boom")
    def _boom() -> None:  # pragma: no cover - siempre levanta
        raise DatosSensiblesError(["nombre", "rut"])

    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.WARNING, logger="jaimes.api.errors"):
        r = client.get("/boom")

    assert r.status_code == 422
    body = r.json()
    assert set(body.keys()) == {"detail"}
    detalle = body["detail"].lower()
    assert "datos no permitidos" in detalle
    # Mensaje genérico y seguro: no incluye valores sensibles.
    assert "12.345.678" not in body["detail"]
