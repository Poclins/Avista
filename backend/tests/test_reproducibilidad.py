"""Tests de la verificación de reproducibilidad del Dataset E-1 oficial (tarea 3.9).

Requirements 10.10 / 14.5: la verificación re-ejecuta ``generador.py`` con la
**semilla ``20261013``** y la **fecha de referencia ``2026-10-13``**, confirma
salida **idéntica bit a bit** (hashes publicados coincidentes) y que
``validador.py`` finaliza **sin errores**.

Los artefactos oficiales del desafío (``generador.py``, ``validador.py``,
``dataset_e1_publico.zip``, hashes publicados) **no se versionan** en este
repositorio. Por eso los tests:

- ejercitan el **mecanismo de verificación** completo con un generador/validador
  *stand-in* mínimo (que escribe un dataset determinista y reporta OK), de modo
  que el camino "regenerar → hashear → comparar bit a bit → validar" quede
  cubierto sin depender de artefactos externos;
- verifican que, cuando faltan los artefactos, la verificación **no da un falso
  positivo** sino que lanza :class:`ArtefactosNoDisponiblesError` en español;
- verifican el **determinismo real** del generador reducido/casero que sí vive
  en el repo (``generate_dataset.py``): re-ejecutarlo produce una salida
  **idéntica bit a bit**.
"""

from __future__ import annotations

import json
import textwrap
import zipfile
from pathlib import Path

import pytest

from app.repositories.seed.generate_dataset import build_dataset, build_distribucion
from app.repositories.seed.reproducibilidad import (
    FECHA_REFERENCIA_OFICIAL,
    SEMILLA_OFICIAL,
    ArtefactosNoDisponiblesError,
    HashesNoCoincidenError,
    ResultadoReproducibilidad,
    ValidadorFallidoError,
    cargar_hashes_publicados,
    comparar_hashes,
    hashes_de_directorio,
    hashes_de_zip,
    localizar_artefactos,
    sha256_archivo,
    sha256_bytes,
    verificar_reproducibilidad,
)


# ===========================================================================
# Constantes oficiales
# ===========================================================================
def test_constantes_oficiales_de_semilla_y_fecha() -> None:
    """La semilla y la fecha de referencia son las oficiales del desafío."""
    assert SEMILLA_OFICIAL == 20261013
    assert FECHA_REFERENCIA_OFICIAL == "2026-10-13"


# ===========================================================================
# Hashing byte-exacto
# ===========================================================================
def test_sha256_bytes_es_determinista() -> None:
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert sha256_bytes(b"abc") != sha256_bytes(b"abd")


def test_sha256_archivo_coincide_con_bytes(tmp_path: Path) -> None:
    datos = "contenido áéí\n".encode("utf-8")
    f = tmp_path / "x.txt"
    f.write_bytes(datos)
    assert sha256_archivo(f) == sha256_bytes(datos)


def test_hashes_de_directorio_orden_canonico(tmp_path: Path) -> None:
    (tmp_path / "b.csv").write_text("b", encoding="utf-8")
    (tmp_path / "a.csv").write_text("a", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.csv").write_text("c", encoding="utf-8")

    hashes = hashes_de_directorio(tmp_path)
    # Claves en orden canónico (ordenadas, separador POSIX).
    assert list(hashes.keys()) == ["a.csv", "b.csv", "sub/c.csv"]
    assert hashes["a.csv"] == sha256_bytes(b"a")


def test_hashes_de_zip_usa_contenido_descomprimido(tmp_path: Path) -> None:
    ruta_zip = tmp_path / "d.zip"
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("datos_publicos/ninos.csv", "id_nino\nN-001\n")
    hashes = hashes_de_zip(ruta_zip)
    assert hashes["datos_publicos/ninos.csv"] == sha256_bytes(
        "id_nino\nN-001\n".encode("utf-8")
    )


# ===========================================================================
# Carga y comparación de hashes publicados
# ===========================================================================
def test_cargar_hashes_json_plano(tmp_path: Path) -> None:
    f = tmp_path / "hashes.json"
    f.write_text(json.dumps({"ninos.csv": "ABCDEF"}), encoding="utf-8")
    assert cargar_hashes_publicados(f) == {"ninos.csv": "abcdef"}


def test_cargar_hashes_json_anidado(tmp_path: Path) -> None:
    f = tmp_path / "hashes.json"
    f.write_text(json.dumps({"archivos": {"a.csv": "AA"}}), encoding="utf-8")
    assert cargar_hashes_publicados(f) == {"a.csv": "aa"}


def test_cargar_hashes_formato_sha256sums(tmp_path: Path) -> None:
    f = tmp_path / "SHA256SUMS"
    f.write_text("aa11  ninos.csv\nbb22  *jardines.csv\n", encoding="utf-8")
    assert cargar_hashes_publicados(f) == {
        "ninos.csv": "aa11",
        "jardines.csv": "bb22",
    }


def test_comparar_hashes_coincidencia_por_nombre_base() -> None:
    calc = {"datos_publicos/ninos.csv": "aa", "datos_publicos/jardines.csv": "bb"}
    pub = {"ninos.csv": "AA", "jardines.csv": "BB"}
    assert comparar_hashes(calc, pub) == []


def test_comparar_hashes_detecta_discrepancia_y_ausencia() -> None:
    calc = {"ninos.csv": "aa"}
    pub = {"ninos.csv": "zz", "jardines.csv": "bb"}
    disc = comparar_hashes(calc, pub)
    assert any("ninos.csv" in d for d in disc)
    assert any("jardines.csv" in d for d in disc)
    assert len(disc) == 2


def test_cargar_hashes_publicados_faltante(tmp_path: Path) -> None:
    with pytest.raises(ArtefactosNoDisponiblesError):
        cargar_hashes_publicados(tmp_path / "no_existe.json")


# ===========================================================================
# Fixture: generador/validador "stand-in" mínimos (solo stdlib)
# ===========================================================================
# Un generador determinista que escribe un zip público con la misma estructura
# (carpeta datos_publicos/ + consolidado.json) a partir de la semilla y fecha
# recibidas. Reproduce exactamente el mismo contenido en cada ejecución.
_GENERADOR_STUB = textwrap.dedent(
    '''\
    import argparse, io, csv, json, random, zipfile
    from pathlib import Path

    def main() -> int:
        ap = argparse.ArgumentParser()
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--fecha-referencia", required=True)
        ap.add_argument("--salida", required=True)
        a = ap.parse_args()
        rng = random.Random(a.seed)
        salida = Path(a.salida)
        salida.mkdir(parents=True, exist_ok=True)
        filas = [{"id_nino": f"N-{i:03d}", "n": str(rng.randint(0, 9))}
                 for i in range(1, 6)]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["id_nino", "n"], lineterminator="\\n")
        w.writeheader()
        w.writerows(filas)
        consolidado = {"semilla": a.seed, "fecha_referencia": a.fecha_referencia,
                       "conteos": {"ninos": len(filas)}}
        zpath = salida / "dataset_e1_publico.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("datos_publicos/ninos.csv", buf.getvalue())
            zf.writestr("datos_publicos/consolidado.json",
                        json.dumps(consolidado, ensure_ascii=False, indent=2) + "\\n")
        return 0

    raise SystemExit(main())
    '''
)

_VALIDADOR_STUB = textwrap.dedent(
    '''\
    import sys, zipfile
    def main() -> int:
        objetivo = sys.argv[1]
        with zipfile.ZipFile(objetivo) as zf:
            nombres = set(zf.namelist())
        requeridos = {"datos_publicos/ninos.csv", "datos_publicos/consolidado.json"}
        if not requeridos.issubset(nombres):
            print("faltan archivos", file=sys.stderr)
            return 1
        return 0
    raise SystemExit(main())
    '''
)

_VALIDADOR_STUB_FALLA = "import sys\nraise SystemExit(2)\n"


def _hashes_publicados_desde_zip(ruta_zip: Path) -> dict[str, str]:
    """Deriva los hashes 'publicados' desde una ejecución de referencia."""
    return hashes_de_zip(ruta_zip)


@pytest.fixture()
def artefactos_oficiales(tmp_path: Path) -> Path:
    """Crea un directorio con generador/validador stand-in + hashes publicados.

    Ejecuta el generador una vez para obtener la salida de referencia y publica
    sus hashes, de modo que una segunda ejecución deba coincidir bit a bit.
    """
    raiz = tmp_path / "oficial"
    raiz.mkdir()
    (raiz / "generador.py").write_text(_GENERADOR_STUB, encoding="utf-8")
    (raiz / "validador.py").write_text(_VALIDADOR_STUB, encoding="utf-8")

    # Ejecución de referencia (publicación) → derivar hashes publicados.
    import subprocess
    import sys

    ref = raiz / "_ref"
    subprocess.run(
        [sys.executable, str(raiz / "generador.py"),
         "--seed", str(SEMILLA_OFICIAL),
         "--fecha-referencia", FECHA_REFERENCIA_OFICIAL,
         "--salida", str(ref)],
        check=True,
    )
    publicados = _hashes_publicados_desde_zip(ref / "dataset_e1_publico.zip")
    (raiz / "hashes.json").write_text(
        json.dumps(publicados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return raiz


# ===========================================================================
# Verificación end-to-end (mecanismo completo con stand-ins)
# ===========================================================================
def test_verificacion_exitosa_bit_a_bit(artefactos_oficiales: Path) -> None:
    resultado = verificar_reproducibilidad(artefactos_oficiales)
    assert isinstance(resultado, ResultadoReproducibilidad)
    assert resultado.reproducible is True
    assert resultado.validador_ok is True
    assert resultado.discrepancias == []
    assert resultado.archivos_verificados  # no vacío


def test_verificacion_detecta_salida_no_reproducible(
    artefactos_oficiales: Path,
) -> None:
    """Si los hashes publicados no coinciden, se rechaza (no falso positivo)."""
    (artefactos_oficiales / "hashes.json").write_text(
        json.dumps({"ninos.csv": "0" * 64}), encoding="utf-8"
    )
    with pytest.raises(HashesNoCoincidenError) as exc:
        verificar_reproducibilidad(artefactos_oficiales)
    assert "bit a bit" in str(exc.value)


def test_verificacion_detecta_validador_fallido(
    artefactos_oficiales: Path,
) -> None:
    """Un validador que termina con error se reporta como fallo."""
    (artefactos_oficiales / "validador.py").write_text(
        _VALIDADOR_STUB_FALLA, encoding="utf-8"
    )
    with pytest.raises(ValidadorFallidoError):
        verificar_reproducibilidad(artefactos_oficiales)


def test_verificacion_sin_artefactos_no_da_falso_positivo(tmp_path: Path) -> None:
    """Sin artefactos oficiales, la verificación falla con error en español."""
    with pytest.raises(ArtefactosNoDisponiblesError) as exc:
        verificar_reproducibilidad(tmp_path)
    mensaje = str(exc.value)
    assert "generador.py" in mensaje
    assert "validador.py" in mensaje
    assert "externamente" in mensaje


def test_localizar_artefactos_detecta_lo_presente(
    artefactos_oficiales: Path,
) -> None:
    encontrados = localizar_artefactos(artefactos_oficiales)
    assert "generador" in encontrados
    assert "validador" in encontrados
    assert "hashes" in encontrados


# ===========================================================================
# Determinismo REAL del generador reducido/casero del repo
# ===========================================================================
def test_generador_reducido_es_bit_a_bit_determinista() -> None:
    """Re-ejecutar ``build_dataset`` produce exactamente el mismo contenido.

    Es la propiedad de reproducibilidad que sí se puede ejercitar hoy con los
    artefactos presentes en el repo (dataset reducido/casero), serializando con
    la misma codificación/orden canónico que usa el seed.
    """
    def serializar(dataset: dict) -> bytes:
        payload = {tabla: filas for tabla, filas in dataset.items()}
        payload["__distribucion__"] = build_distribucion(dataset)
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )

    primero = serializar(build_dataset())
    segundo = serializar(build_dataset())
    assert sha256_bytes(primero) == sha256_bytes(segundo)
