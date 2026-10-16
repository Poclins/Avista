"""``BitacoraService`` del Módulo F (bitácora quincenal, Modelo 2: RAG + LLM).

Orquesta, **dentro de la frontera del Módulo F**, la generación de la bitácora
quincenal de un niño/a a partir de la evidencia real recuperada (RAG) y la
rúbrica vigente, redactada por el ``LlmProvider``:

``RelationalRepo`` (observaciones del período) + ``VectorRepo`` (hasta 20
similares de la ventana) → contexto RAG + rúbrica vigente → ``LlmProvider``
(redacción con trazabilidad) → ``RelationalRepo`` (persistencia en "borrador").

Principio de aislamiento (Requirement 13): este servicio depende **solo de
interfaces/puertos** (``RelationalRepo``, ``VectorRepo``, ``LlmProvider`` y el
protocolo mínimo ``EmbeddingPort`` definido aquí para embeber la consulta RAG).
No importa ninguna implementación concreta de módulos hermanos (ni el
``EmbeddingService`` real del Módulo C, ni el LLM/vector real): todas las
dependencias se inyectan por constructor y en los tests se usan fakes locales.

Alcance de esta pieza (tarea 7.6): **solo** la generación de la bitácora
(Requirements 5.1–5.6). La edición/aprobación (Requirements 5.7–5.9) la añade
la tarea 7.7 extendiendo esta clase sin reescribir lo existente.

Garantías cubiertas (criterios 5.1–5.6):
- **5.1** — Recupera observaciones del ``id_nino`` dentro del período vía
  ``RelationalRepo`` y las complementa con hasta 20 observaciones similares del
  **mismo** ``id_nino`` restringidas a la ventana, vía ``VectorRepo.search``.
- **5.2** — Si no hay ninguna observación del niño/a en el período, aborta sin
  crear bitácora lanzando :class:`BitacoraSinEvidenciaError` (→ HTTP 422).
- **5.3** — Invoca el LLM con la evidencia recuperada y la rúbrica vigente como
  contexto.
- **5.4** — Si el LLM falla o excede 60 s, aborta sin crear bitácora en borrador
  lanzando :class:`BitacoraLlmError` (→ HTTP 503). El plazo máximo es
  inyectable para poder verificarlo en los tests.
- **5.5** — El prompt exige que cada afirmación evaluativa cite al menos una
  observación/manifestación por su ``id_observacion``/id de manifestación; la
  lista de ids disponibles se pasa en el contexto.
- **5.6** — Persiste la bitácora vía ``RelationalRepo.add`` en estado
  ``EstadoBitacora.borrador``.
"""

from __future__ import annotations

import concurrent.futures
import re
import uuid
from datetime import date
from typing import Protocol, runtime_checkable

from app.core.nombres_sinteticos import nombre_completo
from app.domain.models import EstadoBitacora
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Bitacora as BitacoraORM,
    Nino as NinoORM,
    Observacion as ObservacionORM,
    RubricaVersion as RubricaVersionORM,
)
from app.repositories.vector.base import VectorRepo

# Plazo máximo por defecto para la invocación al LLM (Requirement 5.4): 60 s.
PLAZO_LLM_SEGUNDOS = 60.0

# Número máximo de observaciones similares a complementar vía RAG
# (Requirement 5.1): hasta las 20 más similares del mismo niño/a en la ventana.
MAX_SIMILARES = 20


# ---------------------------------------------------------------------------
# Excepciones tipadas (la Capa G las traduce a respuestas HTTP en español)
# ---------------------------------------------------------------------------
class BitacoraSinEvidenciaError(ValueError):
    """No hay evidencia suficiente en el período (traducible a HTTP 422).

    Se lanza cuando no existe ninguna observación del ``id_nino`` dentro del
    período solicitado (Requirement 5.2). El mensaje va en español y la capa de
    API (Módulo G) lo traduce a una respuesta 422 sin crear ninguna bitácora.
    """


class BitacoraLlmError(RuntimeError):
    """El LLM falló o excedió su plazo máximo (traducible a HTTP 503).

    Se lanza cuando la invocación al ``LlmProvider`` falla o supera el plazo de
    60 s (Requirement 5.4). El mensaje va en español y la capa de API lo traduce
    a una respuesta 503; **no** se persiste ninguna bitácora en borrador.
    """


class BitacoraNoEncontradaError(LookupError):
    """La bitácora solicitada no existe (traducible a HTTP 404).

    Se lanza al intentar editar o aprobar una bitácora cuyo ``id_bitacora`` no
    está registrado (Requirements 5.7, 5.8). El mensaje va en español y la capa
    de API (Módulo G) lo traduce a una respuesta 404 sin alterar ningún dato.
    """


class BitacoraConflictoError(RuntimeError):
    """La operación entra en conflicto con el estado actual (traducible a 409).

    Se lanza al intentar editar una bitácora que ya está en estado "aprobada"
    (Requirement 5.9): una bitácora aprobada es inmutable. El mensaje va en
    español y la capa de API lo traduce a una respuesta 409 sin modificar el
    texto ni el estado de la bitácora.
    """


# ---------------------------------------------------------------------------
# Puerto mínimo de embeddings para embeber la consulta RAG
# ---------------------------------------------------------------------------
@runtime_checkable
class EmbeddingPort(Protocol):
    """Puerto mínimo para embeber el texto de consulta de la búsqueda RAG.

    El proveedor concreto de embeddings pertenece al Módulo C; para no acoplar
    el Módulo F a esa implementación, aquí se declara solo la capacidad que la
    bitácora necesita: convertir un texto de consulta en un vector denso. El
    contenedor de DI inyecta la implementación real; los tests inyectan un fake.
    """

    def embed(self, text: str) -> list[float]:
        """Devuelve el embedding del texto de consulta dado."""
        ...


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------
class BitacoraService:
    """Genera bitácoras quincenales con RAG + LLM (Modelo 2).

    Depende únicamente de puertos inyectados por constructor (DIP + ISP). Deja
    espacio para que la tarea 7.7 añada edición/aprobación (Requirements
    5.7–5.9) sin reescribir la generación.
    """

    def __init__(
        self,
        repo: RelationalRepo,
        vector: VectorRepo,
        llm: LlmProvider,
        embeddings: EmbeddingPort,
        *,
        plazo_llm_segundos: float = PLAZO_LLM_SEGUNDOS,
    ) -> None:
        self._repo = repo
        self._vector = vector
        self._llm = llm
        self._embeddings = embeddings
        # Plazo máximo inyectable para verificar el corte de 60 s en los tests.
        self._plazo_llm_segundos = plazo_llm_segundos

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def generar(
        self,
        id_nino: str,
        id_educadora: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> BitacoraORM:
        """Genera y persiste la bitácora quincenal de un niño/a.

        Args:
            id_nino: niño/a cuya bitácora se genera.
            id_educadora: educadora que solicita la generación.
            fecha_inicio: inicio del período quincenal (inclusive).
            fecha_fin: fin del período quincenal (inclusive, ventana de 14 días).

        Returns:
            La :class:`Bitacora` persistida en estado ``borrador``.

        Raises:
            BitacoraSinEvidenciaError: si no hay observaciones del niño/a en el
                período (Requirement 5.2 → HTTP 422).
            BitacoraLlmError: si el LLM falla o excede el plazo de 60 s
                (Requirement 5.4 → HTTP 503); no se persiste ninguna bitácora.
        """
        # --- 1) Observaciones del período vía RelationalRepo (5.1) ----------
        observaciones = self._observaciones_del_periodo(
            id_nino, fecha_inicio, fecha_fin
        )

        # --- 2) Abortar si no hay evidencia (5.2 → 422) ---------------------
        # El criterio exige evidencia *dentro del período*; la búsqueda
        # semántica solo complementa esa evidencia, nunca la sustituye.
        if not observaciones:
            raise BitacoraSinEvidenciaError(
                "No hay evidencia suficiente en el período solicitado para "
                "generar la bitácora: no se registraron observaciones del "
                "niño/a entre las fechas indicadas."
            )

        # --- 3) Complementar con hasta 20 similares del mismo niño/a (5.1) --
        similares = self._similares_en_ventana(
            id_nino, observaciones, fecha_inicio, fecha_fin
        )

        # --- 4) Construir el contexto RAG (evidencia + rúbrica vigente) -----
        rubrica = self._repo.rubrica_vigente()
        contexto = self._construir_contexto(observaciones, similares, rubrica)
        prompt = self._construir_prompt(id_nino, fecha_inicio, fecha_fin)

        # --- 5) Invocar el LLM con plazo máximo verificable (5.3, 5.4) ------
        texto_generado = self._invocar_llm(prompt, contexto)
        texto_generado = self._numerar_referencias_observaciones(
            texto_generado, observaciones, similares
        )
        try:
            nino = self._repo.get(NinoORM, id_nino)
        except NotImplementedError:
            nino = None
        if nino is not None:
            etiqueta_nino = nombre_completo(
                nino.id_nino,
                getattr(nino, "nombre", None),
                getattr(nino, "apellido_paterno", None),
                getattr(nino, "apellido_materno", None),
            )
            texto_generado = texto_generado.replace(id_nino, etiqueta_nino)

        # --- 6) Persistir en estado "borrador" (5.6) ------------------------
        bitacora = BitacoraORM(
            id_bitacora=uuid.uuid4().hex,
            id_nino=id_nino,
            id_educadora=id_educadora,
            periodo=f"{fecha_inicio.isoformat()}/{fecha_fin.isoformat()}",
            texto_generado=texto_generado,
            estado=EstadoBitacora.borrador,
            fecha=date.today(),
        )
        self._repo.add(bitacora)
        return bitacora

    def editar(self, id_bitacora: str, nuevo_texto: str) -> BitacoraORM:
        """Edita el texto de una bitácora mientras está en "borrador" (5.7).

        La educadora puede corregir el texto generado solo mientras la bitácora
        permanece en estado ``borrador``; el cambio se persiste vía
        ``RelationalRepo.add`` (SQLAlchemy fusiona por clave primaria).

        Args:
            id_bitacora: identificador de la bitácora a editar.
            nuevo_texto: nuevo contenido de ``texto_generado``.

        Returns:
            La :class:`Bitacora` actualizada y persistida (sigue en "borrador").

        Raises:
            BitacoraNoEncontradaError: si la bitácora no existe (→ HTTP 404).
            BitacoraConflictoError: si la bitácora ya está "aprobada"
                (Requirement 5.9 → HTTP 409); el texto no se modifica.
        """
        bitacora = self._obtener_bitacora(id_bitacora)

        # Una bitácora aprobada es inmutable: se rechaza sin tocar el texto (5.9).
        if bitacora.estado is EstadoBitacora.aprobada:
            raise BitacoraConflictoError(
                "No es posible editar la bitácora: ya está aprobada y no admite "
                "modificaciones."
            )

        bitacora.texto_generado = nuevo_texto
        # SQLAlchemy fusiona por clave primaria en ``add``: persiste la edición.
        return self._repo.add(bitacora)  # type: ignore[return-value]

    def aprobar(self, id_bitacora: str) -> BitacoraORM:
        """Aprueba una bitácora, cambiando su estado a "aprobada" (5.8).

        La aprobación es idempotente respecto al estado final: una bitácora ya
        "aprobada" permanece "aprobada" (nunca vuelve a "borrador"). El cambio se
        persiste vía ``RelationalRepo.add`` (fusión por clave primaria).

        Args:
            id_bitacora: identificador de la bitácora a aprobar.

        Returns:
            La :class:`Bitacora` en estado ``aprobada`` y persistida.

        Raises:
            BitacoraNoEncontradaError: si la bitácora no existe (→ HTTP 404).
        """
        bitacora = self._obtener_bitacora(id_bitacora)

        # Idempotente: si ya está aprobada, no hay cambio de estado que persistir.
        if bitacora.estado is EstadoBitacora.aprobada:
            return bitacora

        bitacora.estado = EstadoBitacora.aprobada
        return self._repo.add(bitacora)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _obtener_bitacora(self, id_bitacora: str) -> BitacoraORM:
        """Recupera una bitácora por su PK o lanza el error 404 tipado (5.7/5.8)."""
        bitacora = self._repo.get(BitacoraORM, id_bitacora)
        if bitacora is None:
            raise BitacoraNoEncontradaError(
                f"No se encontró la bitácora solicitada (id_bitacora="
                f"{id_bitacora!r})."
            )
        return bitacora  # type: ignore[return-value]

    def _observaciones_del_periodo(
        self, id_nino: str, fecha_inicio: date, fecha_fin: date
    ) -> list[ObservacionORM]:
        """Observaciones del niño/a cuya fecha cae en ``[inicio, fin]`` (5.1)."""
        todas = self._repo.observaciones_de_nino(id_nino)
        return [
            obs
            for obs in todas
            if fecha_inicio <= obs.fecha_observacion <= fecha_fin
        ]

    def _similares_en_ventana(
        self,
        id_nino: str,
        observaciones: list[ObservacionORM],
        fecha_inicio: date,
        fecha_fin: date,
    ) -> list[dict]:
        """Hasta 20 observaciones similares del mismo niño/a en la ventana (5.1).

        Construye el embedding de consulta a partir del texto de las
        observaciones del período y busca en ``VectorRepo`` restringiendo por
        ``id_nino`` y por la ventana del período. Devuelve los documentos
        recuperados (metadatos de contrato) **excluyendo** las observaciones ya
        presentes en el período para no duplicar evidencia.
        """
        consulta = " ".join(
            (obs.nota_breve or "").strip()
            for obs in observaciones
            if (obs.nota_breve or "").strip()
        ).strip()
        # Sin texto no hay con qué formar la consulta semántica; la evidencia
        # del período (criterio 2) basta para generar la bitácora.
        if not consulta:
            return []

        query_embedding = self._embeddings.embed(consulta)
        filtros = {
            "id_nino": id_nino,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
        }
        resultados = self._vector.search(query_embedding, filtros, MAX_SIMILARES)

        ids_periodo = {obs.id_observacion for obs in observaciones}
        similares: list[dict] = []
        for doc in resultados:
            if doc.get("id_observacion") in ids_periodo:
                continue
            similares.append(doc)
            if len(similares) >= MAX_SIMILARES:
                break
        return similares

    def _construir_contexto(
        self,
        observaciones: list[ObservacionORM],
        similares: list[dict],
        rubrica: RubricaVersionORM | None,
    ) -> str:
        """Arma el contexto RAG: evidencia citable + rúbrica vigente (5.3, 5.5).

        Incluye explícitamente la lista de ``id_observacion`` y de ids de
        manifestación disponibles, de modo que el LLM pueda citar cada
        afirmación evaluativa por su identificador (Requirement 5.5).
        """
        lineas: list[str] = []

        lineas.append("## Evidencia del período (observaciones)")
        ids_disponibles: list[str] = []
        ids_manifestaciones: list[str] = []
        for indice, obs in enumerate(observaciones, start=1):
            ids_disponibles.append(obs.id_observacion)
            nivel = obs.nivel_estimado if obs.nivel_estimado is not None else "s/n"
            nota = (obs.nota_breve or "").strip() or "(sin nota)"
            manifestaciones = self._repo.manifestaciones_de_observacion(
                obs.id_observacion
            )
            ids_man_obs = [m.id_manifestacion for m in manifestaciones]
            ids_manifestaciones.extend(ids_man_obs)
            reglas_observables = [
                (
                    f"{m.id_manifestacion} "
                    f"[{getattr(m.dominio, 'value', m.dominio)}]: "
                    f"{m.texto_observable}"
                )
                for m in manifestaciones
            ]
            lineas.append(
                f"- Observación {indice} (referencia interna {obs.id_observacion}) "
                f"(fecha {obs.fecha_observacion.isoformat()}, nivel {nivel}): "
                f"{nota}."
            )
            if reglas_observables:
                lineas.append(
                    "  Reglas/manifestaciones observables respaldadas: "
                    + " | ".join(reglas_observables)
                )

        if similares:
            lineas.append("")
            lineas.append("## Evidencia similar recuperada (RAG)")
            for doc in similares:
                id_obs = doc.get("id_observacion", "s/id")
                if id_obs not in ids_disponibles:
                    ids_disponibles.append(id_obs)
                texto = str(doc.get("texto", "")).strip() or "(sin texto)"
                lineas.append(f"- {id_obs}: {texto}")

        lineas.append("")
        lineas.append("## Identificadores citables disponibles")
        lineas.append(
            "Observaciones: "
            + (", ".join(ids_disponibles) if ids_disponibles else "(ninguna)")
        )
        lineas.append(
            "Manifestaciones: "
            + (
                ", ".join(sorted(set(ids_manifestaciones)))
                if ids_manifestaciones
                else "(ninguna)"
            )
        )

        lineas.append("")
        lineas.append("## Rúbrica vigente")
        if rubrica is not None:
            lineas.append(
                f"Versión {rubrica.version_rubrica}: "
                f"{rubrica.descripcion or '(sin descripción)'}"
            )
        else:
            lineas.append("(no hay rúbrica vigente registrada)")

        return "\n".join(lineas)

    def _construir_prompt(
        self, id_nino: str, fecha_inicio: date, fecha_fin: date
    ) -> str:
        """Prompt que exige trazabilidad por identificador (Requirement 5.5)."""
        return (
            "Redacta en español (es-CL), con registro sobrio y pedagógico, la "
            f"bitácora quincenal del niño/a {id_nino} para el período "
            f"{fecha_inicio.isoformat()} a {fecha_fin.isoformat()}. "
            "Fundaméntate únicamente en la evidencia y en las reglas/manifestaciones "
            "observables entregadas en el contexto; "
            "no inventes datos. CADA afirmación evaluativa DEBE citar al menos "
            "una observación (por su id_observacion) o una manifestación (por "
            "su identificador) de la evidencia que la respalde. No incluyas "
            "afirmaciones sin su cita de respaldo. Escribe entre 120 y 180 "
            "palabras, sin títulos ni listas, en tres párrafos breves: síntesis "
            "del período, evidencia principal y próximo paso pedagógico. Cita "
            "al menos una referencia por párrafo usando exclusivamente las "
            "etiquetas 'Observación 1', 'Observación 2', etc.; no muestres UUID "
            "ni identificadores técnicos de observación. Termina con una "
            "oración completa."
        )

    @staticmethod
    def _numerar_referencias_observaciones(
        texto: str,
        observaciones: list[ObservacionORM],
        similares: list[dict],
    ) -> str:
        """Reemplaza identificadores técnicos por Observación 1, 2, etc."""
        ids: list[str] = []
        for observacion in observaciones:
            if observacion.id_observacion not in ids:
                ids.append(observacion.id_observacion)
        for documento in similares:
            ident = str(documento.get("id_observacion", "")).strip()
            if ident and ident not in ids:
                ids.append(ident)

        resultado = texto
        for indice, ident in enumerate(ids, start=1):
            patron = (
                rf"(?<![\w-])(?:observaci[oó]n\s+)?"
                rf"{re.escape(ident)}(?![\w-])"
            )
            resultado = re.sub(
                patron,
                f"Observación {indice}",
                resultado,
                flags=re.IGNORECASE,
            )
        return resultado
    def _invocar_llm(self, prompt: str, context: str) -> str:
        """Invoca el LLM aplicando el plazo máximo de 60 s (Requirement 5.4).

        El plazo se aplica de forma verificable con un ejecutor de un hilo: si
        la invocación excede ``self._plazo_llm_segundos`` o lanza
        :class:`LlmError`, se traduce a :class:`BitacoraLlmError` y la
        generación se aborta sin persistir ninguna bitácora.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            futuro = executor.submit(self._llm.generate, prompt, context)
            try:
                return futuro.result(timeout=self._plazo_llm_segundos)
            except concurrent.futures.TimeoutError as exc:
                # No cancelamos el hilo subyacente (no es interrumpible), pero
                # abortamos la generación: el llamador no persiste nada.
                raise BitacoraLlmError(
                    "La generación de la bitácora no pudo completarse: el "
                    "modelo de lenguaje excedió el tiempo máximo permitido "
                    f"({int(self._plazo_llm_segundos)} segundos)."
                ) from exc
            except LlmError as exc:
                raise BitacoraLlmError(
                    "La generación de la bitácora no pudo completarse: el "
                    "modelo de lenguaje devolvió un error."
                ) from exc


__all__ = [
    "BitacoraService",
    "BitacoraSinEvidenciaError",
    "BitacoraLlmError",
    "BitacoraNoEncontradaError",
    "BitacoraConflictoError",
    "EmbeddingPort",
    "PLAZO_LLM_SEGUNDOS",
    "MAX_SIMILARES",
]
