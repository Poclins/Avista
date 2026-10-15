"""Adaptadores ORM/resultado-de-servicio → modelos de respuesta de la API.

Centralizan la conversión entre las entidades ORM (``app.repositories.schema``)
o los objetos de resultado de la Capa 2 (``IngestionResult``,
``ResultadoRecomendacion``, ``ResultadoReporte``) y los modelos Pydantic de
salida (``app.api.schemas``). Mantener este mapeo en un solo lugar evita que los
routers filtren tipos de SQLAlchemy y asegura una forma de respuesta estable.
"""

from __future__ import annotations

from typing import Any

from app.api.schemas import (
    BitacoraOut,
    ClasificacionOut,
    FichaNinoOut,
    NinoOut,
    NivelRutaOut,
    ObservacionClasificadaOut,
    ObservacionOut,
    RecomendacionOut,
    ReporteOut,
    RutaNivelesOut,
)


def clasificacion_out(clasificacion: Any | None) -> ClasificacionOut | None:
    """Mapea una ``ClasificacionPropuesta`` del dominio a su modelo de salida."""
    if clasificacion is None:
        return None
    return ClasificacionOut(
        nivel_estimado=clasificacion.nivel_estimado,
        dominios=list(clasificacion.dominios),
        manifestaciones=list(clasificacion.manifestaciones),
        confianza=clasificacion.confianza,
        pendiente_clasificacion_manual=clasificacion.pendiente_clasificacion_manual,
    )


def observacion_de_resultado(resultado: Any) -> ObservacionOut:
    """Mapea un ``IngestionResult`` al modelo de observación de la API."""
    return ObservacionOut(
        id_observacion=resultado.id_observacion,
        id_nino=resultado.id_nino,
        id_educadora=resultado.id_educadora,
        fecha_observacion=resultado.fecha_observacion,
        formato_captura=resultado.formato_captura,
        nivel_estimado=(
            resultado.clasificacion.nivel_estimado
            if resultado.clasificacion
            else None
        ),
        nota_breve=resultado.texto or "",
        duplicado=resultado.duplicado,
        clasificacion=clasificacion_out(resultado.clasificacion),
    )


def observacion_de_orm(obs: Any) -> ObservacionOut:
    """Mapea una ``Observacion`` ORM al modelo de observación de la API."""
    return ObservacionOut(
        id_observacion=obs.id_observacion,
        id_nino=obs.id_nino,
        id_educadora=obs.id_educadora,
        fecha_observacion=obs.fecha_observacion,
        formato_captura=obs.formato_captura,
        nivel_estimado=obs.nivel_estimado,
        nota_breve=obs.nota_breve or "",
        duplicado=False,
        clasificacion=None,
    )


def observacion_clasificada_de_orm(obs: Any) -> ObservacionClasificadaOut:
    """Mapea una ``Observacion`` ORM persistida tras clasificar."""
    return ObservacionClasificadaOut(
        id_observacion=obs.id_observacion,
        id_nino=obs.id_nino,
        id_educadora=obs.id_educadora,
        fecha_observacion=obs.fecha_observacion,
        formato_captura=obs.formato_captura,
        nivel_estimado=obs.nivel_estimado,
        nota_breve=obs.nota_breve or "",
    )


def nino_out(nino: Any) -> NinoOut:
    """Mapea un ``Nino`` ORM a su ficha básica de salida."""
    return NinoOut(
        id_nino=nino.id_nino,
        id_jardin=nino.id_jardin,
        fecha_nacimiento=nino.fecha_nacimiento,
        sexo_registrado=nino.sexo_registrado,
        sala_grupo=nino.sala_grupo,
        fecha_ingreso=nino.fecha_ingreso,
    )


def ficha_nino_out(nino: Any, observaciones: list[Any]) -> FichaNinoOut:
    """Compone la ficha + trayectoria de un niño/a."""
    return FichaNinoOut(
        nino=nino_out(nino),
        trayectoria=[observacion_de_orm(o) for o in observaciones],
    )


def bitacora_out(bitacora: Any) -> BitacoraOut:
    """Mapea una ``Bitacora`` ORM a su modelo de salida."""
    return BitacoraOut(
        id_bitacora=bitacora.id_bitacora,
        id_nino=bitacora.id_nino,
        id_educadora=bitacora.id_educadora,
        periodo=bitacora.periodo,
        texto_generado=bitacora.texto_generado,
        estado=bitacora.estado,
        fecha=bitacora.fecha,
    )


def recomendacion_out(resultado: Any) -> RecomendacionOut:
    """Mapea un ``ResultadoRecomendacion`` al modelo de salida."""
    return RecomendacionOut(
        id_recomendacion=resultado.id_recomendacion,
        id_nino=resultado.id_nino,
        id_educadora=resultado.id_educadora,
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
        argumento_ia=resultado.argumento_ia,
        argumento_disponible=resultado.argumento_disponible,
        datos_insuficientes=resultado.datos_insuficientes,
        observaciones_registradas=resultado.observaciones_registradas,
        observaciones_faltantes=resultado.observaciones_faltantes,
        persistida=resultado.persistida,
    )


def reporte_out(resultado: Any) -> ReporteOut:
    """Mapea un ``ResultadoReporte`` al modelo de salida."""
    return ReporteOut(
        id_reporte=resultado.id_reporte,
        id_jardin=resultado.id_jardin,
        periodo=resultado.periodo,
        metricas=resultado.metricas,
        resumen_ejecutivo=resultado.resumen_ejecutivo,
        resumen_disponible=resultado.resumen_disponible,
        fecha=resultado.fecha,
    )


def nivel_ruta_out(nivel: Any) -> NivelRutaOut:
    """Mapea un ``RutaNivel`` ORM a su modelo de salida."""
    return NivelRutaOut(
        nivel=nivel.nivel,
        nombre_nivel=nivel.nombre_nivel,
        edad_min_meses=nivel.edad_min_meses,
        edad_max_meses=nivel.edad_max_meses,
        dominios=list(nivel.dominios or []),
        descripcion=nivel.descripcion or "",
    )


def ruta_niveles_out(
    niveles: list[Any], version_rubrica: str | None
) -> RutaNivelesOut:
    """Compone la ruta de niveles de referencia + versión de rúbrica vigente."""
    ordenados = sorted(niveles, key=lambda n: n.nivel)
    return RutaNivelesOut(
        niveles=[nivel_ruta_out(n) for n in ordenados],
        version_rubrica=version_rubrica,
    )


__all__ = [
    "clasificacion_out",
    "observacion_de_resultado",
    "observacion_de_orm",
    "observacion_clasificada_de_orm",
    "nino_out",
    "ficha_nino_out",
    "bitacora_out",
    "recomendacion_out",
    "reporte_out",
    "nivel_ruta_out",
    "ruta_niveles_out",
]
