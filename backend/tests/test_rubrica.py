"""Tests unitarios de la rúbrica de decisión determinista (`RubricaDecision`).

Cubren (tarea 7.2):
- Derivación del **tramo de sala** por rango etario del niño/a.
- Conducta observable **sin evidencia = pendiente** (sin inferir cumplimiento).
- Ramas de decisión **AVANZAR / MANTENER / RETROCEDER** (incluida la racha).
- **Determinismo**: dos ejecuciones iguales ⇒ mismo resultado.
- Casos borde (sin tramos, nivel inexistente, edad fuera de rango, etc.).

Trazabilidad: Requirements 6.2, 6.3, 6.4, 6.5, 21.3, 21.6.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.contracts import ResultadoRubrica
from app.domain.models import DecisionNivel, FormatoCaptura, Nino, Observacion
from app.domain.rubrica import NUCLEO_POR_DEFECTO, RubricaDecision


# ---------------------------------------------------------------------------
# Fixtures: una rúbrica oficial mínima (3 tramos, 1 núcleo, niveles de prueba)
# ---------------------------------------------------------------------------
def _criterios() -> dict:
    """Rúbrica versionada de prueba con los 3 tramos y conductas simples.

    Para que el emparejamiento de evidencia sea legible en los tests, cada
    conducta usa palabras significativas distintas; el nivel 3 de ``sala_cuna``
    tiene 4 conductas para ejercitar fracciones de cobertura (0.0–1.0).
    """
    return {
        "version": "test-v1",
        "tramos": {
            "sala_cuna": {
                "rango_etario_meses": [0, 24],
                "nucleos": {
                    "identidad_y_autonomia": {
                        "niveles": [
                            {
                                "n": 3,
                                "nombre": "Desarrollando",
                                "descriptor": "...",
                                "conductas_observables": [
                                    "camina sostenida sola distancias cortas",
                                    "explora objetos nuevos manipula curiosidad",
                                    "reconoce rutinas diarias cotidianas sala",
                                    "comparte juguetes pares cercanos interaccion",
                                ],
                            }
                        ]
                    }
                },
            },
            "nivel_medio": {
                "rango_etario_meses": [24, 48],
                "nucleos": {
                    "identidad_y_autonomia": {
                        "niveles": [
                            {
                                "n": 4,
                                "nombre": "Afianzando",
                                "descriptor": "...",
                                "conductas_observables": [
                                    "expresa emociones palabras simples claras"
                                ],
                            }
                        ]
                    }
                },
            },
            "transicion": {
                "rango_etario_meses": [48, 72],
                "nucleos": {
                    "identidad_y_autonomia": {
                        "niveles": [
                            {
                                "n": 5,
                                "nombre": "Integrando",
                                "descriptor": "...",
                                "conductas_observables": [
                                    "resuelve conflictos dialogo propone acuerdos"
                                ],
                            }
                        ]
                    }
                },
            },
        },
        "umbrales": {
            "cobertura_avanzar": 0.8,
            "nucleos_requeridos": ["identidad_y_autonomia"],
            "racha_retroceso": 3,
        },
    }


def _nino(fecha_nacimiento: date) -> Nino:
    """Construye un niño/a de prueba con la fecha de nacimiento indicada."""
    return Nino(
        id_nino="N-001",
        id_jardin="J-001",
        fecha_nacimiento=fecha_nacimiento,
        sexo_registrado="F",
        sala_grupo="sala-cuna-a",
        fecha_ingreso=date(2026, 1, 1),
    )


def _obs(
    id_obs: str,
    nota: str = "",
    nivel: int | None = None,
    fecha: date = date(2026, 10, 1),
    manifestaciones: list[str] | None = None,
) -> Observacion:
    """Construye una observación de prueba con los campos relevantes."""
    return Observacion(
        id_observacion=id_obs,
        id_nino="N-001",
        id_educadora="E-001",
        fecha_observacion=fecha,
        formato_captura=FormatoCaptura.texto,
        nivel_estimado=nivel,
        nota_breve=nota,
        manifestaciones=manifestaciones or [],
    )


FECHA_REF = date(2026, 10, 13)


# ---------------------------------------------------------------------------
# Derivación del tramo por edad
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fecha_nacimiento, tramo_esperado",
    [
        (date(2025, 10, 13), "sala_cuna"),   # 12 meses → [0,24)
        (date(2026, 10, 13), "sala_cuna"),   # 0 meses  → límite inferior
        (date(2023, 10, 13), "nivel_medio"), # 36 meses → [24,48)
        (date(2024, 10, 13), "nivel_medio"), # 24 meses → límite inclusivo
        (date(2021, 10, 13), "transicion"),  # 60 meses → [48,72)
        (date(2022, 10, 13), "transicion"),  # 48 meses → límite inclusivo
    ],
)
def test_derivacion_de_tramo_por_edad(
    fecha_nacimiento: date, tramo_esperado: str
) -> None:
    """Requirement 6.3: el tramo se deriva del rango etario del niño/a."""
    rubrica = RubricaDecision(_criterios())
    nivel = {"sala_cuna": 3, "nivel_medio": 4, "transicion": 5}[tramo_esperado]
    res = rubrica.evaluar(
        _nino(fecha_nacimiento), [], nivel, fecha_referencia=FECHA_REF
    )
    assert res.tramo == tramo_esperado


def test_edad_fuera_de_rango_cae_en_el_extremo_mas_cercano() -> None:
    """Edad mayor al máximo de todos los tramos → tramo de mayor edad."""
    rubrica = RubricaDecision(_criterios())
    # ~120 meses (10 años), por encima de transición [48,72).
    res = rubrica.evaluar(
        _nino(date(2016, 10, 13)), [], 5, fecha_referencia=FECHA_REF
    )
    assert res.tramo == "transicion"


# ---------------------------------------------------------------------------
# Cobertura: conducta sin evidencia = pendiente (Requirement 21.6)
# ---------------------------------------------------------------------------
def test_conducta_sin_evidencia_es_pendiente() -> None:
    """Sin ninguna observación, todas las conductas quedan pendientes."""
    rubrica = RubricaDecision(_criterios())
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), [], 3, fecha_referencia=FECHA_REF
    )
    assert res.conductas_observables_cubiertas == []
    assert len(res.conductas_observables_pendientes) == 4
    assert res.score == 0.0
    assert res.evidencia == []


def test_no_se_infiere_cumplimiento_sin_solape_suficiente() -> None:
    """Evidencia que no solapa con la conducta no la marca como cubierta."""
    rubrica = RubricaDecision(_criterios())
    obs = [_obs("O-1", nota="hoy durmio siesta tranquilo", nivel=3)]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert res.conductas_observables_cubiertas == []
    assert res.score == 0.0


def test_evidencia_respalda_conducta_por_solape_de_texto() -> None:
    """Una nota con tokens coincidentes marca la conducta como cubierta."""
    rubrica = RubricaDecision(_criterios())
    obs = [_obs("O-1", nota="la nina camina sola distancias cortas", nivel=3)]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert "camina sostenida sola distancias cortas" in (
        res.conductas_observables_cubiertas
    )
    assert "O-1" in res.evidencia
    assert res.score == 0.25  # 1 de 4 conductas


def test_evidencia_respalda_por_manifestacion() -> None:
    """Una manifestación citada en la conducta respalda la cobertura."""
    criterios = _criterios()
    # Inyectar un id de manifestación en una conducta y en la observación.
    criterios["tramos"]["sala_cuna"]["nucleos"]["identidad_y_autonomia"][
        "niveles"
    ][0]["conductas_observables"][0] = "camina sola m021 referencia"
    rubrica = RubricaDecision(criterios)
    obs = [_obs("O-1", nota="texto irrelevante aqui", manifestaciones=["M021"])]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert "camina sola m021 referencia" in res.conductas_observables_cubiertas
    assert "O-1" in res.evidencia


# ---------------------------------------------------------------------------
# Ramas de decisión
# ---------------------------------------------------------------------------
def test_avanzar_cuando_cobertura_supera_umbral() -> None:
    """Requirement 6.4: AVANZAR si fracción cubierta ≥ cobertura_avanzar."""
    rubrica = RubricaDecision(_criterios())
    obs = [
        _obs("O-1", nota="camina sostenida sola distancias cortas", nivel=3),
        _obs("O-2", nota="explora objetos nuevos manipula curiosidad", nivel=3),
        _obs("O-3", nota="reconoce rutinas diarias cotidianas sala", nivel=3),
        _obs("O-4", nota="comparte juguetes pares cercanos interaccion", nivel=3),
    ]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert res.score == 1.0
    assert res.decision is DecisionNivel.AVANZAR


def test_mantener_cuando_cobertura_parcial() -> None:
    """Requirement 6.4: MANTENER si la cobertura es parcial (bajo umbral)."""
    rubrica = RubricaDecision(_criterios())
    obs = [
        _obs("O-1", nota="camina sostenida sola distancias cortas", nivel=3),
        _obs("O-2", nota="explora objetos nuevos manipula curiosidad", nivel=3),
    ]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert res.score == 0.5  # 2 de 4, bajo el umbral 0.8
    assert res.decision is DecisionNivel.MANTENER


def test_retroceder_por_racha_de_tres_observaciones_bajo_nivel() -> None:
    """Requirement 6.4: RETROCEDER con racha ≥ 3 consecutivas bajo el nivel."""
    rubrica = RubricaDecision(_criterios())
    obs = [
        _obs("O-1", nivel=2, fecha=date(2026, 9, 1)),
        _obs("O-2", nivel=1, fecha=date(2026, 9, 10)),
        _obs("O-3", nivel=2, fecha=date(2026, 9, 20)),
    ]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert res.decision is DecisionNivel.RETROCEDER


def test_racha_interrumpida_no_retrocede() -> None:
    """Una observación en nivel corta la racha → no RETROCEDER."""
    rubrica = RubricaDecision(_criterios())
    obs = [
        _obs("O-1", nivel=2, fecha=date(2026, 9, 1)),
        _obs("O-2", nivel=3, fecha=date(2026, 9, 10)),  # corta la racha
        _obs("O-3", nivel=2, fecha=date(2026, 9, 20)),
        _obs("O-4", nivel=1, fecha=date(2026, 9, 25)),
    ]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    # Solo hay 2 consecutivas por debajo al final → MANTENER (cobertura 0).
    assert res.decision is DecisionNivel.MANTENER


def test_avanzar_tiene_precedencia_sobre_retroceso() -> None:
    """AVANZAR (cobertura alta) prevalece aunque exista racha de retroceso."""
    rubrica = RubricaDecision(_criterios())
    obs = [
        _obs("O-1", nota="camina sostenida sola distancias cortas", nivel=1),
        _obs("O-2", nota="explora objetos nuevos manipula curiosidad", nivel=1),
        _obs("O-3", nota="reconoce rutinas diarias cotidianas sala", nivel=1),
        _obs("O-4", nota="comparte juguetes pares cercanos interaccion", nivel=1),
    ]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert res.score == 1.0
    assert res.decision is DecisionNivel.AVANZAR


def test_observaciones_sin_nivel_estimado_no_cuentan_para_la_racha() -> None:
    """Observaciones con nivel_estimado=None no forman racha de retroceso."""
    rubrica = RubricaDecision(_criterios())
    obs = [
        _obs("O-1", nivel=None, fecha=date(2026, 9, 1)),
        _obs("O-2", nivel=None, fecha=date(2026, 9, 10)),
        _obs("O-3", nivel=None, fecha=date(2026, 9, 20)),
    ]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    assert res.decision is DecisionNivel.MANTENER


# ---------------------------------------------------------------------------
# Determinismo (Requirement 6.2)
# ---------------------------------------------------------------------------
def test_determinismo_misma_entrada_mismo_resultado() -> None:
    """Dos ejecuciones con la misma entrada producen el mismo resultado."""
    rubrica = RubricaDecision(_criterios())
    nino = _nino(date(2025, 10, 13))
    obs = [
        _obs("O-1", nota="camina sostenida sola distancias cortas", nivel=2),
        _obs("O-2", nota="explora objetos nuevos manipula curiosidad", nivel=2),
    ]
    r1 = rubrica.evaluar(nino, obs, 3, fecha_referencia=FECHA_REF)
    r2 = rubrica.evaluar(nino, obs, 3, fecha_referencia=FECHA_REF)
    assert r1.model_dump() == r2.model_dump()


def test_determinismo_independiente_del_orden_de_observaciones() -> None:
    """El resultado no depende del orden de entrada de las observaciones."""
    rubrica = RubricaDecision(_criterios())
    nino = _nino(date(2025, 10, 13))
    obs = [
        _obs("O-1", nota="camina sostenida sola distancias cortas", nivel=2),
        _obs("O-2", nota="explora objetos nuevos manipula curiosidad", nivel=2),
    ]
    r1 = rubrica.evaluar(nino, obs, 3, fecha_referencia=FECHA_REF)
    r2 = rubrica.evaluar(nino, list(reversed(obs)), 3, fecha_referencia=FECHA_REF)
    assert r1.decision == r2.decision
    assert r1.score == r2.score
    assert set(r1.conductas_observables_cubiertas) == set(
        r2.conductas_observables_cubiertas
    )
    assert set(r1.evidencia) == set(r2.evidencia)


def test_version_rubrica_se_propaga_al_resultado() -> None:
    """La versión de la rúbrica usada se refleja en el resultado."""
    rubrica = RubricaDecision(_criterios())
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), [], 3, fecha_referencia=FECHA_REF
    )
    assert res.version_rubrica == "test-v1"
    assert isinstance(res, ResultadoRubrica)


# ---------------------------------------------------------------------------
# Casos borde
# ---------------------------------------------------------------------------
def test_nivel_inexistente_da_cobertura_cero() -> None:
    """Un nivel sin conductas en la rúbrica → score 0 y MANTENER."""
    rubrica = RubricaDecision(_criterios())
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), [], 7, fecha_referencia=FECHA_REF
    )
    assert res.conductas_observables_cubiertas == []
    assert res.conductas_observables_pendientes == []
    assert res.score == 0.0
    assert res.decision is DecisionNivel.MANTENER


def test_criterios_no_dict_rechazado() -> None:
    """Construir la rúbrica con criterios no-dict lanza ValueError."""
    with pytest.raises(ValueError):
        RubricaDecision([])  # type: ignore[arg-type]


def test_sin_tramos_lanza_error_al_evaluar() -> None:
    """Una rúbrica sin tramos no puede derivar el tramo del niño/a."""
    rubrica = RubricaDecision({"version": "v0", "tramos": {}, "umbrales": {}})
    with pytest.raises(ValueError):
        rubrica.evaluar(
            _nino(date(2025, 10, 13)), [], 3, fecha_referencia=FECHA_REF
        )


def test_fecha_referencia_derivada_de_observaciones() -> None:
    """Sin fecha_referencia explícita, se usa la observación más reciente."""
    rubrica = RubricaDecision(_criterios())
    # Niño que a la fecha de la última observación tiene ~12 meses (sala_cuna).
    nino = _nino(date(2025, 10, 1))
    obs = [_obs("O-1", nota="nota", fecha=date(2026, 10, 1))]
    res = rubrica.evaluar(nino, obs, 3)
    assert res.tramo == "sala_cuna"


# ---------------------------------------------------------------------------
# "Pasos a seguir" por nivel — alcance futuro (Requirement 29, amplía 21.1)
# ---------------------------------------------------------------------------
def test_pasos_a_seguir_ausentes_opera_normalmente() -> None:
    """Req 29.2: una rúbrica SIN ``pasos_a_seguir`` opera normalmente.

    El esquema vigente (conductas observables, sin pasos) sigue parseando y
    evaluando sin error, y los pasos del nivel se tratan como ausentes
    (lista vacía).
    """
    rubrica = RubricaDecision(_criterios())
    nino = _nino(date(2025, 10, 13))
    # La evaluación determinista no se ve afectada por la ausencia del campo.
    res = rubrica.evaluar(nino, [], 3, fecha_referencia=FECHA_REF)
    assert res.tramo == "sala_cuna"
    assert res.decision is DecisionNivel.MANTENER
    # El campo opcional ausente se expone como lista vacía, sin error.
    assert rubrica.pasos_a_seguir_del_nivel("sala_cuna", NUCLEO_POR_DEFECTO, 3) == []


def test_pasos_a_seguir_presentes_se_preservan() -> None:
    """Req 29.1/29.3: una rúbrica CON ``pasos_a_seguir`` preserva el valor.

    El campo opcional por nivel se admite y se expone como parte de los
    criterios del nivel, sin alterar la decisión determinista.
    """
    criterios = _criterios()
    pasos = [
        "ofrecer actividades de marcha asistida en recorridos cortos",
        "proponer exploracion guiada de objetos nuevos",
    ]
    criterios["tramos"]["sala_cuna"]["nucleos"][NUCLEO_POR_DEFECTO]["niveles"][0][
        "pasos_a_seguir"
    ] = pasos
    rubrica = RubricaDecision(criterios)

    # El valor se preserva verbatim al exponerlo.
    assert rubrica.pasos_a_seguir_del_nivel("sala_cuna", NUCLEO_POR_DEFECTO, 3) == pasos


def test_pasos_a_seguir_no_alteran_la_decision_determinista() -> None:
    """Req 29.3 + 6.2: agregar ``pasos_a_seguir`` no cambia la decisión.

    La misma entrada produce el mismo ``ResultadoRubrica`` con y sin el campo
    opcional presente (los pasos son informativos, no entran en la decisión).
    """
    nino = _nino(date(2025, 10, 13))
    obs = [
        _obs("O-1", nota="camina sostenida sola distancias cortas", nivel=3),
        _obs("O-2", nota="explora objetos nuevos manipula curiosidad", nivel=3),
    ]

    sin_pasos = RubricaDecision(_criterios())
    res_sin = sin_pasos.evaluar(nino, obs, 3, fecha_referencia=FECHA_REF)

    criterios_con = _criterios()
    criterios_con["tramos"]["sala_cuna"]["nucleos"][NUCLEO_POR_DEFECTO]["niveles"][
        0
    ]["pasos_a_seguir"] = ["cualquier paso a observar en la proxima actividad"]
    con_pasos = RubricaDecision(criterios_con)
    res_con = con_pasos.evaluar(nino, obs, 3, fecha_referencia=FECHA_REF)

    # La decisión determinista es idéntica con y sin pasos a seguir.
    assert res_sin.model_dump() == res_con.model_dump()


def test_pasos_a_seguir_nivel_inexistente_da_lista_vacia() -> None:
    """Un nivel sin entrada en la rúbrica devuelve pasos vacíos, sin error."""
    rubrica = RubricaDecision(_criterios())
    assert rubrica.pasos_a_seguir_del_nivel("sala_cuna", NUCLEO_POR_DEFECTO, 7) == []


def test_umbrales_por_defecto_cuando_faltan() -> None:
    """Si la rúbrica no define umbrales, se usan los valores por defecto."""
    criterios = _criterios()
    del criterios["umbrales"]
    rubrica = RubricaDecision(criterios)
    obs = [
        _obs("O-1", nota="camina sostenida sola distancias cortas", nivel=3),
        _obs("O-2", nota="explora objetos nuevos manipula curiosidad", nivel=3),
        _obs("O-3", nota="reconoce rutinas diarias cotidianas sala", nivel=3),
        _obs("O-4", nota="comparte juguetes pares cercanos interaccion", nivel=3),
    ]
    res = rubrica.evaluar(
        _nino(date(2025, 10, 13)), obs, 3, fecha_referencia=FECHA_REF
    )
    # Cobertura 1.0 ≥ 0.8 (default) → AVANZAR.
    assert res.decision is DecisionNivel.AVANZAR
