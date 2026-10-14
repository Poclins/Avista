# Design — jAImes MVP

## Overview

jAImes es un sistema full-stack de 3 capas que transforma evidencia cruda (texto/audio/foto/video) en observaciones estructuradas, bitácoras, recomendaciones de nivel y reportes de dirección. El backend (FastAPI, Python) concentra la lógica de negocio y expone una API REST; el frontend (React + Vite PWA) solo consume esa API. La IA se integra mediante **puertos y adaptadores** (interfaces + implementaciones AWS/mock), de modo que la demo corre sin AWS activando mocks.

Este diseño cubre los Requirements 1–11. El detalle visual del frontend se completará con los mockups de Figma; aquí se define la estructura, los contratos de API y los componentes.

## Architecture

### Capas (3-tier)

```
Capa 1 · Presentación      → Frontend React/Vite PWA (solo UI + llamadas REST)
Capa 2 · Lógica de negocio → FastAPI: routers (API) → services (casos de uso)
                             → domain (modelos POO) → providers (puertos IA)
Capa 3 · Acceso a datos    → repositories: relacional (Postgres), vectorial, storage
Infra externa              → AWS Transcribe/Textract/Rekognition/Bedrock/Titan/S3
                             (o mocks locales)
```

### Principios SOLID aplicados
- **SRP:** un servicio por caso de uso (transcribir, clasificar, embeber, bitácora, recomendación, reporte).
- **OCP:** nuevos proveedores de IA se agregan como adaptadores sin tocar los servicios.
- **LSP:** adaptadores AWS y mock son intercambiables tras la misma interfaz.
- **ISP:** interfaces pequeñas por capacidad (`TranscriptionProvider`, `LlmProvider`, `EmbeddingProvider`, repos).
- **DIP:** los servicios dependen de interfaces, inyectadas por un contenedor de DI simple leído de configuración.

### Selección de implementaciones
Un contenedor de dependencias en `core/` lee `USE_MOCKS` y construye los adaptadores correspondientes (AWS vs mock) y los repositorios (Postgres+pgvector vs SQLite+índice en memoria). Los routers reciben los servicios por `Depends()` de FastAPI.

## Components and Interfaces

### Domain models (`app/domain/models.py`)
`Jardin`, `Educadora`, `Nino`, `NivelRuta`, `Manifestacion`, `Observacion`, `Bitacora`, `Recomendacion`, `ReporteDireccion`. Enums: `FormatoCaptura {texto,audio,foto,video}`, `Dominio {cognitivo,lenguaje_comunicacion,motor_fino,motor_grueso,socioemocional}`, `DecisionNivel {AVANZAR,MANTENER,RETROCEDER}`, `EstadoBitacora {borrador,aprobada}`, `Rol {educadora,directora}`.

### Rúbrica (`app/domain/rubrica.py`)
`RubricaDecision` encapsula los criterios versionados y es puramente determinista:
```
evaluar(nino, observaciones_recientes, nivel_actual) -> ResultadoRubrica{
  decision, score, dominios_cubiertos[], dominios_pendientes[], evidencia[], version_rubrica
}
```
Criterios (configurables por versión, almacenados en `rubrica_versiones`):
- `n_observaciones_consistentes` (ventana N),
- `dominios_requeridos` (por defecto los 5),
- `umbral_score_avanzar`, `umbral_score_retroceder`,
- regla de retroceso: ≥K observaciones bajo el nivel asignado.

### Provider interfaces (`app/providers/*/base.py`)
```
TranscriptionProvider.transcribe(media_ref, formato) -> str
EmbeddingProvider.embed(text) -> list[float]
LlmProvider.generate(prompt, context) -> str
```
Adaptadores: `aws.py` (boto3) y `mock.py` por cada uno. Los mocks derivan salidas plausibles del dataset E-1.

### Repository interfaces (`app/repositories/*/base.py`)
- `RelationalRepo`: CRUD de todas las entidades + consultas agregadas para el reporte de dirección.
- `VectorRepo`: `index(doc)` y `search(query_embedding, filtros, k)`.
- `StorageRepo`: `put(file) -> ref`, `get_url(ref)`.

### Services (`app/services/`)
- `IngestionService`: orquesta carga → storage → transcripción → clasificación → persistencia → embedding.
- `TranscriptionService`: envuelve `TranscriptionProvider` según formato.
- `ClassificationService`: estima nivel/dominio y vincula manifestaciones; produce clasificación propuesta.
- `EmbeddingService`: embebe texto e indexa en `VectorRepo`.
- `BitacoraService` (Modelo 2): RAG (recupera evidencia) + `LlmProvider` → bitácora trazable.
- `RecommendationService` (Modelo 3): recupera evidencia → `RubricaDecision` (decide) → `LlmProvider` (argumenta) → persiste con `version_rubrica`.
- `DirectorReportService` (Modelo 4): agrega métricas vía `RelationalRepo` → `LlmProvider` (resumen ejecutivo).

### API (`app/api/routers/`) — contratos REST (JSON)
```
POST   /ninos/{id}/observaciones            # crear observación (multipart: medio o texto) → clasificación propuesta
PATCH  /observaciones/{id}/clasificacion    # confirmar/corregir clasificación
GET    /ninos/{id}/observaciones            # listar
GET    /ninos/{id}                          # ficha + trayectoria
GET    /ninos?sala=...                      # "Mi sala"
POST   /ninos/{id}/bitacoras                # generar bitácora quincenal (body: periodo)
GET    /ninos/{id}/bitacoras                # listar
PATCH  /bitacoras/{id}                      # editar / aprobar
POST   /ninos/{id}/recomendaciones          # generar recomendación de nivel
POST   /recomendaciones/{id}/decision       # registrar decisión de la educadora
GET    /jardines/{id}/reportes              # generar/obtener reporte de dirección (query: periodo)
GET    /ruta-niveles                        # rúbrica/ruta de referencia
```
Errores en español, con códigos HTTP apropiados (400 formato no soportado, 404 no encontrado, 422 validación).

### Frontend (`frontend/src/`)
PWA React + Vite. Capa de servicios API (`api/`) tipada; estado por pantalla; router por rol.
Pantallas (estructura; estilo pendiente de Figma):
- `MiSala` (educadora) — lista de niños/as con última observación.
- `Capturar` — selección de medio (grabar audio, foto, video, texto) con botón grande central.
- `ConfirmarClasificacion` — muestra clasificación propuesta; confirmar/corregir; sugerencia proactiva de avance.
- `FichaNino` — trayectoria por dominio + observaciones + botón "¿Puede subir de nivel?" con los 3 estados.
- `Bitacoras` — lista por estado; detalle editable; aprobar.
- `DashboardDireccion` (directora) — métricas agregadas + resumen ejecutivo + KPI.
- Componentes transversales: `SelectorRol`, `BannerDatosSinteticos`, `IndicadorCarga`.

## Data Models

### Base relacional (PostgreSQL / SQLite en demo)
Tablas del dataset E-1 (según diccionario de datos) + nuevas:
- `bitacoras(id_bitacora PK, id_nino FK, id_educadora FK, periodo, texto_generado, estado, fecha)`
- `recomendaciones(id_recomendacion PK, id_nino FK, id_educadora FK, decision, score, dominios_cubiertos, dominios_pendientes, argumento_ia, version_rubrica FK, decision_educadora, fecha)`
- `rubrica_versiones(version_rubrica PK, criterios JSON, vigente_desde, descripcion)`
- `reportes_direccion(id_reporte PK, id_jardin FK, periodo, metricas JSON, resumen_ejecutivo, fecha)`

Tipos y nulabilidad siguen el diccionario E-1 (fechas AAAA-MM-DD; `nota_breve` admite vacío; `edad_meses` derivada).

### Base vectorial (pgvector / índice en memoria en demo)
Documento por observación: `{id_observacion, id_nino, texto_transcrito, embedding[], dominio, nivel, fecha, formato}`. Índice por similitud coseno + filtros de metadatos.

## Error Handling
- Providers lanzan excepciones tipadas (`TranscriptionError`, `LlmError`, `EmbeddingError`); los servicios las traducen a respuestas HTTP con mensaje en español y no filtran detalles sensibles.
- IngestionService es idempotente respecto al archivo subido (reintentos no duplican observaciones).
- Fallos de IA en modo AWS degradan con mensaje claro; en modo mock no deberían ocurrir.
- Validación de entrada con Pydantic en los routers.

## Seguridad y privacidad
- `id_nino` seudónimo en todo el flujo; prompts al LLM sin PII.
- S3 cifrado + URLs prefirmadas (camino AWS); almacenamiento local aislado (mock).
- Separación física de datos personales (relacional) y contenido (vectorial).

## Testing Strategy
- **Unit:** `RubricaDecision` (determinismo y cada rama AVANZAR/MANTENER/RETROCEDER con fixtures del dataset E-1); mocks de providers.
- **Service:** flujo de ingesta end-to-end con mocks; generación de bitácora/recomendación/reporte con providers mock.
- **Contract/API:** tests de los endpoints con TestClient de FastAPI (códigos, forma de respuesta, validación).
- **Seed:** test que verifica que el dataset E-1 carga en ambas bases y que los conteos coinciden con `distribucion_y_validacion`.
- **Frontend:** smoke tests de render por pantalla y de la capa de servicios API (mock del backend).
- Pruebas priorizan modo mock (sin AWS) para CI y para la demo.

## Decisiones y notas
- **RAG, no fine-tuning:** la base vectorial alimenta el contexto del LLM; no se entrena ningún modelo.
- **La rúbrica decide, la IA argumenta, la educadora valida:** la decisión de nivel es determinista y auditable; el LLM solo redacta.
- **pgvector vs OpenSearch:** para la demo se usa pgvector (un solo motor); el diseño permite cambiar a OpenSearch cambiando el adaptador `VectorRepo`.
- **Figma:** las pantallas se refinarán al llegar los mockups; la estructura y los contratos de API no dependen del estilo visual.
