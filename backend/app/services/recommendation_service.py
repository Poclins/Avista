"""``RecommendationService`` del Módulo F (Modelo 3 — recomendación de nivel).

Orquesta, **dentro de la frontera del Módulo F**, el flujo de recomendación de
nivel de un niño/a:

evidencia previa (``RelationalRepo`` + RAG sobre ``VectorRepo``) →
``RubricaDecision`` (mapea la evidencia a las **conductas observables** del
tramo × núcleo × nivel actual y **decide** de forma determinista) →
``LlmProvider`` (redacta **solo el argumento** citando conductas y evidencia,
sin alterar la decisión) → persistencia de la ``Recomendacion`` con
``version_rubrica``.

Principio clave (Requirements 6.2, 6.7, 21.4): **la rúbrica decide, la IA
argumenta y la educadora valida.** La decisión AVANZAR/MANTENER/RETROCEDER
proviene siempre de ``RubricaDecision``; el ``LlmProvider`` nunca la cambia.

Principio de aislamiento (Requirement 13): este servicio depende **solo de
puertos** inyectados por constructor (``RelationalRepo``, ``VectorRepo``,
``LlmProvider`` y un ``EmbeddingPort`` definido localmente como hace la ingesta).
No importa ninguna implementación concreta de módulos hermanos; en los tests se
usan fakes locales.

Garantías cubiertas:
- **6.1 — Respuesta en ≤10 s con una de AVANZAR/MANTENER/RETROCEDER:** el
  argumento del LLM se calcula bajo un plazo máximo configurable (10 s por
  defecto); si se excede, se conserva la decisión determinista.
- **6.5 — Respuesta completa:** incluye decisión, tramo, núcleo, nivel, score,
  conductas cubiertas/pendientes, evidencia citada y ``version_rubrica``.
- **6.8 — Sugerencia proactiva:** helper que indica si el ``score`` cruza el
  umbral de avance de la rúbrica vigente.
- **6.9 — Decisión humana final:** ``registrar_decision_educadora`` persiste uno
  de ``aceptó``/``rechazó``/``ajustó`` en ``decision_educadora``.
- **6.10 — Abstención por datos insuficientes (<5 observaciones):** no persiste
  recomendación y devuelve un indicador señalando cuántas observaciones faltan.
- **6.11 — Resiliencia del LLM:** si el LLM falla o excede el plazo, conserva y
  devuelve la decisión determinista con el argumento marcado como no disponible.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturoTimeout
from datetime import date
from typing import Any, Protocol, runtime_checkable

from app.domain.contracts import ResultadoRubrica
from app.domain.models import DecisionNivel
from app.domain.rubrica import NUCLEO_POR_DEFECTO, RubricaDecision
from app.providers.errors import LlmError
from app.providers.llm.base import LlmProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import Nino as NinoORM, Recomendacion as RecomendacionORM
from app.repositories.vector.base import VectorRepo

# Mínimo de observaciones para poder emitir una decisión (Requirement 6.10).
MIN_OBSERVACIONES = 5

# Plazo máximo por defecto para el argumento del LLM (Requirements 6.1, 6.11).
LLM_TIMEOUT_SEGUNDOS = 10.0

# Umbral de avance por defecto si la rúbrica vigente no lo define (coincide con
# ``RubricaDecision``).
_COBERTURA_AVANZAR_DEFAULT = 0.8

# Vecinos a recuperar en la búsqueda semántica (RAG) de evidencia previa.
_RAG_K = 10

# Mensaje estándar cuando el argumento del LLM no está disponible (6.11).
ARGUMENTO_NO_DISPONIBLE = "El argumento generado por IA no está disponible."

# Valores admitidos para la decisión final de la educadora (Requirement 6.9).
DECISIONES_EDUCADORA = frozenset({"aceptó", "rechazó", "ajustó"})


class RecommendationError(Exception):
    """Error de dominio del servicio de recomendación (mensajes en español)."""


class RecommendationValidationError(RecommendationError):
    """Entrada inválida (traducible a HTTP 400). No produce efectos de escritura."""


@runtime_checkable
class EmbeddingPort(Protocol):
    """Puerto mínimo de embeddings que consume la recomendación para el RAG.

    El servicio de embeddings concreto pertenece al Módulo C; para no acoplar el
    Módulo F a esa implementación, aquí se declara solo la capacidad necesaria:
    convertir el texto de consulta en un vector para ``VectorRepo.search``. El
    contenedor de DI inyecta la implementación real; los tests inyectan un fake.
    """

    def embed(self, text: str) -> list[float]:
        """Devuelve el embedding del texto de consulta para la búsqueda RAG."""
        ...


class ResultadoRecomendacion:
    """Resultado de ``recomendar`` entregado a la capa de API / tests.

    Expone la decisión determinista, su fundamento (tramo/núcleo/nivel, score,
    conductas y evidencia), la ``version_rubrica`` y el argumento legible. Cuando
    el niño/a tiene datos insuficientes, ``datos_insuficientes`` es ``True``, la
    recomendación **no** se persiste y ``observaciones_faltantes`` indica cuántas
    observaciones faltan para alcanzar el mínimo (Requirement 6.10).
    """

    __slots__ = (
        "id_recomendacion",
        "id_nino",
        "id_educadora",
        "decision",
        "tramo",
        "nucleo",
        "nivel_actual",
        "score",
        "conductas_observables_cubiertas",
        "conductas_observables_pendientes",
        "evidencia",
        "version_rubrica",
        "argumento_ia",
        "argumento_disponible",
        "datos_insuficientes",
        "observaciones_registradas",
        "observaciones_faltantes",
        "persistida",
    )

    def __init__(
        self,
        *,
        id_recomendacion: str | None,
        id_nino: str,
        id_educadora: str,
        decision: DecisionNivel | None,
        tramo: str | None,
        nucleo: str | None,
        nivel_actual: int | None,
        score: float | None,
        conductas_observables_cubiertas: list[str],
        conductas_observables_pendientes: list[str],
        evidencia: list[str],
        version_rubrica: str | None,
        argumento_ia: str,
        argumento_disponible: bool,
        datos_insuficientes: bool,
        observaciones_registradas: int,
        observaciones_faltantes: int,
        persistida: bool,
    ) -> None:
        self.id_recomendacion = id_recomendacion
        self.id_nino = id_nino
        self.id_educadora = id_educadora
        self.decision = decision
        self.tramo = tramo
        self.nucleo = nucleo
        self.nivel_actual = nivel_actual
        self.score = score
        self.conductas_observables_cubiertas = conductas_observables_cubiertas
        self.conductas_observables_pendientes = conductas_observables_pendientes
        self.evidencia = evidencia
        self.version_rubrica = version_rubrica
        self.argumento_ia = argumento_ia
        self.argumento_disponible = argumento_disponible
        self.datos_insuficientes = datos_insuficientes
        self.observaciones_registradas = observaciones_registradas
        self.observaciones_faltantes = observaciones_faltantes
        self.persistida = persistida


class RecommendationService:
    """Orquesta la recomendación de nivel (la rúbrica decide, la IA argumenta).

    Depende únicamente de puertos inyectados por constructor (DIP + ISP). La
    ``RubricaDecision`` se construye con los ``criterios`` de la rúbrica vigente
    (``RelationalRepo.rubrica_vigente()``), de modo que agregar tramos/núcleos es
    cuestión de datos y no de código (Requirements 21.4, 21.6).
    """

    def __init__(
        self,
        repo: RelationalRepo,
        vector_repo: VectorRepo,
        llm: LlmProvider,
        embeddings: EmbeddingPort,
        *,
        timeout_segundos: float = LLM_TIMEOUT_SEGUNDOS,
    ) -> None:
        self._repo = repo
        self._vector = vector_repo
        self._llm = llm
        self._embeddings = embeddings
        self._timeout = timeout_segundos

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def recomendar(
        self,
        id_nino: str,
        id_educadora: str,
        nivel_actual: int,
        *,
        nucleo: str = NUCLEO_POR_DEFECTO,
        fecha: date | None = None,
    ) -> ResultadoRecomendacion:
        """Produce la recomendación de nivel de un niño/a.

        Flujo (ver design.md §RecommendationService):
        1. Recuperar la evidencia previa del niño/a (``RelationalRepo`` + RAG).
        2. **Abstención (6.10):** si tiene <5 observaciones, no persistir y
           devolver un indicador de datos insuficientes.
        3. ``RubricaDecision.evaluar`` produce la decisión determinista.
        4. Construir el contexto para el LLM (conductas + evidencia) y pedir
           **solo el argumento** bajo un plazo máximo (6.1, 6.7, 21.4).
        5. **Resiliencia (6.11):** si el LLM falla/excede el plazo, conservar la
           decisión determinista con el argumento marcado como no disponible.
        6. La respuesta incluye decisión, tramo, núcleo, nivel, score, conductas
           cubiertas/pendientes, evidencia y ``version_rubrica`` (6.5).
        7. Persistir la ``Recomendacion`` con ``version_rubrica`` (salvo si hubo
           abstención).

        Raises:
            RecommendationValidationError: si falta ``id_nino`` o ``id_educadora``.
            RecommendationError: si no existe el niño/a o no hay rúbrica vigente.
        """
        if not id_nino or not id_educadora:
            raise RecommendationValidationError(
                "Debe indicar un niño/a (id_nino) y una educadora de sesión "
                "(id_educadora) para solicitar una recomendación."
            )

        nino = self._repo.get(NinoORM, id_nino)
        if nino is None:
            raise RecommendationError(
                f"No se encontró el niño/a con id_nino={id_nino!r}."
            )

        # 1. Evidencia previa: observaciones relacionales (fuente autoritativa).
        observaciones = self._repo.observaciones_de_nino(id_nino)

        # 2. Abstención por datos insuficientes (Requirement 6.10): sin persistir.
        registradas = len(observaciones)
        if registradas < MIN_OBSERVACIONES:
            faltantes = MIN_OBSERVACIONES - registradas
            return ResultadoRecomendacion(
                id_recomendacion=None,
                id_nino=id_nino,
                id_educadora=id_educadora,
                decision=None,
                tramo=None,
                nucleo=None,
                nivel_actual=None,
                score=None,
                conductas_observables_cubiertas=[],
                conductas_observables_pendientes=[],
                evidencia=[],
                version_rubrica=None,
                argumento_ia=(
                    "Datos insuficientes para recomendar: el niño/a tiene "
                    f"{registradas} observación(es) registrada(s) y se "
                    f"requieren al menos {MIN_OBSERVACIONES}. Faltan "
                    f"{faltantes} observación(es)."
                ),
                argumento_disponible=False,
                datos_insuficientes=True,
                observaciones_registradas=registradas,
                observaciones_faltantes=faltantes,
                persistida=False,
            )

        # RAG: complementar la evidencia con la búsqueda semántica (6.3). No es
        # la fuente de la decisión (que es determinista), sino contexto adicional
        # para el argumento del LLM. Un fallo de RAG degrada sin romper el flujo.
        evidencia_rag = self._recuperar_rag(id_nino, observaciones)

        # 3. Decisión determinista de la rúbrica vigente (Requirements 6.2–6.4).
        rubrica = self._rubrica_vigente()
        resultado = rubrica.evaluar(
            self._a_dominio_nino(nino),
            [self._a_dominio_obs(o) for o in observaciones],
            nivel_actual,
            nucleo=nucleo,
        )

        # 4–5. Argumento del LLM bajo plazo máximo; la decisión no cambia (6.7).
        argumento, disponible = self._argumentar(resultado, evidencia_rag)

        # 7. Persistir la recomendación con la version_rubrica (6.5, 6.6).
        id_recomendacion = uuid.uuid4().hex
        fecha_rec = fecha or date.today()
        recomendacion = RecomendacionORM(
            id_recomendacion=id_recomendacion,
            id_nino=id_nino,
            id_educadora=id_educadora,
            decision=resultado.decision,
            score=resultado.score,
            # La tabla usa nombres heredados ``dominios_*``; aquí mapeamos las
            # listas de conductas observables cubiertas/pendientes (sin cambiar
            # el esquema congelado).
            dominios_cubiertos=list(resultado.conductas_observables_cubiertas),
            dominios_pendientes=list(resultado.conductas_observables_pendientes),
            argumento_ia=argumento,
            version_rubrica=resultado.version_rubrica,
            decision_educadora=None,  # la decisión humana se registra aparte (6.9)
            fecha=fecha_rec,
        )
        self._repo.add(recomendacion)

        return ResultadoRecomendacion(
            id_recomendacion=id_recomendacion,
            id_nino=id_nino,
            id_educadora=id_educadora,
            decision=resultado.decision,
            tramo=resultado.tramo,
            nucleo=resultado.nucleo,
            nivel_actual=resultado.nivel_actual,
            score=resultado.score,
            conductas_observables_cubiertas=list(
                resultado.conductas_observables_cubiertas
            ),
            conductas_observables_pendientes=list(
                resultado.conductas_observables_pendientes
            ),
            evidencia=list(resultado.evidencia),
            version_rubrica=resultado.version_rubrica,
            argumento_ia=argumento,
            argumento_disponible=disponible,
            datos_insuficientes=False,
            observaciones_registradas=registradas,
            observaciones_faltantes=0,
            persistida=True,
        )

    def registrar_decision_educadora(
        self, id_recomendacion: str, decision_educadora: str
    ) -> RecomendacionORM:
        """Registra la decisión humana final sobre una recomendación (6.9).

        ``decision_educadora`` debe ser uno de ``aceptó`` / ``rechazó`` /
        ``ajustó``. Persiste el valor de modo que la decisión final siempre sea
        humana (human-in-the-loop, Requirement 16.5).

        Raises:
            RecommendationValidationError: si el valor no es uno de los admitidos.
            RecommendationError: si la recomendación no existe.
        """
        valor = (decision_educadora or "").strip().lower()
        # Normalizar sin tildes para aceptar "acepto"/"aceptó", etc., pero
        # persistir el valor canónico con tilde.
        canonico = _canonizar_decision_educadora(valor)
        if canonico is None:
            raise RecommendationValidationError(
                "La decisión de la educadora debe ser una de: "
                "aceptó, rechazó o ajustó."
            )

        recomendacion = self._repo.get(RecomendacionORM, id_recomendacion)
        if recomendacion is None:
            raise RecommendationError(
                f"No se encontró la recomendación con id={id_recomendacion!r}."
            )

        recomendacion.decision_educadora = canonico
        self._repo.add(recomendacion)
        return recomendacion

    def sugerir_avance(
        self,
        id_nino: str,
        nivel_actual: int,
        *,
        nucleo: str = NUCLEO_POR_DEFECTO,
    ) -> bool:
        """Indica si corresponde sugerir avance proactivamente (Requirement 6.8).

        Devuelve ``True`` cuando el ``score`` determinista del niño/a alcanza o
        supera el umbral de avance de la rúbrica vigente. No persiste nada: es un
        helper consultable tras registrar una observación/bitácora para decidir
        si mostrar la sugerencia proactiva en la ficha del niño/a.

        Si el niño/a no existe o tiene datos insuficientes (<5 observaciones), no
        corresponde sugerir avance y devuelve ``False``.
        """
        nino = self._repo.get(NinoORM, id_nino)
        if nino is None:
            return False
        observaciones = self._repo.observaciones_de_nino(id_nino)
        if len(observaciones) < MIN_OBSERVACIONES:
            return False

        rubrica = self._rubrica_vigente()
        resultado = rubrica.evaluar(
            self._a_dominio_nino(nino),
            [self._a_dominio_obs(o) for o in observaciones],
            nivel_actual,
            nucleo=nucleo,
        )
        return resultado.score >= self._umbral_avance()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _rubrica_vigente(self) -> RubricaDecision:
        """Construye ``RubricaDecision`` con los criterios de la rúbrica vigente."""
        vigente = self._repo.rubrica_vigente()
        if vigente is None:
            raise RecommendationError(
                "No hay una versión de rúbrica vigente para evaluar la "
                "recomendación."
            )
        return RubricaDecision(vigente.criterios)

    def _umbral_avance(self) -> float:
        """Lee el umbral de avance de la rúbrica vigente (o el valor por defecto)."""
        vigente = self._repo.rubrica_vigente()
        criterios = (vigente.criterios if vigente else {}) or {}
        umbrales = criterios.get("umbrales", {}) or {}
        try:
            return float(umbrales.get("cobertura_avanzar", _COBERTURA_AVANZAR_DEFAULT))
        except (TypeError, ValueError):  # pragma: no cover - criterios malformados
            return _COBERTURA_AVANZAR_DEFAULT

    def _recuperar_rag(
        self, id_nino: str, observaciones: list[Any]
    ) -> list[dict[str, Any]]:
        """Recupera evidencia semántica previa del niño/a vía ``VectorRepo``.

        Embebe una consulta derivada de las notas recientes del niño/a y busca
        documentos similares acotados por ``id_nino``. Un fallo de embeddings o
        de la base vectorial **degrada** devolviendo lista vacía: la decisión es
        determinista y no depende del RAG (Requirements 4.4, 6.2).
        """
        consulta = " ".join(
            (getattr(o, "nota_breve", None) or "") for o in observaciones
        ).strip()
        if not consulta:
            return []
        try:
            vector = self._embeddings.embed(consulta)
            return self._vector.search(vector, {"id_nino": id_nino}, _RAG_K)
        except Exception:  # noqa: BLE001 - RAG es best-effort; degrada sin romper
            return []

    def _argumentar(
        self, resultado: ResultadoRubrica, evidencia_rag: list[dict[str, Any]]
    ) -> tuple[str, bool]:
        """Pide al LLM el argumento legible bajo el plazo máximo (6.1, 6.11).

        Devuelve ``(argumento, disponible)``. Si el LLM falla o excede el plazo,
        devuelve ``(ARGUMENTO_NO_DISPONIBLE, False)`` sin alterar la decisión.
        """
        prompt = self._construir_prompt(resultado)
        context = self._construir_contexto(resultado, evidencia_rag)

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                futuro = executor.submit(self._llm.generate, prompt, context)
                try:
                    argumento = futuro.result(timeout=self._timeout)
                except FuturoTimeout:
                    # El LLM excedió el plazo máximo (Requirement 6.11): se
                    # cancela y se conserva la decisión determinista.
                    futuro.cancel()
                    return ARGUMENTO_NO_DISPONIBLE, False
        except LlmError:
            # El proveedor falló (Requirement 6.11): decisión conservada.
            return ARGUMENTO_NO_DISPONIBLE, False

        texto = (argumento or "").strip()
        if not texto:
            return ARGUMENTO_NO_DISPONIBLE, False
        return texto, True

    @staticmethod
    def _construir_prompt(resultado: ResultadoRubrica) -> str:
        """Instrucción para el LLM: argumentar SIN alterar la decisión (6.7)."""
        return (
            "Redacta en español (Chile), con registro pedagógico y sobrio, un "
            "argumento breve que justifique la decisión de nivel ya tomada por "
            f"la rúbrica oficial ({resultado.decision.value}). Cita las "
            "conductas observables específicas (cubiertas y pendientes) y las "
            "observaciones previas por su identificador. No cambies la decisión "
            "ni inventes evidencia; solo explica por qué la rúbrica decidió así."
        )

    @staticmethod
    def _construir_contexto(
        resultado: ResultadoRubrica, evidencia_rag: list[dict[str, Any]]
    ) -> str:
        """Contexto fundamentante del argumento: conductas + evidencia (6.7)."""
        cubiertas = "; ".join(resultado.conductas_observables_cubiertas) or "ninguna"
        pendientes = (
            "; ".join(resultado.conductas_observables_pendientes) or "ninguna"
        )
        evidencia_ids = ", ".join(resultado.evidencia) or "sin observaciones citadas"
        extractos: list[str] = []
        for doc in evidencia_rag:
            texto = str(doc.get("texto", "")).strip()
            ident = str(doc.get("id_observacion", "")).strip()
            if texto:
                extractos.append(f"[{ident}] {texto}" if ident else texto)
        extractos_txt = " | ".join(extractos) or "sin extractos adicionales"

        return (
            f"Decisión determinista: {resultado.decision.value}. "
            f"Tramo: {resultado.tramo}. Núcleo: {resultado.nucleo}. "
            f"Nivel actual: {resultado.nivel_actual}. "
            f"Score de cobertura: {resultado.score:.2f}. "
            f"Versión de rúbrica: {resultado.version_rubrica}. "
            f"Conductas observables cubiertas: {cubiertas}. "
            f"Conductas observables pendientes: {pendientes}. "
            f"Observaciones citadas (identificadores): {evidencia_ids}. "
            f"Extractos de evidencia previa (RAG): {extractos_txt}."
        )

    # --- Adaptación ORM → modelos de dominio para la rúbrica --------------
    @staticmethod
    def _a_dominio_nino(nino: NinoORM) -> Any:
        """Adapta un ``Nino`` ORM al modelo de dominio que consume la rúbrica.

        ``RubricaDecision`` solo lee ``fecha_nacimiento`` del niño/a; se usa un
        envoltorio ligero para no acoplar la rúbrica a SQLAlchemy ni exigir una
        validación Pydantic completa de campos irrelevantes a la decisión.
        """
        return _VistaNino(fecha_nacimiento=nino.fecha_nacimiento)

    @staticmethod
    def _a_dominio_obs(obs: Any) -> Any:
        """Adapta una ``Observacion`` ORM a la vista que consume la rúbrica.

        La rúbrica lee ``id_observacion``, ``fecha_observacion``,
        ``nivel_estimado``, ``nota_breve`` y ``manifestaciones``. Las
        manifestaciones se derivan de los vínculos ORM si están cargados.
        """
        manifestaciones: list[str] = []
        vinculos = getattr(obs, "manifestaciones", None) or []
        for v in vinculos:
            ident = getattr(v, "id_manifestacion", None)
            if ident:
                manifestaciones.append(str(ident))
        return _VistaObservacion(
            id_observacion=obs.id_observacion,
            fecha_observacion=obs.fecha_observacion,
            nivel_estimado=obs.nivel_estimado,
            nota_breve=obs.nota_breve or "",
            manifestaciones=manifestaciones,
        )


class _VistaNino:
    """Vista mínima de un niño/a para ``RubricaDecision`` (solo ``fecha_nacimiento``)."""

    __slots__ = ("fecha_nacimiento",)

    def __init__(self, *, fecha_nacimiento: date) -> None:
        self.fecha_nacimiento = fecha_nacimiento


class _VistaObservacion:
    """Vista mínima de una observación para ``RubricaDecision``."""

    __slots__ = (
        "id_observacion",
        "fecha_observacion",
        "nivel_estimado",
        "nota_breve",
        "manifestaciones",
    )

    def __init__(
        self,
        *,
        id_observacion: str,
        fecha_observacion: date,
        nivel_estimado: int | None,
        nota_breve: str,
        manifestaciones: list[str],
    ) -> None:
        self.id_observacion = id_observacion
        self.fecha_observacion = fecha_observacion
        self.nivel_estimado = nivel_estimado
        self.nota_breve = nota_breve
        self.manifestaciones = manifestaciones


def _canonizar_decision_educadora(valor: str) -> str | None:
    """Devuelve el valor canónico (con tilde) o ``None`` si no es admitido."""
    mapa = {
        "acepto": "aceptó",
        "aceptó": "aceptó",
        "rechazo": "rechazó",
        "rechazó": "rechazó",
        "ajusto": "ajustó",
        "ajustó": "ajustó",
    }
    return mapa.get(valor)


__all__ = [
    "RecommendationService",
    "ResultadoRecomendacion",
    "RecommendationError",
    "RecommendationValidationError",
    "EmbeddingPort",
    "MIN_OBSERVACIONES",
    "LLM_TIMEOUT_SEGUNDOS",
    "ARGUMENTO_NO_DISPONIBLE",
    "DECISIONES_EDUCADORA",
]
