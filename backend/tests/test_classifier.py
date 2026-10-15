"""Tests del Módulo E — Clasificación (tarea 6.1).

Verifican el contrato del puerto ``Classifier`` sobre sus dos adaptadores
(``RuleBasedClassifier`` secundario y ``LlmClassifier`` primario) en aislamiento:
solo usan el dominio del Módulo A y un ``LlmProvider`` falso, sin importar
implementaciones concretas de módulos hermanos.

Trazabilidad: Requirements 3.1 (nivel 1–9 + 1–5 dominios), 3.2 (vínculo de 1–10
manifestaciones coherentes) y 3.5 (texto vacío/baja confianza → pendiente de
clasificación manual, sin descartar el texto).
"""

from __future__ import annotations

import pytest

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import NIVEL_MAX, NIVEL_MIN, Dominio, Manifestacion
from app.providers.classifier import (
    Classifier,
    LlmClassifier,
    RuleBasedClassifier,
    build_classifier,
)
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider


# ---------------------------------------------------------------------------
# Fixtures: catálogo de manifestaciones de ejemplo (estilo dataset E-1)
# ---------------------------------------------------------------------------
def _catalogo() -> list[Manifestacion]:
    """Catálogo mínimo con nivel×dominio variados para ejercitar el vínculo."""
    filas = [
        # Nivel 1
        ("M-N1-COG-1", 1, Dominio.cognitivo, "Clasifica objetos por color o forma."),
        ("M-N1-LEN-1", 1, Dominio.lenguaje_comunicacion, "Nombra objetos cotidianos."),
        ("M-N1-MOF-1", 1, Dominio.motor_fino, "Toma objetos pequeños con pinza."),
        ("M-N1-MOG-1", 1, Dominio.motor_grueso, "Se desplaza sorteando un obstaculo."),
        ("M-N1-SOC-1", 1, Dominio.socioemocional, "Comparte un material con un par."),
        # Nivel 3
        ("M-N3-COG-1", 3, Dominio.cognitivo, "Resuelve un rompecabezas con atencion."),
        ("M-N3-LEN-1", 3, Dominio.lenguaje_comunicacion, "Cuenta un relato con frases."),
        ("M-N3-SOC-1", 3, Dominio.socioemocional, "Espera su turno y consuela a un amigo."),
        ("M-N3-SOC-2", 3, Dominio.socioemocional, "Nombra la emocion que siente."),
        ("M-N3-MOG-1", 3, Dominio.motor_grueso, "Corre y salta con equilibrio."),
        # Nivel 5
        ("M-N5-MOF-1", 5, Dominio.motor_fino, "Recorta con tijera siguiendo una linea."),
        ("M-N5-COG-1", 5, Dominio.cognitivo, "Compara cantidades y agrupa por patron."),
    ]
    return [
        Manifestacion(
            id_manifestacion=i, nivel=n, dominio=d, texto_observable=t
        )
        for (i, n, d, t) in filas
    ]


class _FakeLlm(LlmProvider):
    """``LlmProvider`` falso que devuelve una salida predefinida o lanza error."""

    def __init__(self, salida: str = "", *, error: bool = False) -> None:
        self._salida = salida
        self._error = error
        self.llamadas: list[tuple[str, str]] = []

    def generate(self, prompt: str, context: str) -> str:
        self.llamadas.append((prompt, context))
        if self._error:
            raise LlmError("fallo simulado del LLM")
        return self._salida


# ---------------------------------------------------------------------------
# RuleBasedClassifier (camino secundario)
# ---------------------------------------------------------------------------
class TestRuleBasedClassifier:
    def test_texto_vacio_marca_pendiente(self) -> None:
        """Requirement 3.5: texto vacío → pendiente de clasificación manual."""
        clf = RuleBasedClassifier(_catalogo())
        for texto in ["", "   ", "\n\t"]:
            prop = clf.classify(texto)
            assert prop.pendiente_clasificacion_manual is True
            assert prop.nivel_estimado is None
            assert prop.dominios == []
            assert prop.manifestaciones == []

    def test_sin_senal_marca_pendiente(self) -> None:
        """Texto sin relación con el catálogo → pendiente (no se inventa clasificación)."""
        clf = RuleBasedClassifier(_catalogo())
        prop = clf.classify("zzz qqq xkcd lorem ipsum")
        assert prop.pendiente_clasificacion_manual is True

    def test_estima_nivel_y_dominios_dentro_de_rango(self) -> None:
        """Requirement 3.1: nivel entre 1–9 y entre 1–5 dominios del conjunto cerrado."""
        clf = RuleBasedClassifier(_catalogo())
        prop = clf.classify(
            "La niña esperó su turno, consoló a un amigo y nombró la emoción que sentía."
        )
        assert prop.pendiente_clasificacion_manual is False
        assert prop.nivel_estimado is not None
        assert NIVEL_MIN <= prop.nivel_estimado <= NIVEL_MAX
        assert 1 <= len(prop.dominios) <= 5
        assert all(isinstance(d, Dominio) for d in prop.dominios)
        assert Dominio.socioemocional in prop.dominios

    def test_vinculo_coherente_nivel_y_dominio(self) -> None:
        """Requirement 3.2: 1–10 manifestaciones con nivel == estimado y dominio ∈ dominios."""
        catalogo = _catalogo()
        indice = {m.id_manifestacion: m for m in catalogo}
        clf = RuleBasedClassifier(catalogo)
        prop = clf.classify(
            "El niño esperó su turno, consoló a un amigo y nombró su emoción."
        )
        assert prop.pendiente_clasificacion_manual is False
        assert 1 <= len(prop.manifestaciones) <= 10
        for mid in prop.manifestaciones:
            m = indice[mid]
            assert m.nivel == prop.nivel_estimado
            assert m.dominio in prop.dominios

    def test_tope_de_diez_manifestaciones(self) -> None:
        """El vínculo nunca excede 10 manifestaciones aunque haya más candidatas."""
        # Catálogo con 15 manifestaciones del mismo nivel/dominio y texto similar.
        catalogo = [
            Manifestacion(
                id_manifestacion=f"M-N2-SOC-{i:02d}",
                nivel=2,
                dominio=Dominio.socioemocional,
                texto_observable="Comparte material y espera su turno con un amigo.",
            )
            for i in range(15)
        ]
        clf = RuleBasedClassifier(catalogo)
        prop = clf.classify("El niño comparte material y espera su turno con un amigo.")
        assert len(prop.manifestaciones) <= 10

    def test_resultado_es_clasificacion_propuesta(self) -> None:
        """El tipo de retorno es el contrato compartido del Módulo A."""
        clf = RuleBasedClassifier(_catalogo())
        prop = clf.classify("Clasifica objetos por color y forma con atención.")
        assert isinstance(prop, ClasificacionPropuesta)
        assert 0.0 <= prop.confianza <= 1.0

    def test_umbral_de_confianza_marca_pendiente(self) -> None:
        """Requirement 3.5: confianza bajo el umbral → pendiente de clasificación manual."""
        # Umbral imposible de alcanzar fuerza la ruta de baja confianza.
        clf = RuleBasedClassifier(_catalogo(), umbral_confianza=1.0)
        prop = clf.classify("Clasifica objetos por color y forma.")
        assert prop.pendiente_clasificacion_manual is True


# ---------------------------------------------------------------------------
# LlmClassifier (camino primario)
# ---------------------------------------------------------------------------
class TestLlmClassifier:
    def test_salida_valida_produce_clasificacion(self) -> None:
        """Requirements 3.1/3.2: estima nivel/dominios y vincula manifestaciones reales."""
        llm = _FakeLlm(
            '{"nivel_estimado": 3, "dominios": ["socioemocional"], "confianza": 0.9}'
        )
        clf = LlmClassifier(llm, _catalogo())
        prop = clf.classify("El niño esperó su turno y consoló a un amigo.")
        assert prop.pendiente_clasificacion_manual is False
        assert prop.nivel_estimado == 3
        assert prop.dominios == [Dominio.socioemocional]
        assert set(prop.manifestaciones) == {"M-N3-SOC-1", "M-N3-SOC-2"}

    def test_json_con_texto_alrededor(self) -> None:
        """Tolera texto adicional alrededor del objeto JSON."""
        llm = _FakeLlm(
            'Claro, aquí tienes:\n{"nivel_estimado": 1, '
            '"dominios": ["cognitivo"], "confianza": 0.8}\n¡Listo!'
        )
        clf = LlmClassifier(llm, _catalogo())
        prop = clf.classify("Clasifica objetos por color.")
        assert prop.nivel_estimado == 1
        assert prop.dominios == [Dominio.cognitivo]
        assert prop.manifestaciones == ["M-N1-COG-1"]

    def test_fallo_del_llm_marca_pendiente(self) -> None:
        """Requirement 3.5: si el LLM falla, pendiente sin descartar el texto."""
        clf = LlmClassifier(_FakeLlm(error=True), _catalogo())
        prop = clf.classify("Un texto cualquiera de observación.")
        assert prop.pendiente_clasificacion_manual is True

    def test_json_invalido_marca_pendiente(self) -> None:
        """Salida no parseable → pendiente de clasificación manual."""
        clf = LlmClassifier(_FakeLlm("no soy json"), _catalogo())
        prop = clf.classify("Un texto cualquiera.")
        assert prop.pendiente_clasificacion_manual is True

    def test_nivel_fuera_de_rango_marca_pendiente(self) -> None:
        """Un nivel fuera de 1–9 se descarta → pendiente."""
        llm = _FakeLlm('{"nivel_estimado": 42, "dominios": ["cognitivo"], "confianza": 0.9}')
        clf = LlmClassifier(llm, _catalogo())
        prop = clf.classify("Clasifica objetos por color.")
        assert prop.pendiente_clasificacion_manual is True

    def test_dominio_desconocido_se_ignora(self) -> None:
        """Valores de dominio fuera del conjunto cerrado se descartan."""
        llm = _FakeLlm(
            '{"nivel_estimado": 1, "dominios": ["inventado", "cognitivo"], "confianza": 0.9}'
        )
        clf = LlmClassifier(llm, _catalogo())
        prop = clf.classify("Clasifica objetos por color.")
        assert prop.dominios == [Dominio.cognitivo]

    def test_baja_confianza_marca_pendiente(self) -> None:
        """Requirement 3.5: confianza bajo el umbral → pendiente."""
        llm = _FakeLlm('{"nivel_estimado": 1, "dominios": ["cognitivo"], "confianza": 0.1}')
        clf = LlmClassifier(llm, _catalogo(), umbral_confianza=0.5)
        prop = clf.classify("Clasifica objetos por color.")
        assert prop.pendiente_clasificacion_manual is True

    def test_sin_manifestaciones_coherentes_marca_pendiente(self) -> None:
        """Si no hay manifestaciones con ese nivel×dominio, pendiente (3.2)."""
        # Nivel 9 no existe en el catálogo → sin vínculo posible.
        llm = _FakeLlm('{"nivel_estimado": 9, "dominios": ["cognitivo"], "confianza": 0.95}')
        clf = LlmClassifier(llm, _catalogo())
        prop = clf.classify("Clasifica objetos por color.")
        assert prop.pendiente_clasificacion_manual is True

    def test_texto_vacio_no_invoca_al_llm(self) -> None:
        """Texto vacío → pendiente sin llamar al LLM (Requirement 3.5)."""
        llm = _FakeLlm('{"nivel_estimado": 1, "dominios": ["cognitivo"], "confianza": 0.9}')
        clf = LlmClassifier(llm, _catalogo())
        prop = clf.classify("   ")
        assert prop.pendiente_clasificacion_manual is True
        assert llm.llamadas == []


# ---------------------------------------------------------------------------
# Fábrica build_classifier (selección por USE_MOCKS) e intercambiabilidad (LSP)
# ---------------------------------------------------------------------------
class TestFactory:
    def test_use_mocks_true_devuelve_rule_based(self) -> None:
        clf = build_classifier(_catalogo(), use_mocks=True)
        assert isinstance(clf, RuleBasedClassifier)
        assert isinstance(clf, Classifier)

    def test_use_mocks_false_devuelve_llm(self) -> None:
        clf = build_classifier(_catalogo(), use_mocks=False, llm=_FakeLlm("{}"))
        assert isinstance(clf, LlmClassifier)
        assert isinstance(clf, Classifier)

    def test_use_mocks_false_sin_llm_falla(self) -> None:
        with pytest.raises(ValueError):
            build_classifier(_catalogo(), use_mocks=False)

    @pytest.mark.parametrize("use_mocks", [True, False])
    def test_intercambiabilidad_del_contrato(self, use_mocks: bool) -> None:
        """LSP: ambos adaptadores devuelven una ``ClasificacionPropuesta`` válida."""
        llm = _FakeLlm(
            '{"nivel_estimado": 3, "dominios": ["socioemocional"], "confianza": 0.9}'
        )
        clf = build_classifier(_catalogo(), use_mocks=use_mocks, llm=llm)
        prop = clf.classify("El niño esperó su turno y consoló a un amigo.")
        assert isinstance(prop, ClasificacionPropuesta)
        if not prop.pendiente_clasificacion_manual:
            assert NIVEL_MIN <= prop.nivel_estimado <= NIVEL_MAX
            assert 1 <= len(prop.dominios) <= 5
            assert 1 <= len(prop.manifestaciones) <= 10
