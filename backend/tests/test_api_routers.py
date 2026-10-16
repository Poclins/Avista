"""Tests de contrato de los routers REST (Módulo G, tarea 9.3).

Usan el ``TestClient`` de FastAPI con los servicios/repos **sobrescritos por
fakes** mediante ``app.dependency_overrides`` sobre las funciones proveedoras
del contenedor de DI. Así se verifica el cableado de los routers, la validación
Pydantic y la forma de las respuestas en total aislamiento de B/D/E/F
(Requirements 1.1, 3.3, 3.4, 5.7, 5.8, 6.1, 6.7, 7.1, 8.1).

Cada test construye su app con ``create_app()`` para no arrastrar overrides
entre casos; los fakes implementan solo la superficie que el router consume.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.container import (
    get_bitacora_service,
    get_classification_service,
    get_director_report_service,
    get_ingestion_service,
    get_recommendation_service,
    get_relational_repo,
)
from app.domain.contracts import ClasificacionPropuesta
from app.domain.models import DecisionNivel, Dominio, EstadoBitacora, FormatoCaptura
from app.main import create_app
from app.repositories.schema import (
    Bitacora as BitacoraORM,
    Nino as NinoORM,
    Observacion as ObservacionORM,
    Recomendacion as RecomendacionORM,
    RubricaVersion as RubricaVersionORM,
    RutaNivel as RutaNivelORM,
)
from app.services.bitacora_service import (
    BitacoraConflictoError,
    BitacoraNoEncontradaError,
    BitacoraSinEvidenciaError,
)
from app.services.director_report_service import (
    ResultadoReporte,
    ReporteRangoInvalidoError,
)
from app.services.errors import PersistenciaError
from app.services.ingestion_service import IngestionResult, IngestionValidationError
from app.services.recommendation_service import (
    RecommendationError,
    ResultadoRecomendacion,
)


# ---------------------------------------------------------------------------
# Fakes (implementan solo lo que el router consume)
# ---------------------------------------------------------------------------
class FakeIngestionService:
    def ingest(self, *, id_nino, id_educadora, formato, archivo=None, texto=None, fecha_observacion=None):
        if not id_nino or not id_educadora:
            raise IngestionValidationError(
                "Debe seleccionar un niño/a y una educadora de sesión."
            )
        clasificacion = ClasificacionPropuesta(
            nivel_estimado=3,
            dominios=[Dominio.socioemocional],
            manifestaciones=["m1"],
            confianza=0.9,
        )
        return IngestionResult(
            id_observacion="obs-1",
            id_nino=id_nino,
            id_educadora=id_educadora,
            fecha_observacion=fecha_observacion or date(2026, 1, 10),
            formato_captura=formato,
            texto=texto or "texto transcrito",
            media_ref=None,
            clasificacion=clasificacion,
            duplicado=False,
        )


class FakeClassificationService:
    def __init__(self) -> None:
        self.ultima = None

    def confirmar(self, id_observacion, propuesta):
        if id_observacion == "inexistente":
            raise PersistenciaError(
                f"No existe la observación '{id_observacion}'; "
                "no se persistió ninguna clasificación."
            )
        self.ultima = ("confirmar", id_observacion, propuesta)
        return ObservacionORM(
            id_observacion=id_observacion,
            id_nino="nino-1",
            id_educadora="edu-1",
            fecha_observacion=date(2026, 1, 10),
            formato_captura=FormatoCaptura.texto,
            nivel_estimado=propuesta.nivel_estimado,
            nota_breve="nota",
        )

    def corregir(self, id_observacion, *, nivel_estimado, dominios, manifestaciones):
        self.ultima = ("corregir", id_observacion, nivel_estimado)
        return ObservacionORM(
            id_observacion=id_observacion,
            id_nino="nino-1",
            id_educadora="edu-1",
            fecha_observacion=date(2026, 1, 10),
            formato_captura=FormatoCaptura.texto,
            nivel_estimado=nivel_estimado,
            nota_breve="nota",
        )


class FakeBitacoraService:
    def __init__(self) -> None:
        self.sin_evidencia = False
        self.conflicto = False
        self.no_encontrada = False

    def generar(self, *, id_nino, id_educadora, fecha_inicio, fecha_fin):
        if self.sin_evidencia:
            raise BitacoraSinEvidenciaError("No hay evidencia suficiente en el período.")
        return BitacoraORM(
            id_bitacora="bit-1",
            id_nino=id_nino,
            id_educadora=id_educadora,
            periodo=f"{fecha_inicio.isoformat()}/{fecha_fin.isoformat()}",
            texto_generado="Bitácora generada.",
            estado=EstadoBitacora.borrador,
            fecha=date(2026, 1, 15),
        )

    def editar(self, id_bitacora, nuevo_texto):
        if self.no_encontrada:
            raise BitacoraNoEncontradaError("No se encontró la bitácora.")
        if self.conflicto:
            raise BitacoraConflictoError("La bitácora ya está aprobada.")
        return BitacoraORM(
            id_bitacora=id_bitacora,
            id_nino="nino-1",
            id_educadora="edu-1",
            periodo="2026-01-01/2026-01-15",
            texto_generado=nuevo_texto,
            estado=EstadoBitacora.borrador,
            fecha=date(2026, 1, 15),
        )

    def aprobar(self, id_bitacora):
        return BitacoraORM(
            id_bitacora=id_bitacora,
            id_nino="nino-1",
            id_educadora="edu-1",
            periodo="2026-01-01/2026-01-15",
            texto_generado="Bitácora aprobada.",
            estado=EstadoBitacora.aprobada,
            fecha=date(2026, 1, 15),
        )


class FakeRecommendationService:
    def __init__(self) -> None:
        self.insuficiente = False
        self.no_existe = False

    def recomendar(self, *, id_nino, id_educadora, nivel_actual, nucleo):
        if self.no_existe:
            raise RecommendationError(f"No se encontró el niño/a con id_nino={id_nino!r}.")
        if self.insuficiente:
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
                argumento_ia="Datos insuficientes.",
                argumento_disponible=False,
                datos_insuficientes=True,
                observaciones_registradas=2,
                observaciones_faltantes=3,
                persistida=False,
            )
        return ResultadoRecomendacion(
            id_recomendacion="rec-1",
            id_nino=id_nino,
            id_educadora=id_educadora,
            decision=DecisionNivel.AVANZAR,
            tramo="Nivel Medio",
            nucleo=nucleo,
            nivel_actual=nivel_actual,
            score=0.85,
            conductas_observables_cubiertas=["c1", "c2"],
            conductas_observables_pendientes=["c3"],
            evidencia=["obs-1", "obs-2"],
            version_rubrica="v1",
            argumento_ia="La rúbrica decidió avanzar.",
            argumento_disponible=True,
            datos_insuficientes=False,
            observaciones_registradas=6,
            observaciones_faltantes=0,
            persistida=True,
        )

    def registrar_decision_educadora(self, id_recomendacion, decision_educadora):
        return RecomendacionORM(
            id_recomendacion=id_recomendacion,
            id_nino="nino-1",
            id_educadora="edu-1",
            decision=DecisionNivel.AVANZAR,
            score=0.85,
            dominios_cubiertos=[],
            dominios_pendientes=[],
            argumento_ia="",
            version_rubrica="v1",
            decision_educadora="aceptó",
            fecha=date(2026, 1, 16),
        )


class FakeDirectorReportService:
    def __init__(self) -> None:
        self.rango_invalido = False

    def generar(self, *, id_jardin, fecha_inicio, fecha_fin):
        if self.rango_invalido:
            raise ReporteRangoInvalidoError("El rango de fechas es inválido.")
        return ResultadoReporte(
            id_reporte="rep-1",
            id_jardin=id_jardin,
            periodo=f"{fecha_inicio.isoformat()}/{fecha_fin.isoformat()}",
            metricas={"observaciones": {"total": 0}},
            resumen_ejecutivo="Resumen.",
            resumen_disponible=True,
            fecha=date(2026, 1, 20),
        )


class FakeRelationalRepo:
    def __init__(self) -> None:
        self._ninos = {
            "nino-1": NinoORM(
                id_nino="nino-1",
                id_jardin="jar-1",
                fecha_nacimiento=date(2023, 5, 1),
                sexo_registrado="F",
                sala_grupo="sala-a",
                fecha_ingreso=date(2024, 3, 1),
            )
        }
        self._observaciones = [
            ObservacionORM(
                id_observacion="obs-1",
                id_nino="nino-1",
                id_educadora="edu-1",
                fecha_observacion=date(2026, 1, 5),
                formato_captura=FormatoCaptura.texto,
                nivel_estimado=3,
                nota_breve="juega en grupo",
            )
        ]
        self._bitacoras = [
            BitacoraORM(
                id_bitacora="bit-1",
                id_nino="nino-1",
                id_educadora="edu-1",
                periodo="2026-01-01/2026-01-15",
                texto_generado="texto",
                estado=EstadoBitacora.borrador,
                fecha=date(2026, 1, 15),
            )
        ]
        self._niveles = [
            RutaNivelORM(
                nivel=2,
                nombre_nivel="Nivel 2",
                edad_min_meses=12,
                edad_max_meses=24,
                dominios=[Dominio.socioemocional.value],
                descripcion="desc 2",
            ),
            RutaNivelORM(
                nivel=1,
                nombre_nivel="Nivel 1",
                edad_min_meses=0,
                edad_max_meses=12,
                dominios=[],
                descripcion="desc 1",
            ),
        ]
        self._rubrica = RubricaVersionORM(
            version_rubrica="v1",
            criterios={},
            vigente_desde=date(2026, 1, 1),
            descripcion="rúbrica oficial",
        )

    def get(self, model, pk):
        if model is NinoORM:
            return self._ninos.get(pk)
        return None

    def observaciones_de_nino(self, id_nino):
        return [o for o in self._observaciones if o.id_nino == id_nino]

    def bitacoras_de_nino(self, id_nino):
        return [b for b in self._bitacoras if b.id_nino == id_nino]

    def ninos_por_sala(self, id_jardin, sala_grupo):
        return [
            n
            for n in self._ninos.values()
            if n.id_jardin == id_jardin and n.sala_grupo == sala_grupo
        ]

    def list(self, model, **filters):
        if model is RutaNivelORM:
            return list(self._niveles)
        return []

    def rubrica_vigente(self):
        return self._rubrica


# ---------------------------------------------------------------------------
# Fixture: app con overrides configurables
# ---------------------------------------------------------------------------
@pytest.fixture
def ctx():
    app = create_app()
    fakes = {
        "ingestion": FakeIngestionService(),
        "classification": FakeClassificationService(),
        "bitacora": FakeBitacoraService(),
        "recommendation": FakeRecommendationService(),
        "report": FakeDirectorReportService(),
        "repo": FakeRelationalRepo(),
    }
    app.dependency_overrides[get_ingestion_service] = lambda: fakes["ingestion"]
    app.dependency_overrides[get_classification_service] = lambda: fakes["classification"]
    app.dependency_overrides[get_bitacora_service] = lambda: fakes["bitacora"]
    app.dependency_overrides[get_recommendation_service] = lambda: fakes["recommendation"]
    app.dependency_overrides[get_director_report_service] = lambda: fakes["report"]
    app.dependency_overrides[get_relational_repo] = lambda: fakes["repo"]
    client = TestClient(app)
    yield client, fakes
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def test_health_responde_ok(ctx):
    client, _ = ctx
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "jAImes"
    assert "use_mocks" in body


# ---------------------------------------------------------------------------
# Observaciones
# ---------------------------------------------------------------------------
def test_crear_observacion_texto_multipart(ctx):
    client, _ = ctx
    r = client.post(
        "/ninos/nino-1/observaciones",
        data={"id_educadora": "edu-1", "formato": "texto", "texto": "juega"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id_observacion"] == "obs-1"
    assert body["clasificacion"]["nivel_estimado"] == 3
    assert body["duplicado"] is False


def test_crear_observacion_multipart_sin_formato_es_422(ctx):
    client, _ = ctx
    r = client.post("/ninos/nino-1/observaciones", data={"id_educadora": "edu-1"})
    assert r.status_code == 422


def test_crear_observacion_foto_sin_archivo_es_422(ctx):
    client, _ = ctx
    r = client.post(
        "/ninos/nino-1/observaciones",
        data={"id_educadora": "edu-1", "formato": "foto"},
    )
    assert r.status_code == 422


def test_crear_observacion_con_archivo(ctx):
    client, _ = ctx
    r = client.post(
        "/ninos/nino-1/observaciones",
        data={"id_educadora": "edu-1", "formato": "audio"},
        files={"archivo": ("nota.mp3", b"bytes-de-audio", "audio/mpeg")},
    )
    assert r.status_code == 201
    assert r.json()["formato_captura"] == "audio"


def test_listar_observaciones(ctx):
    client, _ = ctx
    r = client.get("/ninos/nino-1/observaciones")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["id_observacion"] == "obs-1"


def test_listar_observaciones_nino_inexistente_es_404(ctx):
    client, _ = ctx
    r = client.get("/ninos/fantasma/observaciones")
    assert r.status_code == 404


def test_patch_clasificacion_confirmar(ctx):
    client, fakes = ctx
    r = client.patch(
        "/observaciones/obs-1/clasificacion",
        json={
            "accion": "confirmar",
            "nivel_estimado": 4,
            "dominios": ["cognitivo"],
            "manifestaciones": ["m2"],
        },
    )
    assert r.status_code == 200
    assert r.json()["nivel_estimado"] == 4
    assert fakes["classification"].ultima[0] == "confirmar"


def test_patch_clasificacion_corregir(ctx):
    client, fakes = ctx
    r = client.patch(
        "/observaciones/obs-1/clasificacion",
        json={"accion": "corregir", "nivel_estimado": 5, "dominios": [], "manifestaciones": []},
    )
    assert r.status_code == 200
    assert fakes["classification"].ultima[0] == "corregir"


def test_patch_clasificacion_accion_invalida_es_422(ctx):
    client, _ = ctx
    r = client.patch(
        "/observaciones/obs-1/clasificacion",
        json={"accion": "borrar"},
    )
    assert r.status_code == 422


def test_patch_clasificacion_observacion_inexistente_es_404(ctx):
    client, _ = ctx
    r = client.patch(
        "/observaciones/inexistente/clasificacion",
        json={"accion": "confirmar", "nivel_estimado": 3, "dominios": ["cognitivo"], "manifestaciones": ["m1"]},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Niños/as
# ---------------------------------------------------------------------------
def test_ficha_nino(ctx):
    client, _ = ctx
    r = client.get("/ninos/nino-1")
    assert r.status_code == 200
    body = r.json()
    assert body["nino"]["id_nino"] == "nino-1"
    assert len(body["trayectoria"]) == 1


def test_ficha_nino_inexistente_es_404(ctx):
    client, _ = ctx
    r = client.get("/ninos/fantasma")
    assert r.status_code == 404


def test_mi_sala(ctx):
    client, _ = ctx
    r = client.get("/ninos", params={"jardin": "jar-1", "sala": "sala-a"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["sala_grupo"] == "sala-a"


def test_mi_sala_sin_params_es_422(ctx):
    client, _ = ctx
    r = client.get("/ninos")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Bitácoras
# ---------------------------------------------------------------------------
def test_generar_bitacora(ctx):
    client, _ = ctx
    r = client.post(
        "/ninos/nino-1/bitacoras",
        json={"id_educadora": "edu-1", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-15"},
    )
    assert r.status_code == 201
    assert r.json()["estado"] == "borrador"


def test_generar_bitacora_rango_invalido_es_422(ctx):
    client, _ = ctx
    r = client.post(
        "/ninos/nino-1/bitacoras",
        json={"id_educadora": "edu-1", "fecha_inicio": "2026-01-20", "fecha_fin": "2026-01-01"},
    )
    assert r.status_code == 422


def test_generar_bitacora_sin_evidencia_es_422(ctx):
    client, fakes = ctx
    fakes["bitacora"].sin_evidencia = True
    r = client.post(
        "/ninos/nino-1/bitacoras",
        json={"id_educadora": "edu-1", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-15"},
    )
    assert r.status_code == 422


def test_listar_bitacoras(ctx):
    client, _ = ctx
    r = client.get("/ninos/nino-1/bitacoras")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_patch_bitacora_editar(ctx):
    client, _ = ctx
    r = client.patch("/bitacoras/bit-1", json={"accion": "editar", "texto": "nuevo texto"})
    assert r.status_code == 200
    assert r.json()["texto_generado"] == "nuevo texto"


def test_patch_bitacora_editar_sin_texto_es_422(ctx):
    client, _ = ctx
    r = client.patch("/bitacoras/bit-1", json={"accion": "editar"})
    assert r.status_code == 422


def test_patch_bitacora_aprobar(ctx):
    client, _ = ctx
    r = client.patch("/bitacoras/bit-1", json={"accion": "aprobar"})
    assert r.status_code == 200
    assert r.json()["estado"] == "aprobada"


def test_patch_bitacora_editar_aprobada_es_409(ctx):
    client, fakes = ctx
    fakes["bitacora"].conflicto = True
    r = client.patch("/bitacoras/bit-1", json={"accion": "editar", "texto": "x"})
    assert r.status_code == 409


def test_patch_bitacora_no_encontrada_es_404(ctx):
    client, fakes = ctx
    fakes["bitacora"].no_encontrada = True
    r = client.patch("/bitacoras/fantasma", json={"accion": "editar", "texto": "x"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Recomendaciones
# ---------------------------------------------------------------------------
def test_generar_recomendacion(ctx):
    client, _ = ctx
    r = client.post(
        "/ninos/nino-1/recomendaciones",
        json={"id_educadora": "edu-1", "nivel_actual": 3},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["decision"] == "AVANZAR"
    assert body["version_rubrica"] == "v1"
    assert body["persistida"] is True


def test_generar_recomendacion_datos_insuficientes(ctx):
    client, fakes = ctx
    fakes["recommendation"].insuficiente = True
    r = client.post(
        "/ninos/nino-1/recomendaciones",
        json={"id_educadora": "edu-1", "nivel_actual": 3},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["datos_insuficientes"] is True
    assert body["decision"] is None
    assert body["observaciones_faltantes"] == 3


def test_generar_recomendacion_nino_inexistente_es_404(ctx):
    client, fakes = ctx
    fakes["recommendation"].no_existe = True
    r = client.post(
        "/ninos/fantasma/recomendaciones",
        json={"id_educadora": "edu-1", "nivel_actual": 3},
    )
    assert r.status_code == 404


def test_generar_recomendacion_nivel_fuera_rango_es_422(ctx):
    client, _ = ctx
    r = client.post(
        "/ninos/nino-1/recomendaciones",
        json={"id_educadora": "edu-1", "nivel_actual": 99},
    )
    assert r.status_code == 422


def test_registrar_decision_educadora(ctx):
    client, _ = ctx
    r = client.post(
        "/recomendaciones/rec-1/decision",
        json={"decision_educadora": "aceptó"},
    )
    assert r.status_code == 200
    assert r.json()["decision_educadora"] == "aceptó"


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------
def test_reporte_direccion(ctx):
    client, _ = ctx
    r = client.get(
        "/jardines/jar-1/reportes",
        params={"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id_jardin"] == "jar-1"
    assert body["resumen_disponible"] is True


def test_reporte_rango_invalido_es_422(ctx):
    client, fakes = ctx
    fakes["report"].rango_invalido = True
    r = client.get(
        "/jardines/jar-1/reportes",
        params={"fecha_inicio": "2026-02-01", "fecha_fin": "2026-01-01"},
    )
    assert r.status_code == 422


def test_reporte_sin_fechas_es_422(ctx):
    client, _ = ctx
    r = client.get("/jardines/jar-1/reportes")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Ruta de niveles
# ---------------------------------------------------------------------------
def test_ruta_niveles(ctx):
    client, _ = ctx
    r = client.get("/ruta-niveles")
    assert r.status_code == 200
    body = r.json()
    assert body["version_rubrica"] == "v1"
    # Debe venir ordenada por nivel ascendente.
    assert [n["nivel"] for n in body["niveles"]] == [1, 2]
