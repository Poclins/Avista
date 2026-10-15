"""Verificación de reproducibilidad del Dataset E-1 oficial (Módulo B, tarea 3.9).

Requirements 10.10 / 14.5: el sistema debe incluir una verificación de
reproducibilidad del **Dataset E-1 oficial** que vuelva a ejecutar
``generador.py`` con la **semilla fija ``20261013``** y la **fecha de
referencia ``2026-10-13``** y confirme que:

1. la salida es **idéntica bit a bit** a la publicada (hashes coincidentes), y
2. ``validador.py`` finaliza **sin errores**.

Este módulo implementa el **mecanismo de verificación** (no el generador
oficial en sí). Usa **solo la biblioteca estándar** (``hashlib``, ``pathlib``,
``subprocess``, ``zipfile``, ``json``), coherente con el requisito de que el
Dataset E-1 oficial se regenera y valida bajo **Python 3.12 (solo stdlib)**.

Frontera de encapsulamiento: igual que ``DatasetLoader`` y ``seed``, esta
utilidad vive **detrás de la frontera del seed** del Módulo B; no toca los
servicios ni la lógica de negocio. Es puramente de verificación.

Artefactos oficiales esperados
-------------------------------
La verificación opera sobre los artefactos del **desafío** (que se distribuyen
externamente, no se versionan en este repositorio):

- ``generador.py``  — generador determinista oficial (semilla ``20261013``).
- ``validador.py``  — validador oficial del dataset.
- ``dataset_e1_publico.zip`` — zip público publicado (7 CSV + ``consolidado.json``).
- ``hashes.json`` (o ``SHA256SUMS``) — hashes publicados de los archivos del dataset.

Cuando esos artefactos **no están presentes**, la verificación **no inventa**
resultados: lanza :class:`ArtefactosNoDisponiblesError` con un mensaje en
español indicando exactamente qué falta, de modo que el llamador (p. ej. un
test) pueda **omitir** la verificación de forma explícita en lugar de dar un
falso positivo.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# --- Constantes oficiales del Dataset E-1 (design.md / requirements.md) -----

#: Semilla fija del generador oficial del Dataset E-1.
SEMILLA_OFICIAL = 20261013

#: Fecha de referencia (ISO ``AAAA-MM-DD``) del generador oficial.
FECHA_REFERENCIA_OFICIAL = "2026-10-13"

#: Codificación canónica de los archivos del dataset.
CODIFICACION = "utf-8"

#: Nombres de los artefactos oficiales esperados.
NOMBRE_GENERADOR = "generador.py"
NOMBRE_VALIDADOR = "validador.py"
NOMBRE_ZIP_PUBLICO = "dataset_e1_publico.zip"

#: Posibles nombres del archivo de hashes publicados (se prueban en orden).
NOMBRES_HASHES = ("hashes.json", "hashes_publicados.json", "SHA256SUMS")

#: Tamaño de bloque para hashear archivos grandes sin cargarlos en memoria.
_BLOQUE = 1 << 20  # 1 MiB


class ReproducibilidadError(RuntimeError):
    """Error (en español) del proceso de verificación de reproducibilidad."""


class ArtefactosNoDisponiblesError(ReproducibilidadError):
    """Faltan artefactos oficiales para ejecutar la verificación.

    Se lanza cuando ``generador.py`` / ``validador.py`` / el zip público o los
    hashes publicados no están presentes. **No** significa que la verificación
    falló: significa que no se pudo ejecutar porque faltan insumos externos.
    """


class HashesNoCoincidenError(ReproducibilidadError):
    """La salida regenerada **no** es idéntica bit a bit a la publicada."""


class ValidadorFallidoError(ReproducibilidadError):
    """``validador.py`` terminó con error (código de salida distinto de 0)."""


@dataclass
class ResultadoReproducibilidad:
    """Resultado de una verificación de reproducibilidad.

    Attributes:
        reproducible: ``True`` si todos los hashes coinciden bit a bit.
        validador_ok: ``True`` si ``validador.py`` finalizó sin errores.
        archivos_verificados: nombre → ``sha256`` de cada archivo comparado.
        discrepancias: lista legible de archivos cuyo hash no coincidió.
    """

    reproducible: bool = False
    validador_ok: bool = False
    archivos_verificados: dict[str, str] = field(default_factory=dict)
    discrepancias: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Cálculo de hashes canónicos (byte-exacto, UTF-8, sin normalizar)
# ---------------------------------------------------------------------------
def sha256_bytes(datos: bytes) -> str:
    """SHA-256 (hex) de una secuencia de bytes."""
    return hashlib.sha256(datos).hexdigest()


def sha256_archivo(ruta: str | Path) -> str:
    """SHA-256 (hex) de un archivo, leído en bloques (byte-exacto)."""
    h = hashlib.sha256()
    with Path(ruta).open("rb") as fh:
        for bloque in iter(lambda: fh.read(_BLOQUE), b""):
            h.update(bloque)
    return h.hexdigest()


def hashes_de_zip(ruta_zip: str | Path) -> dict[str, str]:
    """Devuelve ``{nombre_entrada: sha256}`` de cada archivo del zip.

    Hashea el **contenido descomprimido** de cada entrada (no los bytes del zip
    completo), de modo que la comparación sea estable frente a diferencias de
    compresión/empaquetado y refleje la salida **bit a bit** de los datos.
    Las entradas se recorren en **orden canónico** (ordenadas por nombre).
    """
    ruta = Path(ruta_zip)
    if not ruta.is_file():
        raise ArtefactosNoDisponiblesError(
            f"No se encontró el zip del dataset para hashear: {ruta}"
        )
    resultado: dict[str, str] = {}
    try:
        with zipfile.ZipFile(ruta) as zf:
            for nombre in sorted(zf.namelist()):
                if nombre.endswith("/"):
                    continue  # entrada de directorio
                with zf.open(nombre) as fh:
                    resultado[nombre] = sha256_bytes(fh.read())
    except zipfile.BadZipFile as exc:  # pragma: no cover - entrada corrupta
        raise ReproducibilidadError(
            f"El zip del dataset está dañado o no es válido: {ruta}"
        ) from exc
    return resultado


def hashes_de_directorio(directorio: str | Path) -> dict[str, str]:
    """Devuelve ``{ruta_relativa: sha256}`` de todos los archivos del árbol.

    Recorre el directorio en **orden canónico** (rutas relativas ordenadas,
    con separador ``/``), hasheando cada archivo byte a byte.
    """
    raiz = Path(directorio)
    if not raiz.is_dir():
        raise ArtefactosNoDisponiblesError(
            f"No se encontró el directorio del dataset para hashear: {raiz}"
        )
    pares: dict[str, str] = {}
    for ruta in sorted(p for p in raiz.rglob("*") if p.is_file()):
        rel = ruta.relative_to(raiz).as_posix()
        pares[rel] = sha256_archivo(ruta)
    return pares


# ---------------------------------------------------------------------------
# Carga de hashes publicados
# ---------------------------------------------------------------------------
def cargar_hashes_publicados(ruta: str | Path) -> dict[str, str]:
    """Carga los hashes publicados desde ``hashes.json`` o ``SHA256SUMS``.

    Soporta dos formatos:

    - **JSON** (``{"<archivo>": "<sha256>", ...}``), opcionalmente anidado bajo
      una clave ``"archivos"`` / ``"hashes"``.
    - **SHA256SUMS** estilo coreutils (``<sha256>  <archivo>`` por línea).

    Devuelve ``{nombre_archivo: sha256_en_minúsculas}``.
    """
    p = Path(ruta)
    if not p.is_file():
        raise ArtefactosNoDisponiblesError(
            f"No se encontró el archivo de hashes publicados: {p}"
        )
    texto = p.read_text(encoding=CODIFICACION)

    if p.suffix.lower() == ".json" or texto.lstrip().startswith("{"):
        datos = json.loads(texto)
        if isinstance(datos, dict):
            for clave in ("archivos", "hashes", "files"):
                if clave in datos and isinstance(datos[clave], dict):
                    datos = datos[clave]
                    break
        if not isinstance(datos, dict):
            raise ReproducibilidadError(
                "El archivo de hashes publicados no tiene el formato esperado "
                "(se esperaba un objeto {archivo: sha256})."
            )
        return {str(k): str(v).lower() for k, v in datos.items()}

    # Formato SHA256SUMS: "<hash>  <archivo>".
    pares: dict[str, str] = {}
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = linea.split(None, 1)
        if len(partes) != 2:
            continue
        hash_hex, nombre = partes
        pares[nombre.strip().lstrip("*")] = hash_hex.strip().lower()
    if not pares:
        raise ReproducibilidadError(
            f"No se pudieron leer hashes publicados desde: {p}"
        )
    return pares


# ---------------------------------------------------------------------------
# Comparación bit a bit
# ---------------------------------------------------------------------------
def comparar_hashes(
    calculados: dict[str, str], publicados: dict[str, str]
) -> list[str]:
    """Compara dos mapas de hashes y devuelve la lista de discrepancias.

    La comparación se hace por **nombre base** del archivo (p. ej. ``ninos.csv``),
    para tolerar que los hashes publicados usen rutas con o sin la carpeta
    ``datos_publicos/``. Devuelve una lista vacía si todo coincide bit a bit.
    """

    def base(nombre: str) -> str:
        return nombre.rsplit("/", 1)[-1]

    calc_por_base = {base(k): v.lower() for k, v in calculados.items()}
    discrepancias: list[str] = []
    for nombre, esperado in publicados.items():
        b = base(nombre)
        obtenido = calc_por_base.get(b)
        if obtenido is None:
            discrepancias.append(
                f"- '{b}': publicado pero ausente en la salida regenerada."
            )
        elif obtenido != esperado.lower():
            discrepancias.append(
                f"- '{b}': hash distinto (esperado {esperado[:12]}…, "
                f"obtenido {obtenido[:12]}…)."
            )
    return discrepancias


# ---------------------------------------------------------------------------
# Ejecución de los scripts oficiales (solo stdlib, subproceso aislado)
# ---------------------------------------------------------------------------
def _ejecutar_python(
    script: Path, args: list[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    """Ejecuta ``python <script> <args>`` en ``cwd`` capturando salida."""
    cmd = [sys.executable, str(script), *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding=CODIFICACION,
        check=False,
    )


def localizar_artefactos(directorio: str | Path) -> dict[str, Path]:
    """Localiza los artefactos oficiales en ``directorio``.

    Returns:
        ``{"generador": Path, "validador": Path, "zip": Path, "hashes": Path}``
        con las rutas que existen. Las ausentes no se incluyen.
    """
    raiz = Path(directorio)
    encontrados: dict[str, Path] = {}
    if (raiz / NOMBRE_GENERADOR).is_file():
        encontrados["generador"] = raiz / NOMBRE_GENERADOR
    if (raiz / NOMBRE_VALIDADOR).is_file():
        encontrados["validador"] = raiz / NOMBRE_VALIDADOR
    if (raiz / NOMBRE_ZIP_PUBLICO).is_file():
        encontrados["zip"] = raiz / NOMBRE_ZIP_PUBLICO
    for nombre in NOMBRES_HASHES:
        if (raiz / nombre).is_file():
            encontrados["hashes"] = raiz / nombre
            break
    return encontrados


def verificar_reproducibilidad(
    directorio_artefactos: str | Path,
    *,
    salida: str | Path | None = None,
) -> ResultadoReproducibilidad:
    """Verifica la reproducibilidad bit a bit del Dataset E-1 oficial.

    Re-ejecuta ``generador.py`` con la **semilla ``20261013``** y la **fecha de
    referencia ``2026-10-13``** en un directorio de salida **limpio**, compara
    los hashes de la salida regenerada contra los **hashes publicados** y
    ejecuta ``validador.py`` confirmando que finaliza **sin errores**.

    Args:
        directorio_artefactos: carpeta que contiene ``generador.py``,
            ``validador.py``, el zip público publicado y los hashes publicados.
        salida: directorio limpio donde el generador debe escribir. Si es
            ``None``, se usa ``<directorio_artefactos>/_repro_out`` (se crea).

    Returns:
        :class:`ResultadoReproducibilidad` con el detalle de la verificación.

    Raises:
        ArtefactosNoDisponiblesError: si falta ``generador.py``, ``validador.py``
            o los hashes publicados (la verificación no se puede ejecutar).
        HashesNoCoincidenError: si la salida regenerada no es idéntica bit a
            bit a la publicada.
        ValidadorFallidoError: si ``validador.py`` termina con error.
    """
    raiz = Path(directorio_artefactos)
    artefactos = localizar_artefactos(raiz)

    faltantes = [
        nombre
        for nombre, clave in (
            (NOMBRE_GENERADOR, "generador"),
            (NOMBRE_VALIDADOR, "validador"),
            ("hashes publicados", "hashes"),
        )
        if clave not in artefactos
    ]
    if faltantes:
        raise ArtefactosNoDisponiblesError(
            "No es posible verificar la reproducibilidad del Dataset E-1 "
            "oficial: faltan artefactos requeridos en "
            f"'{raiz}': {', '.join(faltantes)}. "
            "Estos artefactos del desafío se distribuyen externamente y no se "
            "versionan en el repositorio."
        )

    dir_salida = Path(salida) if salida is not None else raiz / "_repro_out"
    dir_salida.mkdir(parents=True, exist_ok=True)
    # Limpieza del directorio de salida para garantizar una ejecución "limpia".
    for p in sorted(dir_salida.rglob("*"), reverse=True):
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            p.rmdir()

    # 1) Re-ejecutar el generador oficial con semilla y fecha fijas.
    proc_gen = _ejecutar_python(
        artefactos["generador"],
        [
            "--seed",
            str(SEMILLA_OFICIAL),
            "--fecha-referencia",
            FECHA_REFERENCIA_OFICIAL,
            "--salida",
            str(dir_salida),
        ],
        cwd=raiz,
    )
    if proc_gen.returncode != 0:
        raise ReproducibilidadError(
            "El generador oficial terminó con error "
            f"(código {proc_gen.returncode}).\n{proc_gen.stderr}"
        )

    # 2) Hashear la salida regenerada (zip o directorio) en orden canónico.
    zip_regenerado = dir_salida / NOMBRE_ZIP_PUBLICO
    if zip_regenerado.is_file():
        calculados = hashes_de_zip(zip_regenerado)
    else:
        calculados = hashes_de_directorio(dir_salida)

    publicados = cargar_hashes_publicados(artefactos["hashes"])
    discrepancias = comparar_hashes(calculados, publicados)

    resultado = ResultadoReproducibilidad(
        reproducible=not discrepancias,
        archivos_verificados=calculados,
        discrepancias=discrepancias,
    )
    if discrepancias:
        detalle = "\n".join(discrepancias)
        raise HashesNoCoincidenError(
            "La salida regenerada del Dataset E-1 oficial NO es idéntica bit a "
            "bit a la publicada (hashes no coinciden):\n" + detalle
        )

    # 3) Ejecutar el validador oficial y confirmar que finaliza sin errores.
    objetivo_validador = (
        zip_regenerado if zip_regenerado.is_file() else dir_salida
    )
    proc_val = _ejecutar_python(
        artefactos["validador"],
        [str(objetivo_validador)],
        cwd=raiz,
    )
    if proc_val.returncode != 0:
        raise ValidadorFallidoError(
            "El validador oficial 'validador.py' finalizó con errores "
            f"(código {proc_val.returncode}).\n{proc_val.stderr}"
        )
    resultado.validador_ok = True
    return resultado


__all__ = [
    "SEMILLA_OFICIAL",
    "FECHA_REFERENCIA_OFICIAL",
    "CODIFICACION",
    "NOMBRE_GENERADOR",
    "NOMBRE_VALIDADOR",
    "NOMBRE_ZIP_PUBLICO",
    "NOMBRES_HASHES",
    "ReproducibilidadError",
    "ArtefactosNoDisponiblesError",
    "HashesNoCoincidenError",
    "ValidadorFallidoError",
    "ResultadoReproducibilidad",
    "sha256_bytes",
    "sha256_archivo",
    "hashes_de_zip",
    "hashes_de_directorio",
    "cargar_hashes_publicados",
    "comparar_hashes",
    "localizar_artefactos",
    "verificar_reproducibilidad",
]
