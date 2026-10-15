"""``DirectorReportService`` del Módulo G (Modelo 4 — reporte de dirección).

Agrega, **para un jardín y un período**, las métricas de supervisión que la
directora necesita y añade un **resumen ejecutivo narrativo** redactado por el
``LlmProvider`` a partir *únicamente* de esas métricas agregadas.

Principio central (Requirement 7.8): **la base de datos relacional calcula las
métricas, el LLM solo las narra.** Todas las cifras del reporte provienen de las
consultas agregadas de ``RelationalRepo`` (tarea 3.4); el ``LlmProvider`` nunca
infiere ni altera un número. Si el LLM falla, el reporte se entrega igual con
sus métricas y una marca de "resumen no disponible" (Requirement 7.6).

Flujo (ver design.md §DirectorReportService):

``RelationalRepo`` (7 consultas agregadas del período) → métricas +
KPI determinista de tiempo ahorrado → ``LlmProvider`` (resumen ejecutivo) →
reporte persistido/entregado.

Principio de aislamiento (Requirement 13): el servicio depende **solo de los
puertos** ``RelationalRepo`` y ``LlmProvider`` inyectados por constructor (DIP +
ISP). No importa ninguna implementación concreta de módulos hermanos; en los
tests se usan fakes locales.

Garantías cubiertas (criterios 7.1–7.8):
- **7.1** — Conteo de niños/as que subieron/mantuvieron/bajaron por sala, cada
  niño/a en **exactamente una** categoría (lo garantiza
  ``RelationalRepo.conteos_nivel_por_sala``).
- **7.2** — Rango de fechas inválido (``inicio > fin`` o fecha mal formada) →
  :class:`ReporteRangoInvalidoError` (→ HTTP 422) **sin** tocar datos.
- **7.3** — Distribución por sala y por dominio, conteos de observaciones y
  bitácoras (total y por educadora), alertas de retroceso e inactividad (14 d).
- **7.4** — KPI determinista de tiempo de documentación ahorrado, derivado del
  volumen de observaciones y bitácoras del período.
- **7.5** — Resumen ejecutivo narrativo en español vía ``LlmProvider`` a partir
  **solo** de las métricas agregadas.
- **7.6** — Si el LLM falla/excede el plazo, el reporte se entrega con las
  métricas y ``resumen_disponible=False`` (resumen no disponible), sin descartar
  las métricas ya calculadas.
- **7.7** — Jardín/sala sin datos ⇒ conteos y distribuciones en cero, sin error.
- **7.8** — Todas las métricas vienen de ``RelationalRepo`` (SQL), no del LLM.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturoTimeout
from datetime import date
from typing import Any

from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import ReporteDireccion as ReporteDireccionORM

# Plazo máximo por defecto para el resumen ejecutivo del LLM (Requirement 7.6).
# El resumen es complementario; si tarda demasiado se entrega el reporte sin él.
LLM_TIMEOUT_SEGUNDOS = 30.0

# Mensaje estándar cuando el resumen narrativo no está disponible (7.6).
RESUMEN_NO_DISPONIBLE = (
    "El resumen ejecutivo generado por IA no está disponible; el reporte se "
    "entrega con sus métricas agregadas calculadas."
)

# --- KPI de tiempo de documentación ahorrado (Requirement 7.4) -------------
# Minutos de redacción manual que jAImes ahorra por cada artefacto generado.
# El KPI es **determinista**: depende solo del volumen de observaciones y
# bitácoras del período (nunca del LLM). Los valores son conservadores y
# consistentes con el objetivo del proyecto (~4 h/semana → ~0 h): documentar y
# estructurar una observación a mano toma del orden de minutos, y redactar una
# bitácora quincenal, bastante más.
MINUTOS_AHORRADOS_POR_OBSERVACION = 10
MINUTOS_AHORRADOS_POR_BITACORA = 45


class DirectorReportError(Exception):
    """Error de dominio del servicio de reporte (mensajes en español)."""


class ReporteRangoInvalidoError(DirectorReportError):
    """Rango de fechas inválido (traducible a HTTP 422).

    Se lanza cuando la fecha de inicio es posterior a la de fin, o cuando alguna
    de las fechas no es válida (Requirement 7.2). No produce ningún efecto de
    escritura: el estado de datos se preserva sin cambios.
    """


class ResultadoReporte:
    """Resultado de ``generar`` entregado a la capa de API / tests.

    Reúne el identificador y el período del reporte, el **diccionario de
    métricas agregadas** (todas provenientes de ``RelationalRepo``), el KPI de
    tiempo ahorrado, el resumen ejecutivo y un indicador de si el resumen
    narrativo pudo generarse (Requirement 7.6).
    """

    __slots__ = (
        "id_reporte",
        "id_jardin",
        "periodo",
        "metricas",
        "resumen_ejecutivo",
        "resumen_disponible",
        "fecha",
    )

    def __init__(
        self,
        *,
        id_reporte: str,
        id_jardin: str,
        periodo: str,
        metricas: dict[str, Any],
        resumen_ejecutivo: str,
        resumen_disponible: bool,
        fecha: date,
    ) -> None:
        self.id_reporte = id_reporte
        self.id_jardin = id_jardin
        self.periodo = periodo
        self.metricas = metricas
        self.resumen_ejecutivo = resumen_ejecutivo
        self.resumen_disponible = resumen_disponible
        self.fecha = fecha


class DirectorReportService:
    """Genera el reporte de dirección (SQL agrega, el LLM narra).

    Depende únicamente de los puertos ``RelationalRepo`` y ``LlmProvider``
    inyectados por constructor (DIP + ISP). El plazo del LLM es inyectable para
    poder verificar en los tests la degradación del resumen (Requirement 7.6).
    """

    def __init__(
        self,
        repo: RelationalRepo,
        llm: LlmProvider,
        *,
        timeout_segundos: float = LLM_TIMEOUT_SEGUNDOS,
        persistir: bool = True,
    ) -> None:
        self._repo = repo
        self._llm = llm
        self._timeout = timeout_segundos
        # Si ``persistir`` es True, el reporte se guarda vía ``RelationalRepo``
        # para quedar disponible luego; el flujo no depende de ello.
        self._persistir = persistir

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def generar(
        self,
        id_jardin: str,
        fecha_inicio: date,
        fecha_fin: date,
        *,
        fecha_reporte: date | None = None,
    ) -> ResultadoReporte:
        """Genera el reporte de dirección de un jardín para un período.

        Args:
            id_jardin: jardín cuyo reporte se genera.
            fecha_inicio: inicio del período (inclusive).
            fecha_fin: fin del período (inclusive); debe ser ``>= fecha_inicio``.
            fecha_reporte: fecha a estampar en el reporte (por defecto, hoy).

        Returns:
            El :class:`ResultadoReporte` con las métricas agregadas, el KPI y el
            resumen ejecutivo (o la marca de resumen no disponible).

        Raises:
            ReporteRangoInvalidoError: si ``fecha_inicio > fecha_fin`` o alguna
                fecha es inválida (Requirement 7.2 → HTTP 422). No se escribe
                nada: el estado de datos se preserva.
        """
        # --- 1) Validar el rango de fechas ANTES de tocar nada (7.2) --------
        self._validar_rango(fecha_inicio, fecha_fin)

        # --- 2) Agregar todas las métricas desde SQL (7.1, 7.3, 7.8) --------
        # Cada cifra proviene de ``RelationalRepo``; el LLM nunca las infiere.
        conteos_por_sala = self._repo.conteos_nivel_por_sala(
            id_jardin, fecha_inicio, fecha_fin
        )
        distribucion_por_sala = self._repo.distribucion_niveles_por_sala(
            id_jardin, fecha_inicio, fecha_fin
        )
        distribucion_por_dominio = self._repo.distribucion_niveles_por_dominio(
            id_jardin, fecha_inicio, fecha_fin
        )
        observaciones = self._repo.contar_observaciones_periodo(
            id_jardin, fecha_inicio, fecha_fin
        )
        bitacoras = self._repo.contar_bitacoras_periodo(
            id_jardin, fecha_inicio, fecha_fin
        )
        alertas_retroceso = self._repo.alertas_retroceso(
            id_jardin, fecha_inicio, fecha_fin
        )
        alertas_inactividad = self._repo.alertas_inactividad(id_jardin, fecha_fin)

        # --- 3) KPI determinista de tiempo ahorrado (7.4) -------------------
        kpi_tiempo = self._calcular_kpi_tiempo(observaciones, bitacoras)

        # Las agregaciones ya devuelven ceros/estructuras vacías cuando no hay
        # datos, de modo que un jardín o sala sin actividad produce un reporte
        # válido con conteos en cero y sin error (Requirement 7.7).
        metricas: dict[str, Any] = {
            "conteos_nivel_por_sala": conteos_por_sala,
            "distribucion_niveles_por_sala": distribucion_por_sala,
            "distribucion_niveles_por_dominio": distribucion_por_dominio,
            "observaciones": observaciones,
            "bitacoras": bitacoras,
            "alertas": {
                "retroceso": list(alertas_retroceso),
                "inactividad": list(alertas_inactividad),
            },
            "kpi_tiempo_ahorrado": kpi_tiempo,
        }

        # --- 4) Resumen ejecutivo narrativo vía LLM (7.5), tolerante a fallo -
        periodo = f"{fecha_inicio.isoformat()}/{fecha_fin.isoformat()}"
        resumen, disponible = self._resumen_ejecutivo(id_jardin, periodo, metricas)

        # --- 5) Persistir el reporte (opcional; no condiciona el resultado) -
        id_reporte = uuid.uuid4().hex
        fecha_final = fecha_reporte or date.today()
        if self._persistir:
            self._repo.add(
                ReporteDireccionORM(
                    id_reporte=id_reporte,
                    id_jardin=id_jardin,
                    periodo=periodo,
                    metricas=metricas,
                    resumen_ejecutivo=resumen,
                    fecha=fecha_final,
                )
            )

        return ResultadoReporte(
            id_reporte=id_reporte,
            id_jardin=id_jardin,
            periodo=periodo,
            metricas=metricas,
            resumen_ejecutivo=resumen,
            resumen_disponible=disponible,
            fecha=fecha_final,
        )

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    @staticmethod
    def _validar_rango(fecha_inicio: Any, fecha_fin: Any) -> None:
        """Valida el rango ``[inicio, fin]`` con ambos extremos inclusivos (7.2).

        Rechaza fechas mal formadas (que no sean ``date``) y el rango invertido
        (``inicio > fin``) con un mensaje en español, sin producir ningún efecto
        de escritura.
        """
        if not isinstance(fecha_inicio, date) or not isinstance(fecha_fin, date):
            raise ReporteRangoInvalidoError(
                "El rango de fechas es inválido: las fechas de inicio y fin "
                "deben tener un formato de fecha válido."
            )
        if fecha_inicio > fecha_fin:
            raise ReporteRangoInvalidoError(
                "El rango de fechas es inválido: la fecha de inicio "
                f"({fecha_inicio.isoformat()}) no puede ser posterior a la "
                f"fecha de fin ({fecha_fin.isoformat()})."
            )

    @staticmethod
    def _calcular_kpi_tiempo(
        observaciones: dict[str, Any], bitacoras: dict[str, Any]
    ) -> dict[str, Any]:
        """KPI determinista del tiempo de documentación ahorrado (7.4).

        Se deriva **solo** del volumen de observaciones y bitácoras del período
        (nunca del LLM): cada observación y cada bitácora representan minutos de
        redacción manual que jAImes evita. El resultado es reproducible: las
        mismas cifras de entrada producen siempre el mismo KPI.
        """
        total_observaciones = int(observaciones.get("total", 0) or 0)
        total_bitacoras = int(bitacoras.get("total", 0) or 0)
        minutos = (
            total_observaciones * MINUTOS_AHORRADOS_POR_OBSERVACION
            + total_bitacoras * MINUTOS_AHORRADOS_POR_BITACORA
        )
        return {
            "observaciones": total_observaciones,
            "bitacoras": total_bitacoras,
            "minutos_por_observacion": MINUTOS_AHORRADOS_POR_OBSERVACION,
            "minutos_por_bitacora": MINUTOS_AHORRADOS_POR_BITACORA,
            "minutos_ahorrados": minutos,
            "horas_ahorradas": round(minutos / 60.0, 2),
        }

    def _resumen_ejecutivo(
        self, id_jardin: str, periodo: str, metricas: dict[str, Any]
    ) -> tuple[str, bool]:
        """Pide al LLM el resumen ejecutivo bajo el plazo máximo (7.5, 7.6).

        Devuelve ``(resumen, disponible)``. Si el LLM falla, excede el plazo o
        devuelve texto vacío, entrega ``(RESUMEN_NO_DISPONIBLE, False)`` sin
        descartar las métricas ya calculadas (Requirement 7.6).
        """
        prompt = self._construir_prompt(id_jardin, periodo)
        context = self._construir_contexto(metricas)

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                futuro = executor.submit(self._llm.generate, prompt, context)
                try:
                    resumen = futuro.result(timeout=self._timeout)
                except FuturoTimeout:
                    # El LLM excedió el plazo (Requirement 7.6): el reporte se
                    # entrega igual con sus métricas agregadas.
                    futuro.cancel()
                    return RESUMEN_NO_DISPONIBLE, False
        except LlmError:
            # El proveedor falló (Requirement 7.6): métricas conservadas.
            return RESUMEN_NO_DISPONIBLE, False

        texto = (resumen or "").strip()
        if not texto:
            return RESUMEN_NO_DISPONIBLE, False
        return texto, True

    @staticmethod
    def _construir_prompt(id_jardin: str, periodo: str) -> str:
        """Instrucción para el LLM: narrar SOLO las métricas entregadas (7.5)."""
        return (
            "Redacta en español (Chile), con registro ejecutivo y sobrio, un "
            f"resumen de supervisión para la dirección del jardín {id_jardin} "
            f"correspondiente al período {periodo}. Básate exclusivamente en las "
            "métricas agregadas entregadas en el contexto: no inventes cifras, "
            "no agregues datos que no estén presentes y no modifiques los "
            "números. Destaca el movimiento de niveles por sala, la actividad de "
            "documentación, el tiempo ahorrado y las alertas que requieran "
            "atención."
        )

    @staticmethod
    def _construir_contexto(metricas: dict[str, Any]) -> str:
        """Serializa las métricas agregadas como contexto fundamentante (7.5, 7.8).

        El LLM recibe únicamente las cifras ya calculadas por ``RelationalRepo``;
        no tiene acceso a los datos crudos ni puede inferir métricas nuevas.
        """
        kpi = metricas.get("kpi_tiempo_ahorrado", {})
        alertas = metricas.get("alertas", {})
        lineas: list[str] = []

        lineas.append("## Movimiento de niveles por sala (subieron/mantuvieron/bajaron)")
        conteos = metricas.get("conteos_nivel_por_sala", {})
        if conteos:
            for sala, cats in conteos.items():
                lineas.append(
                    f"- {sala}: subieron {cats.get('subieron', 0)}, "
                    f"mantuvieron {cats.get('mantuvieron', 0)}, "
                    f"bajaron {cats.get('bajaron', 0)}."
                )
        else:
            lineas.append("- Sin datos de movimiento en el período.")

        lineas.append("")
        lineas.append("## Distribución de niveles por sala")
        dist_sala = metricas.get("distribucion_niveles_por_sala", {})
        if dist_sala:
            for sala, niveles in dist_sala.items():
                detalle = ", ".join(
                    f"nivel {nivel}: {conteo}" for nivel, conteo in sorted(niveles.items())
                )
                lineas.append(f"- {sala}: {detalle or 'sin observaciones con nivel'}.")
        else:
            lineas.append("- Sin observaciones con nivel en el período.")

        lineas.append("")
        lineas.append("## Distribución de niveles por dominio")
        dist_dom = metricas.get("distribucion_niveles_por_dominio", {})
        if dist_dom:
            for dominio, niveles in dist_dom.items():
                detalle = ", ".join(
                    f"nivel {nivel}: {conteo}" for nivel, conteo in sorted(niveles.items())
                )
                lineas.append(f"- {dominio}: {detalle or 'sin observaciones con nivel'}.")
        else:
            lineas.append("- Sin observaciones con nivel en el período.")

        observaciones = metricas.get("observaciones", {})
        bitacoras = metricas.get("bitacoras", {})
        lineas.append("")
        lineas.append("## Actividad de documentación")
        lineas.append(
            f"- Observaciones: {observaciones.get('total', 0)} en total; "
            f"por educadora: {observaciones.get('por_educadora', {}) or 'ninguna'}."
        )
        lineas.append(
            f"- Bitácoras: {bitacoras.get('total', 0)} en total; "
            f"por educadora: {bitacoras.get('por_educadora', {}) or 'ninguna'}."
        )

        lineas.append("")
        lineas.append("## KPI de tiempo de documentación ahorrado")
        lineas.append(
            f"- {kpi.get('minutos_ahorrados', 0)} minutos "
            f"(~{kpi.get('horas_ahorradas', 0)} horas) ahorrados en el período."
        )

        lineas.append("")
        lineas.append("## Alertas")
        retroceso = alertas.get("retroceso", []) or []
        inactividad = alertas.get("inactividad", []) or []
        lineas.append(
            "- Retroceso: "
            + (", ".join(retroceso) if retroceso else "sin alertas.")
        )
        lineas.append(
            "- Inactividad (14 días): "
            + (", ".join(inactividad) if inactividad else "sin alertas.")
        )

        return "\n".join(lineas)


__all__ = [
    "DirectorReportService",
    "ResultadoReporte",
    "DirectorReportError",
    "ReporteRangoInvalidoError",
    "LLM_TIMEOUT_SEGUNDOS",
    "RESUMEN_NO_DISPONIBLE",
    "MINUTOS_AHORRADOS_POR_OBSERVACION",
    "MINUTOS_AHORRADOS_POR_BITACORA",
]
