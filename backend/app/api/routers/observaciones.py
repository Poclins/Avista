"""Routers de observaciones (Módulo G, tarea 9.3).

Endpoints del contrato REST (ver design.md §API):

- ``POST   /ninos/{id}/observaciones``          crear observación (multipart o
  texto) → clasificación propuesta (Requirement 1.1).
- ``GET    /ninos/{id}/observaciones``          listar observaciones del niño/a.
- ``PATCH  /observaciones/{id}/clasificacion``  confirmar/corregir clasificación
  (Requirements 3.3, 3.4).

Los routers son delgados: validan la entrada con Pydantic, delegan en los
servicios de la Capa 2 vía ``Depends(...)`` del contenedor de DI y dan forma a
la respuesta con los mappers. La traducción de las excepciones tipadas de
los servicios a respuestas HTTP en español es centralizada por los manejadores
globales de :mod:`app.api.errors` (tarea 9.4); el router solo valida la forma de
la entrada (p. ej. formato/archivo faltante → 422) y deja propagar los errores
de dominio para que el manejador global los traduzca de forma uniforme.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api import mappers
from app.api.schemas import (
    ClasificacionConfirmarIn,
    ObservacionClasificadaOut,
    ObservacionOut,
    ObservacionTextoIn,
)
from app.core.container import (
    get_classification_service,
    get_ingestion_service,
    get_relational_repo,
)
from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import FormatoCaptura
from app.repositories.relational.base import RelationalRepo
from app.repositories.schema import Nino as NinoORM, Observacion as ObservacionORM
from app.repositories.storage.base import StoredFile
from app.services.classification_service import ClassificationService
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["observaciones"])


@router.post(
    "/ninos/{id_nino}/observaciones",
    response_model=ObservacionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear observación (medio o texto) y obtener su clasificación propuesta",
)
async def crear_observacion(
    id_nino: str,
    id_educadora: str | None = Form(default=None),
    formato: FormatoCaptura | None = Form(default=None),
    texto: str | None = Form(default=None),
    fecha_observacion: date | None = Form(default=None),
    archivo: UploadFile | None = File(default=None),
    cuerpo: ObservacionTextoIn | None = None,
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> ObservacionOut:
    """Crea una observación a partir de un medio (multipart) o de texto directo.

    Acepta dos modos de entrada (Requirement 1.1):

    - **Multipart** (``multipart/form-data``): campos ``formato`` + o bien
      ``archivo`` (audio/foto/video) o ``texto`` (texto), y ``id_educadora``.
    - **JSON** (texto directo): cuerpo :class:`ObservacionTextoIn`.

    Devuelve la observación creada con su clasificación propuesta (sin
    persistir la clasificación; eso lo hace el PATCH tras la revisión humana).
    """
    # Resolver el origen de los datos: cuerpo JSON (texto) o multipart.
    if cuerpo is not None:
        id_educadora_val = cuerpo.id_educadora
        formato_val = FormatoCaptura.texto
        texto_val: str | None = cuerpo.texto
        fecha_val = cuerpo.fecha_observacion
        archivo_val: StoredFile | None = None
    else:
        if formato is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debe indicar el formato de captura de la observación.",
            )
        id_educadora_val = id_educadora
        formato_val = formato
        texto_val = texto
        fecha_val = fecha_observacion
        archivo_val = None
        if formato is not FormatoCaptura.texto:
            if archivo is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "El formato indicado requiere un archivo de medio "
                        "(campo 'archivo')."
                    ),
                )
            archivo_val = StoredFile(
                stream=archivo.file,
                filename=archivo.filename or "medio",
                tipo=archivo.content_type,
            )

    # ``IngestionValidationError`` (entrada inválida, Requirement 1.3 → 400) se
    # traduce en el manejador global de errores (tarea 9.4); el router solo
    # delega y da forma a la respuesta.
    resultado = ingestion.ingest(
        id_nino=id_nino,
        id_educadora=id_educadora_val,
        formato=formato_val,
        archivo=archivo_val,
        texto=texto_val,
        fecha_observacion=fecha_val,
    )

    return mappers.observacion_de_resultado(resultado)


@router.get(
    "/ninos/{id_nino}/observaciones",
    response_model=list[ObservacionOut],
    summary="Listar las observaciones de un niño/a",
)
def listar_observaciones(
    id_nino: str,
    repo: RelationalRepo = Depends(get_relational_repo),
) -> list[ObservacionOut]:
    """Lista las observaciones del niño/a ordenadas por fecha ascendente."""
    _asegurar_nino_existe(repo, id_nino)
    observaciones = repo.observaciones_de_nino(id_nino)
    return [mappers.observacion_de_orm(o) for o in observaciones]


@router.patch(
    "/observaciones/{id_observacion}/clasificacion",
    response_model=ObservacionClasificadaOut,
    summary="Confirmar o corregir la clasificación propuesta de una observación",
)
def actualizar_clasificacion(
    id_observacion: str,
    cuerpo: ClasificacionConfirmarIn,
    clasificacion: ClassificationService = Depends(get_classification_service),
) -> ObservacionClasificadaOut:
    """Persiste la clasificación confirmada o corregida de una observación.

    - ``accion="confirmar"``: aplica la propuesta tal cual (Requirement 3.4).
    - ``accion="corregir"``: aplica los valores corregidos por la educadora.

    No se persiste nada hasta esta acción humana explícita (Requirement 3.3).
    """
    # ``PersistenciaError`` (observación inexistente → 404, otro fallo → 422,
    # conservando los valores previos) se traduce en el manejador global de
    # errores (tarea 9.4), de forma consistente en toda la app.
    if cuerpo.accion == "confirmar":
        propuesta = ClasificacionPropuesta(
            nivel_estimado=cuerpo.nivel_estimado,
            dominios=cuerpo.dominios,
            manifestaciones=cuerpo.manifestaciones,
        )
        observacion = clasificacion.confirmar(id_observacion, propuesta)
    else:  # "corregir" (validado por el patrón del esquema)
        observacion = clasificacion.corregir(
            id_observacion,
            nivel_estimado=cuerpo.nivel_estimado,
            dominios=cuerpo.dominios,
            manifestaciones=cuerpo.manifestaciones,
        )

    return mappers.observacion_clasificada_de_orm(observacion)


def _asegurar_nino_existe(repo: RelationalRepo, id_nino: str) -> None:
    """Lanza 404 en español si el niño/a no existe (Requirement 10.6)."""
    if repo.get(NinoORM, id_nino) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el niño/a con id_nino={id_nino!r}.",
        )


__all__ = ["router"]
