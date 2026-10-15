"""``IngestionService`` idempotente del Módulo D (ingesta de observaciones).

Orquesta, **dentro de la frontera del Módulo D**, el flujo completo de alta de
una observación a partir de un medio o de texto directo:

``StorageRepo`` (guardar medio) → ``TranscriptionProvider`` (transcribir/OCR) →
``Classifier`` (clasificación propuesta) → ``RelationalRepo`` (persistencia) →
``EmbeddingService`` (indexación vectorial).

Principio de aislamiento (Requirement 13): este servicio depende **solo de
interfaces/puertos** (``StorageRepo``, ``TranscriptionProvider``, ``Classifier``,
``RelationalRepo`` y el protocolo ``EmbeddingService`` definido aquí). No importa
ninguna implementación concreta de módulos hermanos (ni el ``Classifier`` real
del Módulo E, ni el ``EmbeddingService`` real del Módulo C): todas las
dependencias se inyectan por constructor y en los tests se usan fakes locales.

Garantías cubiertas:
- **1.1 — Idempotencia / "exactamente una observación":** subir el mismo archivo
  dos veces (mismo contenido binario) **no** crea dos observaciones. Se usa una
  clave de contenido determinista (SHA-256 de los bytes del archivo, o del texto
  directo) para detectar duplicados y devolver la observación ya creada sin
  volver a almacenar, transcribir, clasificar ni indexar.
- **1.3 — Rechazo sin efectos secundarios:** si falta el ``id_nino`` seleccionado
  o la ``id_educadora`` de sesión, se rechaza con un error en español
  (traducible a HTTP 400) y **no** se crea observación ni se almacena archivo.
- **1.5 — Registro de fecha y formato:** toda observación creada registra su
  ``fecha_observacion`` y su ``formato_captura`` con exactamente uno de los
  valores (texto, audio, foto, video).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import FormatoCaptura
from app.providers.classifier.base import Classifier
from app.providers.transcription.base import TranscriptionProvider
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import (
    Observacion as ObservacionORM,
    ObservacionManifestacion,
)
from app.repositories.storage.base import StorageRepo, StoredFile


class IngestionValidationError(ValueError):
    """Entrada inválida de ingesta (traducible a HTTP 400, Requirement 1.3).

    Se usa cuando falta el ``id_nino`` o la ``id_educadora``. El mensaje va en
    español y la capa de API (Módulo G) lo traduce a una respuesta 400 sin
    filtrar detalles sensibles.
    """


@runtime_checkable
class EmbeddingService(Protocol):
    """Puerto mínimo del servicio de embeddings que consume la ingesta.

    El ``EmbeddingService`` concreto pertenece al Módulo C; para no acoplar el
    Módulo D a esa implementación, aquí se declara solo la capacidad que la
    ingesta necesita: embeber el texto de una observación e indexarlo. El
    contenedor de DI inyecta la implementación real; los tests inyectan un fake.
    """

    def index_observacion(self, id_observacion: str, texto: str) -> None:
        """Embebe el ``texto`` de una observación e indexa su vector.

        Un fallo de indexación no debe deshacer la observación relacional ya
        creada (Requirement 4.4); corresponde a la implementación del Módulo C
        decidir cómo degradar.
        """
        ...


class IngestionResult:
    """Resultado de una ingesta: la observación creada (o recuperada) + metadatos.

    Expone lo justo para que la capa de API responda y para que los tests
    verifiquen el comportamiento, sin filtrar tipos de SQLAlchemy.
    """

    __slots__ = (
        "id_observacion",
        "id_nino",
        "id_educadora",
        "fecha_observacion",
        "formato_captura",
        "texto",
        "media_ref",
        "clasificacion",
        "duplicado",
    )

    def __init__(
        self,
        *,
        id_observacion: str,
        id_nino: str,
        id_educadora: str,
        fecha_observacion: date,
        formato_captura: FormatoCaptura,
        texto: str,
        media_ref: str | None,
        clasificacion: ClasificacionPropuesta | None,
        duplicado: bool,
    ) -> None:
        self.id_observacion = id_observacion
        self.id_nino = id_nino
        self.id_educadora = id_educadora
        self.fecha_observacion = fecha_observacion
        self.formato_captura = formato_captura
        self.texto = texto
        self.media_ref = media_ref
        self.clasificacion = clasificacion
        self.duplicado = duplicado


# Tamaño de bloque para el hash incremental del contenido del archivo.
_HASH_CHUNK = 1 << 16  # 64 KiB


class IngestionService:
    """Orquesta la ingesta de observaciones de forma **idempotente**.

    Depende únicamente de puertos inyectados por constructor (DIP + ISP). La
    idempotencia respecto al archivo subido se logra con una clave de contenido
    determinista (hash del binario / del texto): dos cargas del mismo contenido
    para el mismo ``id_nino`` producen una sola observación (Requirement 1.1).
    """

    def __init__(
        self,
        storage: StorageRepo,
        transcriber: TranscriptionProvider,
        classifier: Classifier,
        repo: RelationalRepo,
        embeddings: EmbeddingService,
    ) -> None:
        self._storage = storage
        self._transcriber = transcriber
        self._classifier = classifier
        self._repo = repo
        self._embeddings = embeddings
        # Libro de idempotencia: clave de contenido → id_observacion ya creada.
        # Vive en el orquestador (Módulo D) para no exigir cambios al contrato
        # congelado de ``RelationalRepo``.
        self._por_clave: dict[str, str] = {}

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def ingest(
        self,
        *,
        id_nino: str | None,
        id_educadora: str | None,
        formato: FormatoCaptura,
        archivo: StoredFile | None = None,
        texto: str | None = None,
        fecha_observacion: date | None = None,
    ) -> IngestionResult:
        """Ingresa una observación (medio o texto) y devuelve su resultado.

        Args:
            id_nino: niño/a seleccionado (obligatorio, Requirement 1.3).
            id_educadora: educadora de la sesión (obligatorio, Requirement 1.3).
            formato: ``formato_captura`` de la observación (exactamente uno).
            archivo: medio a almacenar/transcribir cuando el formato no es texto.
            texto: texto directo cuando ``formato`` es ``texto``.
            fecha_observacion: fecha de la observación; por defecto, hoy.

        Returns:
            Un :class:`IngestionResult`. Si el mismo contenido ya se ingresó
            para el mismo ``id_nino``, ``duplicado`` es ``True`` y se devuelve la
            observación existente sin crear una nueva (Requirement 1.1).

        Raises:
            IngestionValidationError: si falta ``id_nino`` o ``id_educadora``
                (Requirement 1.3); no se almacena nada ni se crea observación.
        """
        # --- Validación previa (Requirement 1.3): sin efectos secundarios ---
        if not id_nino or not id_educadora:
            raise IngestionValidationError(
                "Debe seleccionar un niño/a (id_nino) y contar con una "
                "educadora de sesión (id_educadora) para registrar la "
                "observación."
            )

        # --- Clave de contenido determinista para idempotencia (1.1) --------
        clave = self._clave_contenido(
            id_nino=id_nino, formato=formato, archivo=archivo, texto=texto
        )
        existente = self._por_clave.get(clave)
        if existente is not None:
            return self._resultado_existente(existente, duplicado=True)

        # --- Almacenamiento del medio original (Requirement 1.2) ------------
        media_ref: str | None = None
        if formato is FormatoCaptura.texto:
            contenido_texto = (texto or "").strip()
        else:
            if archivo is None:
                raise IngestionValidationError(
                    "El formato indicado requiere un archivo de medio."
                )
            media_ref = self._storage.put(archivo)
            # --- Transcripción / extracción de texto (Modelo 1) -------------
            contenido_texto = self._transcriber.transcribe(media_ref, formato)

        # --- Clasificación propuesta (interfaz del Módulo E) ----------------
        clasificacion: ClasificacionPropuesta | None = None
        if contenido_texto:
            clasificacion = self._classifier.classify(contenido_texto)

        # --- Persistencia relacional (interfaz del Módulo B) ----------------
        id_observacion = uuid.uuid4().hex
        fecha = fecha_observacion or date.today()
        observacion = ObservacionORM(
            id_observacion=id_observacion,
            id_nino=id_nino,
            id_educadora=id_educadora,
            fecha_observacion=fecha,  # Requirement 1.5
            formato_captura=formato,  # Requirement 1.5 (exactamente uno)
            nivel_estimado=(
                clasificacion.nivel_estimado if clasificacion else None
            ),
            nota_breve=contenido_texto or None,
        )
        self._repo.add(observacion)

        # Vincular manifestaciones propuestas (si las hay) vía la tabla puente.
        if clasificacion and clasificacion.manifestaciones:
            self._repo.add_all(
                [
                    ObservacionManifestacion(
                        id_observacion=id_observacion,
                        id_manifestacion=id_manifestacion,
                    )
                    for id_manifestacion in clasificacion.manifestaciones
                ]
            )

        # --- Indexación vectorial (interfaz del Módulo C) -------------------
        # El libro de idempotencia se marca ANTES de indexar: la observación ya
        # existe y es la unidad que no debe duplicarse (Requirement 1.1), aun si
        # la indexación degrada (Requirement 4.4).
        self._por_clave[clave] = id_observacion
        if contenido_texto:
            self._embeddings.index_observacion(id_observacion, contenido_texto)

        return IngestionResult(
            id_observacion=id_observacion,
            id_nino=id_nino,
            id_educadora=id_educadora,
            fecha_observacion=fecha,
            formato_captura=formato,
            texto=contenido_texto,
            media_ref=media_ref,
            clasificacion=clasificacion,
            duplicado=False,
        )

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _clave_contenido(
        self,
        *,
        id_nino: str,
        formato: FormatoCaptura,
        archivo: StoredFile | None,
        texto: str | None,
    ) -> str:
        """Deriva una clave de contenido determinista para la idempotencia.

        La clave combina el ``id_nino`` con el hash del contenido (bytes del
        archivo o texto directo). Así, el mismo archivo para el mismo niño/a
        colisiona (una sola observación), mientras que el mismo archivo para
        otro niño/a es una observación legítimamente distinta.

        Para archivos, consume el stream y lo **rebobina** si es posible, de
        modo que ``StorageRepo.put`` siga pudiendo leer el contenido completo.
        """
        hasher = hashlib.sha256()
        if formato is FormatoCaptura.texto:
            hasher.update((texto or "").strip().encode("utf-8"))
        elif archivo is not None:
            stream = archivo.stream
            inicio = None
            if hasattr(stream, "tell") and hasattr(stream, "seekable"):
                try:
                    if stream.seekable():
                        inicio = stream.tell()
                except (OSError, ValueError):
                    inicio = None
            while True:
                bloque = stream.read(_HASH_CHUNK)
                if not bloque:
                    break
                hasher.update(bloque)
            # Rebobinar para que ``put`` pueda releer el contenido completo.
            if inicio is not None:
                try:
                    stream.seek(inicio)
                except (OSError, ValueError):
                    pass
        return f"{id_nino}:{formato.value}:{hasher.hexdigest()}"

    def _resultado_existente(
        self, id_observacion: str, *, duplicado: bool
    ) -> IngestionResult:
        """Reconstruye el resultado de una observación ya persistida."""
        obs = self._repo.get(ObservacionORM, id_observacion)
        if obs is None:  # pragma: no cover - inconsistencia improbable
            raise RuntimeError(
                f"Observación idempotente no encontrada: {id_observacion}"
            )
        return IngestionResult(
            id_observacion=obs.id_observacion,
            id_nino=obs.id_nino,
            id_educadora=obs.id_educadora,
            fecha_observacion=obs.fecha_observacion,
            formato_captura=obs.formato_captura,
            texto=obs.nota_breve or "",
            media_ref=None,
            clasificacion=None,
            duplicado=duplicado,
        )


__all__ = [
    "IngestionService",
    "IngestionResult",
    "IngestionValidationError",
    "EmbeddingService",
]
