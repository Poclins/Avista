"""``DatasetLoader`` del Dataset E-1 **oficial** (Módulo B, tarea 3.7).

Lee el **Dataset E-1 oficial** distribuido como ``dataset_e1_publico.zip``
(que contiene una carpeta ``datos_publicos/`` con **siete CSV relacionales**
más ``consolidado.json``) y **mapea cada fila a las entidades ORM** del dominio
(Módulo A, :mod:`app.repositories.schema`).

Los siete CSV relacionales oficiales son::

    jardines, educadoras, ninos, ruta_niveles,
    manifestaciones, observaciones, observacion_manifestaciones

Frontera de encapsulamiento (Requirement 14.1): ``DatasetLoader`` vive
**detrás de la frontera del seed** (`RelationalRepo`/`VectorRepo`). Expone
entidades ORM ya construidas, de modo que **cambiar de dataset** (oficial ↔
reducido casero) **no toca el código de los servicios**: estos solo conocen la
interfaz ``RelationalRepo``.

Determinismo (Requirement 10.10 / 14.5): se usa **solo biblioteca estándar**
(``csv``, ``json``, ``zipfile``, ``pathlib``) bajo Python 3.12, con lectura en
**UTF-8** y recorrido en **orden canónico** (el orden de ``CSV_ORDER``, que
respeta las dependencias de claves foráneas). La lógica de carga/validación de
conteos y el consumo del zip público completo corresponden a las tareas 3.8 y
3.9; esta tarea (3.7) implementa el cargador y su mapeo a entidades ORM.

API (según ``design.md``)::

    DatasetLoader.load(ruta_zip) -> DatasetE1          # extrae/lee el zip público
    DatasetLoader.read_csvs() -> dict[str, list[Row]]  # lee los 7 CSV relacionales
    DatasetLoader.read_consolidado() -> dict            # lee consolidado.json
    DatasetLoader.to_entities(tabla, rows) -> list[Entidad]  # filas → entidades ORM
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from app.core.nombres_sinteticos import nombres_para_nino

from app.repositories.schema import (
    Base,
    Educadora,
    Jardin,
    Manifestacion,
    Nino,
    Observacion,
    ObservacionManifestacion,
    RutaNivel,
)

# Una fila CSV cruda: columnas → valores de texto (tal como las entrega ``csv``).
Row = dict[str, str]

# Carpeta dentro del zip público que contiene los CSV + consolidado.json.
CARPETA_DATOS = "datos_publicos"

# Nombre del archivo de metadatos consolidados dentro del dataset.
NOMBRE_CONSOLIDADO = "consolidado.json"

# Orden canónico de las 7 tablas relacionales: respeta las dependencias de
# claves foráneas (jardines → educadoras/ninos → ruta_niveles →
# manifestaciones → observaciones → observacion_manifestaciones). Es también
# el orden en que ``read_csvs`` recorre los archivos (determinismo).
CSV_ORDER: list[tuple[str, type[Base]]] = [
    ("jardines", Jardin),
    ("educadoras", Educadora),
    ("ninos", Nino),
    ("ruta_niveles", RutaNivel),
    ("manifestaciones", Manifestacion),
    ("observaciones", Observacion),
    ("observacion_manifestaciones", ObservacionManifestacion),
]

# Nombres de las 7 tablas en orden canónico (conveniencia para los consumidores).
TABLAS: tuple[str, ...] = tuple(tabla for tabla, _ in CSV_ORDER)

# Modelo ORM por nombre de tabla.
MODELO_POR_TABLA: dict[str, type[Base]] = {tabla: model for tabla, model in CSV_ORDER}

# Columnas de cada tabla que son enteros (se parsean desde texto CSV).
_INT_FIELDS: dict[str, tuple[str, ...]] = {
    "jardines": ("numero_salas", "numero_educadoras"),
    "educadoras": ("anios_experiencia",),
    "ruta_niveles": ("nivel", "edad_min_meses", "edad_max_meses"),
    "manifestaciones": ("nivel",),
    "observaciones": ("nivel_estimado", "edad_meses"),
}

# Columnas de cada tabla que son fechas ISO (AAAA-MM-DD).
_DATE_FIELDS: dict[str, tuple[str, ...]] = {
    "ninos": ("fecha_nacimiento", "fecha_ingreso"),
    "observaciones": ("fecha_observacion",),
}

# Columnas que son listas serializadas (JSON embebido en una celda CSV).
_LIST_FIELDS: dict[str, tuple[str, ...]] = {
    "ruta_niveles": ("dominios",),
}

# Columnas de texto en las que una celda **vacía** representa ausencia de dato
# (no un valor inválido): nota/formato/nivel ausente se trata como ``NULL``.
# Para ``observaciones`` las columnas numéricas opcionales ya se manejan por
# ``_INT_FIELDS`` (celda vacía → ``None``).
_NULLABLE_TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "observaciones": ("nota_breve",),
}


class DatasetLoaderError(ValueError):
    """Error (en español) al leer o mapear el Dataset E-1 oficial."""


@dataclass
class DatasetE1:
    """Contenido del Dataset E-1 oficial ya leído en memoria.

    Agrupa las filas crudas de los 7 CSV (``csvs``) y el ``consolidado.json``
    (``consolidado``). Es el valor de retorno de :meth:`DatasetLoader.load`:
    un contenedor inmutable de datos que el seed consume para construir las
    entidades ORM, manteniendo el cargador detrás de la frontera del seed.
    """

    csvs: dict[str, list[Row]] = field(default_factory=dict)
    consolidado: dict[str, Any] = field(default_factory=dict)


class DatasetLoader:
    """Cargador del Dataset E-1 oficial (7 CSV + ``consolidado.json``).

    Se construye apuntando a un **directorio** que contiene los archivos del
    dataset (los 7 CSV y ``consolidado.json``), típicamente la carpeta
    ``datos_publicos/`` extraída del zip público. El método de clase
    :meth:`load` ofrece la ruta primaria desde el **zip público**.

    El cargador no conoce la base de datos ni los servicios: solo lee archivos
    y produce entidades ORM del dominio A. Así, el seed puede intercambiar la
    fuente (oficial ↔ casero) sin tocar el resto del sistema.
    """

    def __init__(self, directorio: str | Path) -> None:
        self._dir = Path(directorio)

    # -- Construcción desde el zip público (ruta primaria) -----------------
    @classmethod
    def load(cls, ruta_zip: str | Path) -> DatasetE1:
        """Extrae/lee el **zip público** y devuelve un :class:`DatasetE1`.

        Lee ``dataset_e1_publico.zip`` sin extraerlo a disco: abre cada entrada
        de la carpeta ``datos_publicos/`` directamente desde el archivo zip. Es
        la ruta primaria para cargar el dataset oficial.

        Args:
            ruta_zip: ruta al ``dataset_e1_publico.zip``.

        Returns:
            :class:`DatasetE1` con los 7 CSV y ``consolidado.json`` en memoria.

        Raises:
            DatasetLoaderError: si el zip no existe, no contiene la carpeta de
                datos o le falta alguno de los archivos esperados.
        """
        ruta = Path(ruta_zip)
        if not ruta.is_file():
            raise DatasetLoaderError(
                f"No se encontró el zip del dataset en: {ruta}"
            )

        try:
            with zipfile.ZipFile(ruta) as zf:
                nombres = set(zf.namelist())
                csvs: dict[str, list[Row]] = {}
                for tabla in TABLAS:
                    entrada = cls._entrada_zip(nombres, f"{tabla}.csv")
                    if entrada is None:
                        raise DatasetLoaderError(
                            f"Falta el CSV '{tabla}.csv' en el zip del dataset."
                        )
                    with zf.open(entrada) as fh:
                        texto = io.TextIOWrapper(fh, encoding="utf-8", newline="")
                        csvs[tabla] = cls._leer_filas(texto)

                entrada_cons = cls._entrada_zip(nombres, NOMBRE_CONSOLIDADO)
                if entrada_cons is None:
                    raise DatasetLoaderError(
                        f"Falta '{NOMBRE_CONSOLIDADO}' en el zip del dataset."
                    )
                with zf.open(entrada_cons) as fh:
                    consolidado = json.loads(fh.read().decode("utf-8"))
        except zipfile.BadZipFile as exc:  # pragma: no cover - entrada corrupta
            raise DatasetLoaderError(
                f"El zip del dataset está dañado o no es válido: {ruta}"
            ) from exc

        return DatasetE1(csvs=csvs, consolidado=consolidado)

    @staticmethod
    def _entrada_zip(nombres: set[str], archivo: str) -> str | None:
        """Resuelve la entrada del zip para ``archivo`` dentro de la carpeta.

        Acepta tanto ``datos_publicos/<archivo>`` como ``<archivo>`` en la raíz
        del zip, para tolerar variaciones de empaquetado del dataset oficial.
        """
        candidatos = (f"{CARPETA_DATOS}/{archivo}", archivo)
        for candidato in candidatos:
            if candidato in nombres:
                return candidato
        return None

    # -- Lectura de archivos (desde directorio) ----------------------------
    def read_csvs(self) -> dict[str, list[Row]]:
        """Lee los **7 CSV relacionales** del directorio del dataset.

        Devuelve ``{tabla: [fila, ...]}`` recorriendo las tablas en orden
        canónico (``CSV_ORDER``). Cada fila es un ``dict`` columna → texto, tal
        como las entrega el lector CSV estándar (el casteo a tipos ocurre en
        :meth:`to_entities`).

        Raises:
            DatasetLoaderError: si falta alguno de los 7 CSV.
        """
        csvs: dict[str, list[Row]] = {}
        for tabla in TABLAS:
            path = self._dir / f"{tabla}.csv"
            if not path.is_file():
                raise DatasetLoaderError(
                    f"Falta el CSV '{tabla}.csv' en el directorio del dataset: "
                    f"{self._dir}"
                )
            with path.open("r", encoding="utf-8", newline="") as fh:
                csvs[tabla] = self._leer_filas(fh)
        return csvs

    def read_consolidado(self) -> dict[str, Any]:
        """Lee ``consolidado.json`` del directorio del dataset.

        Raises:
            DatasetLoaderError: si el archivo no existe o no es JSON válido.
        """
        path = self._dir / NOMBRE_CONSOLIDADO
        if not path.is_file():
            raise DatasetLoaderError(
                f"Falta '{NOMBRE_CONSOLIDADO}' en el directorio del dataset: "
                f"{self._dir}"
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DatasetLoaderError(
                f"'{NOMBRE_CONSOLIDADO}' no es un JSON válido: {exc}"
            ) from exc

    @staticmethod
    def _leer_filas(fh: Any) -> list[Row]:
        """Lee todas las filas de un flujo CSV con cabecera, en orden."""
        lector = csv.DictReader(fh)
        return [dict(fila) for fila in lector]

    # -- Mapeo de filas → entidades ORM del dominio A ----------------------
    def to_entities(self, tabla: str, rows: list[Row]) -> list[Base]:
        """Mapea las filas de ``tabla`` a entidades ORM del dominio (Módulo A).

        Cada fila CSV (``dict`` de texto) se castea a los tipos de la columna
        correspondiente del esquema: enteros, fechas ISO y listas JSON. Una
        celda **vacía** en una columna opcional se interpreta como **ausencia
        de registro** (``None``), no como dato inválido (Requirement 14.4):
        nota breve, nivel estimado y edad en meses pueden faltar.

        Args:
            tabla: nombre de una de las 7 tablas (``TABLAS``).
            rows: filas crudas de esa tabla (p. ej. de :meth:`read_csvs`).

        Returns:
            Lista de entidades ORM construidas, en el mismo orden que ``rows``.

        Raises:
            DatasetLoaderError: si la tabla es desconocida o una fila no puede
                mapearse (valor no casteable al tipo esperado).
        """
        model = MODELO_POR_TABLA.get(tabla)
        if model is None:
            raise DatasetLoaderError(f"Tabla desconocida en el dataset: '{tabla}'")

        entidades: list[Base] = []
        for indice, fila in enumerate(rows):
            try:
                datos = self._castear_fila(tabla, fila)
                entidades.append(model(**datos))
            except (ValueError, TypeError) as exc:
                raise DatasetLoaderError(
                    f"No se pudo mapear la fila {indice} de '{tabla}': {exc}"
                ) from exc
        return entidades

    def entidades_por_tabla(
        self, csvs: dict[str, list[Row]] | None = None
    ) -> dict[str, list[Base]]:
        """Mapea **todas** las tablas a entidades ORM, en orden canónico.

        Conveniencia para el seed (tarea 3.8): devuelve
        ``{tabla: [entidad ORM, ...]}`` para las 7 tablas respetando las
        dependencias de claves foráneas. Si ``csvs`` es ``None`` se leen del
        directorio con :meth:`read_csvs`.
        """
        if csvs is None:
            csvs = self.read_csvs()
        return {tabla: self.to_entities(tabla, csvs[tabla]) for tabla in TABLAS}

    # -- Casteo de tipos por columna ---------------------------------------
    def _castear_fila(self, tabla: str, fila: Row) -> dict[str, Any]:
        """Convierte los valores de texto de una fila a los tipos del esquema."""
        datos: dict[str, Any] = dict(fila)

        if tabla == "ninos" and datos.get("id_nino"):
            nombre, paterno, materno = nombres_para_nino(datos["id_nino"])
            datos.setdefault("nombre", nombre)
            datos.setdefault("apellido_paterno", paterno)
            datos.setdefault("apellido_materno", materno)

        for campo in _INT_FIELDS.get(tabla, ()):
            if campo in datos:
                datos[campo] = self._a_int(datos[campo])

        for campo in _DATE_FIELDS.get(tabla, ()):
            if campo in datos:
                datos[campo] = self._a_fecha(datos[campo])

        for campo in _LIST_FIELDS.get(tabla, ()):
            if campo in datos:
                datos[campo] = self._a_lista(datos[campo])

        for campo in _NULLABLE_TEXT_FIELDS.get(tabla, ()):
            if campo in datos and self._es_vacio(datos[campo]):
                datos[campo] = None

        return datos

    @staticmethod
    def _es_vacio(valor: Any) -> bool:
        """``True`` si el valor representa una celda vacía (ausencia de dato)."""
        return valor is None or (isinstance(valor, str) and valor.strip() == "")

    @classmethod
    def _a_int(cls, valor: Any) -> int | None:
        """Castea a ``int``; una celda vacía representa ausencia (``None``)."""
        if cls._es_vacio(valor):
            return None
        return int(str(valor).strip())

    @classmethod
    def _a_fecha(cls, valor: Any) -> date | None:
        """Castea una fecha ISO (AAAA-MM-DD); celda vacía → ``None``."""
        if cls._es_vacio(valor):
            return None
        return date.fromisoformat(str(valor).strip())

    @classmethod
    def _a_lista(cls, valor: Any) -> list[Any]:
        """Castea una celda a lista. Acepta JSON (``["a","b"]``) o CSV simple.

        Una celda vacía produce una lista vacía. Si no es JSON válido, se
        interpreta como lista separada por comas (``"a,b"`` → ``["a", "b"]``).
        """
        if cls._es_vacio(valor):
            return []
        texto = str(valor).strip()
        try:
            parsed = json.loads(texto)
        except json.JSONDecodeError:
            # El Dataset E-1 oficial serializa listas en una celda con el
            # separador "|" (p. ej. dominios de ``ruta_niveles``). Se acepta
            # tambien "," como respaldo del dataset reducido/casero.
            separador = "|" if "|" in texto else ","
            return [p.strip() for p in texto.split(separador) if p.strip()]
        if isinstance(parsed, list):
            return parsed
        return [parsed]


__all__ = [
    "DatasetLoader",
    "DatasetE1",
    "DatasetLoaderError",
    "Row",
    "CSV_ORDER",
    "TABLAS",
    "MODELO_POR_TABLA",
    "CARPETA_DATOS",
    "NOMBRE_CONSOLIDADO",
]
