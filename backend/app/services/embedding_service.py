"""``EmbeddingService`` — embeber el texto de una observación e indexarlo (Módulo C).

Caso de uso del Módulo C: a partir de una observación con su texto transcrito,
genera el embedding del texto mediante el ``EmbeddingProvider`` activo
(Requirement 4.2) y lo indexa en la base vectorial mediante ``VectorRepo`` con
los seis metadatos de contrato ``id_observacion``, ``id_nino``, ``dominio``,
``nivel``, ``fecha`` y ``formato`` (Requirement 4.3).

Principio DIP: el servicio depende **solo** de las interfaces congeladas del
Módulo A (``EmbeddingProvider`` y ``VectorRepo``), inyectadas por el constructor.
No referencia ningún SDK de base de datos ni boto3 (Requirement 4.7).

Contrato de fallo (Requirement 4.4): si la generación del embedding **o** su
indexación en la base vectorial falla, el servicio **no** altera ni descarta la
observación relacional —de hecho, no toca el repositorio relacional del cuerpo
de la observación: esa persistencia es responsabilidad del llamador
(``IngestionService``), que debe conservarla intacta—. El servicio solo señala,
con un error tipado (``IndexacionVectorialError``, subtipo de ``EmbeddingError``),
que la indexación vectorial no se completó, dejando a la observación en la base
relacional **sin registro vectorial asociado**.
"""

from __future__ import annotations

from typing import Any

from app.domain.models import Observacion
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.errors import EmbeddingError
from app.repositories.vector.base import VectorRepo

# Mensaje de contrato (en español) para el fallo de indexación (Requirement 4.4).
MENSAJE_INDEXACION_NO_COMPLETADA = (
    "La indexación vectorial no se completó; la observación se conserva en la "
    "base relacional sin registro vectorial asociado."
)


class IndexacionVectorialError(EmbeddingError):
    """La indexación vectorial de una observación no se completó (Requirement 4.4).

    Es un subtipo de :class:`EmbeddingError` para que la capa de API (Módulo G)
    pueda traducir ambos a la misma familia de respuesta en español, pero su tipo
    específico deja explícito que la observación relacional **no** se perdió: solo
    quedó sin registro vectorial. El fallo original (del embedding o de la
    indexación) viaja encadenado en ``__cause__``.
    """


class EmbeddingService:
    """Embebe el texto de una observación y lo indexa en la base vectorial.

    Args:
        embedding_provider: proveedor activo de embeddings (Titan primario o mock
            secundario), inyectado por el contenedor de DI (DIP).
        vector_repo: repositorio vectorial (pgvector primario o índice en memoria
            secundario), inyectado por el contenedor de DI (DIP).
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_repo: VectorRepo,
    ) -> None:
        self._embeddings = embedding_provider
        self._vectors = vector_repo

    def embed_and_index(
        self,
        observacion: Observacion,
        texto_transcrito: str,
    ) -> dict[str, Any]:
        """Embebe ``texto_transcrito`` e indexa el documento de la observación.

        Flujo (Requirements 4.2, 4.3):
            1. Genera el embedding del texto con el ``EmbeddingProvider`` activo.
            2. Arma el documento-por-observación con los seis metadatos de
               contrato + el texto transcrito + el embedding.
            3. Lo indexa en la base vectorial con ``VectorRepo.index``.

        Args:
            observacion: la observación ya persistida en la base relacional, de
                la que se derivan los seis metadatos de contrato. El servicio no
                la modifica ni la vuelve a persistir.
            texto_transcrito: el texto (transcrito o directo) a embeber. Debe ser
                no vacío.

        Returns:
            El documento indexado (incluye ``embedding`` y los seis metadatos),
            útil para que el llamador registre o verifique la indexación.

        Raises:
            IndexacionVectorialError: si la generación del embedding o la
                indexación en la base vectorial falla. En ese caso la observación
                relacional **no** se altera ni se descarta (Requirement 4.4); el
                llamador debe conservarla sin registro vectorial. El fallo
                original queda encadenado en ``__cause__``.
        """
        if texto_transcrito is None or not texto_transcrito.strip():
            raise IndexacionVectorialError(MENSAJE_INDEXACION_NO_COMPLETADA)

        documento = self._build_document(observacion, texto_transcrito)

        try:
            # 1) Generar el embedding del texto (Requirement 4.2).
            documento["embedding"] = self._embeddings.embed(texto_transcrito)
            # 2) Indexar el documento en la base vectorial (Requirement 4.3).
            self._vectors.index(documento)
        except EmbeddingError as exc:
            # Fallo del embedding o de la indexación: la observación relacional se
            # conserva intacta (no se toca aquí) y se señala que la indexación no
            # se completó (Requirement 4.4).
            raise IndexacionVectorialError(MENSAJE_INDEXACION_NO_COMPLETADA) from exc
        except Exception as exc:
            # Cualquier otro fallo inesperado del proveedor/repo se normaliza al
            # mismo contrato: la observación relacional no se pierde.
            raise IndexacionVectorialError(MENSAJE_INDEXACION_NO_COMPLETADA) from exc

        return documento

    @staticmethod
    def _build_document(
        observacion: Observacion,
        texto_transcrito: str,
    ) -> dict[str, Any]:
        """Arma el documento-por-observación con los seis metadatos de contrato.

        El ``dominio`` y el ``nivel`` provienen de la clasificación de la
        observación. Si la observación tiene más de un dominio estimado, se indexa
        el primero como metadato de dominio del documento (el contrato pide un
        único valor de ``dominio`` por documento); el texto completo permanece en
        ``texto_transcrito`` para la búsqueda semántica. Los enums se serializan a
        su valor (``str``) para que el documento sea homogéneo con el índice.
        """
        dominio = observacion.dominios[0] if observacion.dominios else None
        return {
            "id_observacion": observacion.id_observacion,
            "id_nino": observacion.id_nino,
            "dominio": dominio.value if dominio is not None else None,
            "nivel": observacion.nivel_estimado,
            "fecha": observacion.fecha_observacion,
            "formato": observacion.formato_captura.value,
            "texto_transcrito": texto_transcrito,
        }


__all__ = [
    "EmbeddingService",
    "IndexacionVectorialError",
    "MENSAJE_INDEXACION_NO_COMPLETADA",
]
