"""Rúbrica de decisión determinista (`RubricaDecision`) — Módulo F.

Este módulo implementa la **rúbrica oficial** como un componente **puramente
determinista** (sin IA, sin I/O de red): la rúbrica decide, la IA solo argumenta
y la educadora valida (Requirements 6.2, 6.3, 6.4, 6.5).

La rúbrica se consume como **datos versionados** desde ``rubrica_versiones.criterios``
(estructura ``tramo de sala × núcleo × 8 niveles de progresión × conductas
observables`` + descriptor + umbrales). El servicio obtiene esos ``criterios``
vía ``RelationalRepo.rubrica_vigente()`` y los inyecta en el constructor; agregar
tramos o núcleos nuevos es cuestión de datos, **sin cambios de código**
(Requirements 21.3, 21.6).

Determinismo (Requirement 6.2): la misma entrada ``(nino, observaciones, nivel)``
con la misma ``version_rubrica`` produce siempre el mismo ``ResultadoRubrica``.
No se usa reloj del sistema ni aleatoriedad; la fecha de referencia para calcular
la edad del niño/a es explícita e inyectable (``fecha_referencia``) y, si no se
provee, se deriva de forma determinista de las propias observaciones.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any, Iterable

from app.domain.contracts import NivelGeneral, ResultadoRubrica
from app.domain.models import DecisionNivel, Nino, Observacion

# Núcleo por defecto cuando no se especifica (el primero de la rúbrica oficial).
NUCLEO_POR_DEFECTO = "identidad_y_autonomia"

# Umbrales por defecto si la rúbrica no los define explícitamente.
_COBERTURA_AVANZAR_DEFAULT = 0.8
_RACHA_RETROCESO_DEFAULT = 3

# Palabras vacías en español que no aportan señal para el emparejamiento de
# evidencia contra conductas observables (se descartan al tokenizar).
_STOPWORDS = frozenset(
    {
        "a", "al", "ante", "con", "de", "del", "e", "el", "en", "entre", "la",
        "las", "lo", "los", "o", "para", "por", "que", "se", "su", "sus", "un",
        "una", "unas", "unos", "y", "ya", "le", "les", "me", "mi", "mis", "te",
        "tu", "tus", "es", "son", "ser", "esta", "este", "estos", "estas", "sin",
    }
)

# Umbral mínimo de solape de tokens significativos para considerar que una
# observación respalda una conducta observable. Es un valor fijo (determinista).
_MIN_TOKENS_COINCIDENTES = 2

# Identificador real de manifestación del Dataset E-1 (MAN-L08-MF-02).
_MANIFESTACION_ID = re.compile(r"\bMAN-[A-Z0-9-]+\b", re.IGNORECASE)


def _normalizar(texto: str) -> str:
    """Normaliza un texto a minúsculas y sin tildes para comparar de forma estable.

    Quita acentos (NFD + descarte de marcas combinantes) y pasa a minúsculas,
    de modo que "autonomía" y "autonomia" produzcan los mismos tokens.
    """
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _tokenizar(texto: str) -> set[str]:
    """Devuelve el conjunto de tokens significativos de un texto.

    Separa por caracteres no alfanuméricos, descarta palabras vacías y tokens de
    un solo carácter. El resultado es un conjunto (orden irrelevante) para que el
    emparejamiento sea determinista.
    """
    normalizado = _normalizar(texto)
    crudos = "".join(c if c.isalnum() else " " for c in normalizado).split()
    return {t for t in crudos if len(t) > 1 and t not in _STOPWORDS}


class RubricaDecision:
    """Rúbrica determinista versionada (la rúbrica decide, la IA argumenta).

    Recibe los ``criterios`` (dict) de la rúbrica vigente —tal como se almacenan
    en ``rubrica_versiones.criterios``— y expone ``evaluar(...)`` para decidir
    AVANZAR / MANTENER / RETROCEDER sobre la cobertura de conductas observables.

    No realiza I/O ni consulta modelos de IA; es lógica de dominio pura.
    """

    def __init__(self, criterios: dict[str, Any]) -> None:
        """Inicializa la rúbrica con los ``criterios`` versionados.

        ``criterios`` sigue el esquema de ``rubrica_versiones.criterios``:
        ``{"version": str, "tramos": {...}, "umbrales": {...}}``.

        Cada nivel dentro de ``tramos[...]→nucleos[...]→niveles`` puede incluir,
        de forma **opcional**, una lista ``pasos_a_seguir`` (conductas a observar
        en próximas actividades) — **alcance futuro** (Requirement 29, amplía
        21.1). El esquema la tolera y preserva (ver
        :meth:`pasos_a_seguir_del_nivel`) sin requerir cambios de código y sin
        afectar la decisión determinista.
        """
        if not isinstance(criterios, dict):
            raise ValueError("Los criterios de la rúbrica deben ser un dict.")
        self._criterios = criterios
        self._version = str(criterios.get("version", ""))
        self._tramos = criterios.get("tramos", {}) or {}
        self._umbrales = criterios.get("umbrales", {}) or {}

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def evaluar(
        self,
        nino: Nino,
        observaciones_recientes: Iterable[Observacion],
        nivel_actual: int,
        *,
        nucleo: str = NUCLEO_POR_DEFECTO,
        fecha_referencia: date | None = None,
    ) -> ResultadoRubrica:
        """Evalúa la cobertura de conductas observables y decide el nivel.

        Pasos (ver design.md §Rúbrica):
        1. Deriva el **tramo** del rango etario del niño/a.
        2. Selecciona ``núcleo`` (por defecto ``identidad_y_autonomia``) y
           ``nivel_actual`` dentro de la rúbrica.
        3. Mapea la **evidencia previa** del niño/a a las conductas observables
           del ``tramo × núcleo × nivel_actual``: **cubierta** si la evidencia la
           respalda, **pendiente** si no (sin inferir cumplimiento).
        4. ``score`` = fracción de conductas cubiertas sobre el total del nivel.
        5. Decide AVANZAR / MANTENER / RETROCEDER según umbral y racha.

        El resultado es determinista: misma entrada + misma ``version_rubrica``
        ⇒ mismo ``ResultadoRubrica``.
        """
        observaciones = list(observaciones_recientes)

        # 1. Derivar el tramo del rango etario del niño/a.
        fecha_ref = self._resolver_fecha_referencia(observaciones, fecha_referencia)
        edad_meses = self._edad_en_meses(nino.fecha_nacimiento, fecha_ref)
        tramo = self._derivar_tramo(edad_meses)

        # 2. Localizar las conductas observables del tramo × núcleo × nivel.
        conductas = self._conductas_del_nivel(tramo, nucleo, nivel_actual)

        # 3. Mapear la evidencia previa a las conductas (cubierta / pendiente).
        cubiertas, pendientes, evidencia = self._mapear_cobertura(
            conductas, observaciones
        )

        # 4. score = fracción de conductas cubiertas sobre el total del nivel.
        total = len(conductas)
        score = round(len(cubiertas) / total, 2) if total else 0.0

        # 5. Decisión determinista sobre la cobertura y la racha de retroceso.
        decision = self._decidir(score, nucleo, observaciones, nivel_actual)

        return ResultadoRubrica(
            tramo=tramo,
            nucleo=nucleo,
            nivel_actual=nivel_actual,
            decision=decision,
            score=score,
            conductas_observables_cubiertas=cubiertas,
            conductas_observables_pendientes=pendientes,
            evidencia=evidencia,
            version_rubrica=self._version,
        )

    # ------------------------------------------------------------------
    # Nivel general derivado (Requirement 25)
    # ------------------------------------------------------------------
    @staticmethod
    def derivar_nivel_general(
        niveles_por_nucleo: dict[str, int],
    ) -> NivelGeneral:
        """Deriva el **nivel general** como el promedio de los niveles por núcleo.

        El nivel de progresión sigue siendo **por núcleo** (fuente de verdad,
        Requirement 21); este método produce un valor **derivado** y de solo
        lectura para la ficha del niño/a (Requirement 25) sin reemplazar a los
        niveles por núcleo.

        Regla de derivación (Requirement 25.2): promedio aritmético de los
        niveles de progresión de los **distintos núcleos con nivel asignado**. Se
        descartan las entradas sin nivel (``None``) para no contaminar el
        promedio; el resultado se redondea a **2 decimales** (representación
        ``float``, coherente con ``ResultadoRubrica.score``).

        Si ningún núcleo tiene nivel asignado (Requirement 25.4), devuelve
        ``NivelGeneral(disponible=False, nivel_general=None)`` sin lanzar error.

        Es **determinista**: el mismo mapa produce siempre el mismo resultado
        (no usa reloj ni aleatoriedad; el orden de las claves es irrelevante).
        """
        asignados = {
            str(nucleo): int(nivel)
            for nucleo, nivel in niveles_por_nucleo.items()
            if nivel is not None
        }

        if not asignados:
            return NivelGeneral(
                nivel_general=None,
                disponible=False,
                nucleos_considerados=0,
                niveles_por_nucleo={},
            )

        promedio = round(sum(asignados.values()) / len(asignados), 2)
        return NivelGeneral(
            nivel_general=promedio,
            disponible=True,
            nucleos_considerados=len(asignados),
            niveles_por_nucleo=dict(asignados),
        )

    @classmethod
    def nivel_general_desde_resultados(
        cls, resultados: Iterable[ResultadoRubrica]
    ) -> NivelGeneral:
        """Deriva el nivel general a partir de ``ResultadoRubrica`` por núcleo.

        Conveniencia para la ficha del niño/a: toma los resultados de evaluar la
        rúbrica en varios núcleos y deriva el nivel general promediando el
        ``nivel_actual`` de cada uno (Requirement 25.3). Si un mismo núcleo
        aparece más de una vez, prevalece el **último** resultado (orden de
        entrada), de modo que el método sea total y determinista.
        """
        niveles_por_nucleo: dict[str, int] = {}
        for resultado in resultados:
            niveles_por_nucleo[resultado.nucleo] = int(resultado.nivel_actual)
        return cls.derivar_nivel_general(niveles_por_nucleo)

    # ------------------------------------------------------------------
    # Derivación del tramo por edad
    # ------------------------------------------------------------------
    @staticmethod
    def _edad_en_meses(fecha_nacimiento: date, fecha_ref: date) -> int:
        """Calcula la edad en meses completos entre dos fechas (determinista)."""
        meses = (fecha_ref.year - fecha_nacimiento.year) * 12 + (
            fecha_ref.month - fecha_nacimiento.month
        )
        # Si aún no se cumple el día del mes, descontar un mes.
        if fecha_ref.day < fecha_nacimiento.day:
            meses -= 1
        return max(meses, 0)

    def _derivar_tramo(self, edad_meses: int) -> str:
        """Devuelve la clave del tramo cuyo ``rango_etario_meses`` cubre la edad.

        El rango es ``[min, max)`` (mínimo inclusivo, máximo exclusivo). Si la
        edad supera el máximo de todos los tramos, se asigna el tramo de mayor
        edad; si queda por debajo del mínimo, el de menor edad. Así ningún niño/a
        queda sin tramo (comportamiento determinista y total).
        """
        if not self._tramos:
            raise ValueError("La rúbrica no define tramos.")

        tramos_ordenados = sorted(
            self._tramos.items(),
            key=lambda kv: (kv[1].get("rango_etario_meses") or [0, 0])[0],
        )

        for clave, datos in tramos_ordenados:
            rango = datos.get("rango_etario_meses") or [0, 0]
            minimo, maximo = rango[0], rango[1]
            if minimo <= edad_meses < maximo:
                return clave

        # Fuera de todos los rangos: asignar el extremo más cercano.
        primero_clave, primero_datos = tramos_ordenados[0]
        if edad_meses < (primero_datos.get("rango_etario_meses") or [0, 0])[0]:
            return primero_clave
        return tramos_ordenados[-1][0]

    # ------------------------------------------------------------------
    # Localización de conductas observables
    # ------------------------------------------------------------------
    def _conductas_del_nivel(
        self, tramo: str, nucleo: str, nivel_actual: int
    ) -> list[str]:
        """Devuelve las conductas observables del ``tramo × núcleo × nivel``.

        Si el tramo/núcleo/nivel no existe en la rúbrica, devuelve una lista
        vacía (el nivel no tiene conductas definidas → cobertura 0).
        """
        tramo_datos = self._tramos.get(tramo, {})
        nucleos = tramo_datos.get("nucleos", {}) or {}
        nucleo_datos = nucleos.get(nucleo, {})
        niveles = nucleo_datos.get("niveles", []) or []

        for nivel in niveles:
            if int(nivel.get("n", -1)) == int(nivel_actual):
                conductas = nivel.get("conductas_observables", []) or []
                return [str(c) for c in conductas]
        return []

    # ------------------------------------------------------------------
    # "Pasos a seguir" por nivel — alcance futuro (Requirement 29 / 21.1)
    # ------------------------------------------------------------------
    def pasos_a_seguir_del_nivel(
        self, tramo: str, nucleo: str, nivel_actual: int
    ) -> list[str]:
        """Devuelve los **"pasos a seguir"** del ``tramo × núcleo × nivel``.

        **Alcance futuro (Requirement 29, amplía 21.1).** Cada nivel de la rúbrica
        versionada puede incluir, de forma **opcional**, una lista
        ``pasos_a_seguir`` (conductas a observar en próximas actividades) que
        Fundación Integra entregará cuando la rúbrica oficial esté completa.

        El campo es puramente **informativo**: se tolera y preserva, pero **no
        altera la decisión determinista** de :meth:`evaluar` (Requirement 29.3,
        6.2). Cuando el nivel no define ``pasos_a_seguir`` (o la rúbrica aún no los
        incorpora), se devuelve una **lista vacía** sin producir error
        (Requirement 29.2) — por eso agregar los pasos a futuro es cuestión de
        **datos versionados, sin cambios de código** (Requirement 29.1, 21.1).
        """
        tramo_datos = self._tramos.get(tramo, {})
        nucleos = tramo_datos.get("nucleos", {}) or {}
        nucleo_datos = nucleos.get(nucleo, {})
        niveles = nucleo_datos.get("niveles", []) or []

        for nivel in niveles:
            if int(nivel.get("n", -1)) == int(nivel_actual):
                pasos = nivel.get("pasos_a_seguir", []) or []
                return [str(p) for p in pasos]
        return []

    # ------------------------------------------------------------------
    # Mapeo de evidencia a cobertura
    # ------------------------------------------------------------------
    def _mapear_cobertura(
        self, conductas: list[str], observaciones: list[Observacion]
    ) -> tuple[list[str], list[str], list[str]]:
        """Mapea la evidencia previa a cada conducta observable.

        Una conducta se marca **cubierta** solo si alguna observación la respalda
        (coincidencia de ``id_manifestacion`` o solape suficiente de tokens entre
        la conducta y la ``nota_breve``). Una conducta **sin evidencia cuenta como
        pendiente** — nunca se infiere cumplimiento (Requirement 21.6).

        Devuelve ``(cubiertas, pendientes, evidencia)`` donde ``evidencia`` lista
        los ``id_observacion`` que respaldaron al menos una conducta, en orden de
        aparición y sin duplicados.
        """
        # Pre-tokenizar la evidencia una sola vez (determinista). Los ids de
        # manifestación se normalizan (minúsculas, sin tildes) para compararlos
        # con los tokens de la conducta de forma estable.
        evidencia_tokens: list[tuple[Observacion, set[str], set[str]]] = []
        for obs in observaciones:
            tokens = _tokenizar(obs.nota_breve or "")
            manifest = {_normalizar(str(m)) for m in (obs.manifestaciones or [])}
            evidencia_tokens.append((obs, tokens, manifest))

        cubiertas: list[str] = []
        pendientes: list[str] = []
        ids_evidencia: list[str] = []
        vistos: set[str] = set()

        for conducta in conductas:
            tokens_conducta = _tokenizar(conducta)
            manifest_conducta = {
                t for t in tokens_conducta if t.startswith("m")
            }
            manifest_conducta.update(
                _normalizar(ident)
                for ident in _MANIFESTACION_ID.findall(conducta)
            )
            respaldada = False

            for obs, tokens_obs, manifest_obs in evidencia_tokens:
                if self._respalda(
                    tokens_conducta, manifest_conducta, tokens_obs, manifest_obs
                ):
                    respaldada = True
                    if obs.id_observacion not in vistos:
                        vistos.add(obs.id_observacion)
                        ids_evidencia.append(obs.id_observacion)

            if respaldada:
                cubiertas.append(conducta)
            else:
                pendientes.append(conducta)

        return cubiertas, pendientes, ids_evidencia

    @staticmethod
    def _respalda(
        tokens_conducta: set[str],
        manifest_conducta: set[str],
        tokens_obs: set[str],
        manifest_obs: set[str],
    ) -> bool:
        """Determina si una observación respalda una conducta observable.

        Dos vías de respaldo (determinista):
        - **Manifestación explícita:** la observación referencia un id de
          manifestación citado en la conducta.
        - **Solape de texto:** la ``nota_breve`` comparte al menos
          ``_MIN_TOKENS_COINCIDENTES`` tokens significativos con la conducta.
        """
        if manifest_obs and manifest_conducta and (manifest_obs & manifest_conducta):
            return True
        if not tokens_conducta or not tokens_obs:
            return False
        comunes = tokens_conducta & tokens_obs
        return len(comunes) >= _MIN_TOKENS_COINCIDENTES

    # ------------------------------------------------------------------
    # Decisión determinista
    # ------------------------------------------------------------------
    def _decidir(
        self,
        score: float,
        nucleo: str,
        observaciones: list[Observacion],
        nivel_actual: int,
    ) -> DecisionNivel:
        """Aplica las ramas de decisión sobre la cobertura y la racha.

        Orden de precedencia:
        1. **AVANZAR** si ``score`` ≥ ``cobertura_avanzar`` y el núcleo es
           requerido (``nucleos_requeridos``).
        2. **RETROCEDER** si hay una racha ≥ ``racha_retroceso`` de observaciones
           consecutivas con ``nivel_estimado`` por debajo del ``nivel_actual``.
        3. **MANTENER** en cualquier otro caso (cobertura parcial).
        """
        cobertura_avanzar = float(
            self._umbrales.get("cobertura_avanzar", _COBERTURA_AVANZAR_DEFAULT)
        )
        nucleos_requeridos = self._umbrales.get("nucleos_requeridos") or [
            NUCLEO_POR_DEFECTO
        ]
        racha_min = int(
            self._umbrales.get("racha_retroceso", _RACHA_RETROCESO_DEFAULT)
        )

        if (
            nivel_actual < 9
            and score >= cobertura_avanzar
            and nucleo in nucleos_requeridos
        ):
            return DecisionNivel.AVANZAR

        if self._tiene_racha_de_retroceso(observaciones, nivel_actual, racha_min):
            return DecisionNivel.RETROCEDER

        return DecisionNivel.MANTENER

    @staticmethod
    def _tiene_racha_de_retroceso(
        observaciones: list[Observacion], nivel_actual: int, racha_min: int
    ) -> bool:
        """¿Hay ≥ ``racha_min`` observaciones consecutivas bajo el nivel actual?

        Recorre las observaciones **en orden cronológico** (por
        ``fecha_observacion`` y, a igualdad, por ``id_observacion`` para un orden
        total estable) y busca la racha máxima de ``nivel_estimado`` estrictamente
        menor que ``nivel_actual``. Las observaciones sin ``nivel_estimado``
        (``None``) no cuentan como "por debajo" y cortan la racha.
        """
        if racha_min <= 0:
            return False

        ordenadas = sorted(
            observaciones,
            key=lambda o: (o.fecha_observacion, o.id_observacion),
        )

        racha = 0
        for obs in ordenadas:
            nivel = obs.nivel_estimado
            if nivel is not None and nivel < nivel_actual:
                racha += 1
                if racha >= racha_min:
                    return True
            else:
                racha = 0
        return False

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _resolver_fecha_referencia(
        observaciones: list[Observacion], fecha_referencia: date | None
    ) -> date:
        """Resuelve la fecha de referencia para calcular la edad del niño/a.

        Prioriza la ``fecha_referencia`` explícita (determinista). Si no se
        provee, usa la observación más reciente; y si no hay observaciones, cae
        en una fecha fija y neutra (``date.max``-independiente) derivada de la
        propia entrada para no depender del reloj del sistema.
        """
        if fecha_referencia is not None:
            return fecha_referencia
        if observaciones:
            return max(o.fecha_observacion for o in observaciones)
        # Sin señal temporal: usar la fecha de hoy evitaría el determinismo, por
        # lo que se usa una referencia fija y documentada.
        return date(2026, 10, 13)


__all__ = ["RubricaDecision", "NUCLEO_POR_DEFECTO"]
