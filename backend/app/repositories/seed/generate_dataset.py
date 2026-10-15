"""Generador determinista del dataset sintético E-1.

Produce los archivos JSON bajo ``seed/data/`` que el seed carga en la base
relacional, y el archivo ``distribucion_y_validacion.json`` con los conteos
esperados por tabla (derivados del dataset generado → una única fuente de
verdad para los tests).

El dataset es 100% reproducible: se usa ``random.Random(SEED)`` con semilla
fija y toda la estructura es determinista (ninguna fecha "hoy", ningún UUID).
Volver a ejecutar ``python -m app.repositories.seed.generate_dataset`` produce
exactamente los mismos archivos.

Estructura del dataset E-1 (ver ``docs/MVP_BLUEPRINT.md`` §5):
- ``ruta_niveles``: 9 niveles (1–9) × 5 dominios cada uno.
- ``manifestaciones``: 90 = 9 niveles × 5 dominios × 2 manifestaciones.
- ``jardines`` / ``educadoras`` / ``ninos``: conjunto pequeño y realista.
- ``observaciones`` + ``observacion_manifestaciones``: evidencia que vincula
  niños/as con manifestaciones de su nivel.

Privacidad (Requirement 11.1): ``ninos`` solo tiene ``id_nino`` seudónimo; no
hay nombres reales ni RUT.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from app.domain.models import Dominio, FormatoCaptura

# Semilla fija → dataset reproducible.
SEED = 2026

DATA_DIR = Path(__file__).parent / "data"

# Orden canónico de los 5 dominios.
DOMINIOS: list[str] = [d.value for d in Dominio]

# Número de niveles de la ruta de desarrollo.
N_NIVELES = 9
# Manifestaciones por (nivel, dominio).
MANIF_POR_NIVEL_DOMINIO = 2

# Nombres descriptivos por nivel (ruta de desarrollo 0–72 meses, 9 tramos).
NIVELES_META: list[dict] = [
    {"nombre": "Vínculo inicial", "edad_min": 0, "edad_max": 8},
    {"nombre": "Exploración sensorial", "edad_min": 8, "edad_max": 16},
    {"nombre": "Primeros pasos", "edad_min": 16, "edad_max": 24},
    {"nombre": "Descubrimiento activo", "edad_min": 24, "edad_max": 32},
    {"nombre": "Lenguaje emergente", "edad_min": 32, "edad_max": 40},
    {"nombre": "Juego simbólico", "edad_min": 40, "edad_max": 48},
    {"nombre": "Autonomía creciente", "edad_min": 48, "edad_max": 56},
    {"nombre": "Pensamiento conceptual", "edad_min": 56, "edad_max": 64},
    {"nombre": "Preparación escolar", "edad_min": 64, "edad_max": 72},
]

# Fragmentos de texto observable por dominio (se combinan con el nivel para dar
# variedad plausible sin PII).
TEXTO_POR_DOMINIO: dict[str, list[str]] = {
    "cognitivo": [
        "Clasifica objetos por un atributo (color o forma).",
        "Resuelve un encaje o rompecabezas simple por ensayo y acierto.",
    ],
    "lenguaje_comunicacion": [
        "Nombra objetos cotidianos cuando se le pregunta.",
        "Sigue una instrucción verbal sencilla sin apoyo gestual.",
    ],
    "motor_fino": [
        "Toma objetos pequeños con pinza entre pulgar e índice.",
        "Hace trazos intencionados con un lápiz grueso.",
    ],
    "motor_grueso": [
        "Se desplaza con equilibrio sorteando un obstáculo bajo.",
        "Lanza y recibe una pelota a corta distancia.",
    ],
    "socioemocional": [
        "Comparte un material con un par cuando la educadora lo propone.",
        "Expresa una emoción nombrándola ('estoy contento').",
    ],
}


def _manif_id(nivel: int, dominio: str, idx: int) -> str:
    """Id estable de manifestación: ``M-{nivel}-{dominio_abbr}-{idx}``."""
    abbr = {
        "cognitivo": "COG",
        "lenguaje_comunicacion": "LEN",
        "motor_fino": "MOF",
        "motor_grueso": "MOG",
        "socioemocional": "SOC",
    }[dominio]
    return f"M-N{nivel}-{abbr}-{idx}"


def _build_ruta_niveles() -> list[dict]:
    niveles: list[dict] = []
    for i, meta in enumerate(NIVELES_META, start=1):
        niveles.append(
            {
                "nivel": i,
                "nombre_nivel": meta["nombre"],
                "edad_min_meses": meta["edad_min"],
                "edad_max_meses": meta["edad_max"],
                "dominios": list(DOMINIOS),
                "descripcion": (
                    f"Nivel {i} de la ruta de desarrollo: {meta['nombre']} "
                    f"({meta['edad_min']}–{meta['edad_max']} meses)."
                ),
            }
        )
    return niveles


def _build_manifestaciones() -> list[dict]:
    manifestaciones: list[dict] = []
    for nivel in range(1, N_NIVELES + 1):
        for dominio in DOMINIOS:
            for idx in range(1, MANIF_POR_NIVEL_DOMINIO + 1):
                texto_base = TEXTO_POR_DOMINIO[dominio][idx - 1]
                manifestaciones.append(
                    {
                        "id_manifestacion": _manif_id(nivel, dominio, idx),
                        "nivel": nivel,
                        "dominio": dominio,
                        "texto_observable": f"[N{nivel}] {texto_base}",
                    }
                )
    return manifestaciones


def _build_jardines() -> list[dict]:
    return [
        {
            "id_jardin": "J-001",
            "nombre_fantasia": "Los Girasoles",
            "comuna": "Maipú",
            "region": "Región Metropolitana",
            "numero_salas": 2,
            "numero_educadoras": 3,
        },
        {
            "id_jardin": "J-002",
            "nombre_fantasia": "Pequeños Exploradores",
            "comuna": "Valparaíso",
            "region": "Valparaíso",
            "numero_salas": 1,
            "numero_educadoras": 2,
        },
    ]


def _build_educadoras(rng: random.Random, jardines: list[dict]) -> list[dict]:
    educadoras: list[dict] = []
    contador = 1
    for jardin in jardines:
        for _ in range(jardin["numero_educadoras"]):
            educadoras.append(
                {
                    "id_educadora": f"E-{contador:03d}",
                    "id_jardin": jardin["id_jardin"],
                    "rol": "educadora",
                    "anios_experiencia": rng.randint(1, 20),
                }
            )
            contador += 1
    return educadoras


# Salas por jardín (claves estables usadas al generar niños/as).
SALAS_POR_JARDIN: dict[str, list[str]] = {
    "J-001": ["Sala Cuna", "Nivel Medio"],
    "J-002": ["Nivel Medio"],
}

# Niños/as por sala.
NINOS_POR_SALA = 4


def _build_ninos(rng: random.Random, jardines: list[dict]) -> list[dict]:
    ninos: list[dict] = []
    contador = 1
    base = date(2024, 1, 1)
    for jardin in jardines:
        for sala in SALAS_POR_JARDIN[jardin["id_jardin"]]:
            for _ in range(NINOS_POR_SALA):
                edad_meses = rng.randint(6, 70)
                nacimiento = base - timedelta(days=int(edad_meses * 30.4))
                ingreso = base - timedelta(days=rng.randint(30, 365))
                ninos.append(
                    {
                        "id_nino": f"N-{contador:03d}",
                        "id_jardin": jardin["id_jardin"],
                        "fecha_nacimiento": nacimiento.isoformat(),
                        "sexo_registrado": rng.choice(["F", "M"]),
                        "sala_grupo": sala,
                        "fecha_ingreso": ingreso.isoformat(),
                    }
                )
                contador += 1
    return ninos


# Observaciones por niño/a.
OBS_POR_NINO = 3


def _nivel_estimado_para(rng: random.Random, nino: dict) -> int:
    """Deriva un nivel plausible 1–9 según la edad del niño/a."""
    nacimiento = date.fromisoformat(nino["fecha_nacimiento"])
    ref = date(2024, 1, 1)
    edad_meses = max(0, (ref - nacimiento).days // 30)
    # 8 meses de ancho por nivel → nivel 1..9.
    nivel = min(N_NIVELES, max(1, edad_meses // 8 + 1))
    # Pequeña variación acotada para dar realismo (sin salir de 1..9).
    nivel = min(N_NIVELES, max(1, nivel + rng.choice([-1, 0, 0, 1])))
    return nivel


def _build_observaciones(
    rng: random.Random,
    ninos: list[dict],
    educadoras: list[dict],
    manifestaciones: list[dict],
) -> tuple[list[dict], list[dict]]:
    observaciones: list[dict] = []
    vinculos: list[dict] = []

    # Index de manifestaciones por (nivel, dominio) para vincular evidencia.
    manif_por_nivel: dict[int, list[dict]] = {}
    for m in manifestaciones:
        manif_por_nivel.setdefault(m["nivel"], []).append(m)

    educadoras_por_jardin: dict[str, list[dict]] = {}
    for e in educadoras:
        educadoras_por_jardin.setdefault(e["id_jardin"], []).append(e)

    formatos = [f.value for f in FormatoCaptura]
    contador_obs = 1
    base = date(2024, 2, 1)

    for nino in ninos:
        nivel = _nivel_estimado_para(rng, nino)
        edus = educadoras_por_jardin[nino["id_jardin"]]
        for j in range(OBS_POR_NINO):
            educadora = rng.choice(edus)
            fecha = base + timedelta(days=rng.randint(0, 60))
            id_obs = f"O-{contador_obs:04d}"
            observaciones.append(
                {
                    "id_observacion": id_obs,
                    "id_nino": nino["id_nino"],
                    "id_educadora": educadora["id_educadora"],
                    "fecha_observacion": fecha.isoformat(),
                    "formato_captura": rng.choice(formatos),
                    "nivel_estimado": nivel,
                    "nota_breve": "",
                    "edad_meses": None,
                }
            )
            # Vincula 1–2 manifestaciones del nivel estimado (dominios variados).
            candidatas = manif_por_nivel[nivel]
            k = rng.randint(1, 2)
            elegidas = rng.sample(candidatas, k=min(k, len(candidatas)))
            for m in elegidas:
                vinculos.append(
                    {
                        "id_observacion": id_obs,
                        "id_manifestacion": m["id_manifestacion"],
                    }
                )
            contador_obs += 1

    return observaciones, vinculos


def _build_rubrica_versiones() -> list[dict]:
    """Una versión inicial de rúbrica (determinista) para el seed base."""
    return [
        {
            "version_rubrica": "v1",
            "criterios": {
                "n_observaciones_consistentes": 3,
                "dominios_requeridos": list(DOMINIOS),
                "umbral_score_avanzar": 0.8,
                "umbral_score_retroceder": 0.3,
                "k_observaciones_retroceso": 3,
            },
            "vigente_desde": "2024-01-01",
            "descripcion": "Versión inicial de la rúbrica determinista del MVP.",
        }
    ]


def build_dataset() -> dict[str, list[dict]]:
    """Construye el dataset E-1 completo de forma determinista."""
    rng = random.Random(SEED)

    ruta_niveles = _build_ruta_niveles()
    manifestaciones = _build_manifestaciones()
    jardines = _build_jardines()
    educadoras = _build_educadoras(rng, jardines)
    ninos = _build_ninos(rng, jardines)
    observaciones, vinculos = _build_observaciones(
        rng, ninos, educadoras, manifestaciones
    )
    rubrica_versiones = _build_rubrica_versiones()

    return {
        "ruta_niveles": ruta_niveles,
        "manifestaciones": manifestaciones,
        "jardines": jardines,
        "educadoras": educadoras,
        "ninos": ninos,
        "observaciones": observaciones,
        "observacion_manifestaciones": vinculos,
        "rubrica_versiones": rubrica_versiones,
    }


def build_distribucion(dataset: dict[str, list[dict]]) -> dict:
    """Deriva los conteos esperados por tabla desde el dataset generado."""
    manifestaciones = dataset["manifestaciones"]

    manif_por_dominio: dict[str, int] = {d: 0 for d in DOMINIOS}
    manif_por_nivel: dict[str, int] = {str(n): 0 for n in range(1, N_NIVELES + 1)}
    for m in manifestaciones:
        manif_por_dominio[m["dominio"]] += 1
        manif_por_nivel[str(m["nivel"])] += 1

    return {
        "conteos": {
            tabla: len(filas) for tabla, filas in dataset.items()
        },
        "manifestaciones_por_dominio": manif_por_dominio,
        "manifestaciones_por_nivel": manif_por_nivel,
    }


def write_files() -> None:
    """Genera y escribe todos los archivos JSON del dataset + distribución."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataset = build_dataset()

    for tabla, filas in dataset.items():
        path = DATA_DIR / f"{tabla}.json"
        path.write_text(
            json.dumps(filas, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    distribucion = build_distribucion(dataset)
    (DATA_DIR / "distribucion_y_validacion.json").write_text(
        json.dumps(distribucion, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":  # pragma: no cover
    write_files()
    print(f"Dataset E-1 generado en {DATA_DIR}")
