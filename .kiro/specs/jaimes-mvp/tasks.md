# Implementation Plan â€” jAImes MVP

## Overview

Este plan estÃ¡ organizado para que un equipo de **4 personas trabaje en paralelo con mÃ¡xima independencia**. La estrategia es **interface-first**: primero se congela el **MÃ³dulo A (dominio + contratos)** como Ãºnica fuente de verdad; una vez congelado, los mÃ³dulos **Bâ€“H** dependen **solo de las interfaces de A** (nunca de la implementaciÃ³n concreta de otro mÃ³dulo), por lo que pueden implementarse, probarse y mergearse a `main` de forma aislada.

Principios de ejecuciÃ³n:

- **Cada mÃ³dulo es implementable y verificable en aislamiento.** Todo cruce de mÃ³dulo pasa por una interfaz (`providers/*/base.py`, `repositories/*/base.py`) y cada mÃ³dulo trae su propio **fake/mock** para no bloquearse esperando a otro.
- **AWS es el camino primario.** Los adaptadores reales (Bedrock Claude+Titan, Transcribe, Textract, Rekognition, S3, Aurora Serverless v2 + pgvector) son la implementaciÃ³n principal; los mocks son el camino secundario/local tras las mismas interfaces, seleccionados por `USE_MOCKS`.
- **Tests por mÃ³dulo (requeridos) + sondas opcionales.** Cada mÃ³dulo tiene subtareas de test que corren en aislamiento con fakes/mocks y "gatean" el mÃ³dulo. AdemÃ¡s hay subtareas de sonda marcadas `_Optional_` para que un desarrollador verifique rÃ¡pido el mÃ³dulo end-to-end dentro de su propia frontera.
- **Docs por mÃ³dulo.** Cada mÃ³dulo produce o actualiza su propia documentaciÃ³n en `docs/` (backend, database, cloud, frontend) con diagramas Mermaid, para que la documentaciÃ³n no quede dispersa.
- **Frontend es una tarea posterior**, construida desde los mockups de Figma; no bloquea los mÃ³dulos de backend.
- **IntegraciÃ³n final (E2E)** va al final: solo cablea implementaciones reales vÃ­a el contenedor DI y prueba el cruce entre mÃ³dulos, sin romper la independencia de los mÃ³dulos previos.

Estado actual: las tareas **1 (bootstrap), 2 (MÃ³dulo A) y 3.1â€“3.3 (MÃ³dulo B: esquema + `RelationalRepo` + seed inicial E-1)** ya estÃ¡n implementadas y marcadas `[x]`. El cierre del MÃ³dulo B migra el seed al **Dataset E-1 oficial** (3.7â€“3.11) y el resto estÃ¡ sin iniciar. Al final del plan se aÃ±ade un bloque transversal de **atributos de calidad** (tarea 17, pilares de evaluaciÃ³n) y una **matriz legible de dependencias entre mÃ³dulos** (independiente vs integraciÃ³n) en la secciÃ³n *Task Dependency Graph*.

## Tasks

<!-- ============================================================= -->
<!-- BOOTSTRAP Â· Estructura y configuraciÃ³n base (COMPLETADO)       -->
<!-- ============================================================= -->

- [x] 1. Preparar estructura del proyecto y configuraciÃ³n base
  - Crear estructura `backend/app/{api,services,domain,providers,repositories,core}` y `frontend/`.
  - Configurar `pyproject`/requirements (FastAPI, pydantic, boto3, sqlalchemy, pgvector, uvicorn, mangum), `.env.example` con `USE_MOCKS`, y settings en `core/`.
  - AÃ±adir `docker-compose` (backend + Postgres/pgvector) y README inicial con pasos de ejecuciÃ³n.
  - _Requirements: 10.9, 13.1_

<!-- ============================================================= -->
<!-- MÃ“DULO A Â· Dominio y modelos (base compartida) â€” CONGELAR 1Âº   -->
<!-- Responsable: lÃ­der / compartido. Depende de: nada.            -->
<!-- Debe congelarse antes de que Bâ€“H empiecen.                    -->
<!-- ============================================================= -->

- [x] 2. MÃ³dulo A â€” Definir modelos de dominio, enums y contratos compartidos
  - Implementar `domain/models.py` con las entidades (`Jardin`, `Educadora`, `Nino`, `NivelRuta`, `Manifestacion`, `Observacion`, `Bitacora`, `Recomendacion`, `ReporteDireccion`) y enums (`FormatoCaptura`, `Dominio`, `DecisionNivel`, `EstadoBitacora`, `Rol`), todos en Pydantic v2, usando solo `id_nino` seudÃ³nimo (sin nombre real ni RUT).
  - Escribir tests unitarios de construcciÃ³n/validaciÃ³n de los modelos y enums.
  - _Requirements: 1.4, 1.5, 3.1, 4.1, 8.1, 11.1, 13.3_

- [x] 2.1 MÃ³dulo A â€” Alinear/congelar las interfaces de puertos y repos para el nuevo diseÃ±o
  - Declarar las interfaces base que consumirÃ¡n Bâ€“H: `providers/transcription/base.py` (`TranscriptionProvider`), `providers/embeddings/base.py` (`EmbeddingProvider`), `providers/llm/base.py` (`LlmProvider`), `providers/classifier/base.py` (`Classifier`); `repositories/relational/base.py` (`RelationalRepo`), `repositories/vector/base.py` (`VectorRepo`), `repositories/storage/base.py` (`StorageRepo`).
  - Definir los tipos de retorno compartidos (`ClasificacionPropuesta`, `ResultadoRubrica`) y excepciones tipadas (`TranscriptionError`, `LlmError`, `EmbeddingError`).
  - Publicar como contrato estable: una vez acordado, no cambia de forma incompatible mientras Bâ€“H estÃ©n en desarrollo.
  - _Requirements: 13.1, 13.2, 13.3_

- [ ]* 2.2 MÃ³dulo A â€” Sonda de contratos (opcional)
  - _Optional_ â€” prueba de humo que importa todas las interfaces y construye cada modelo con datos del dataset E-1 para confirmar que los contratos son coherentes antes de que arranquen los demÃ¡s mÃ³dulos.
  - _Requirements: 13.3_

<!-- ============================================================= -->
<!-- MÃ“DULO B Â· Relacional + seed â€” Dev 1. Depende de: A.          -->
<!-- NÃºcleo COMPLETADO.                                            -->
<!-- ============================================================= -->

- [x] 3. MÃ³dulo B â€” Esquema relacional, RelationalRepo y seed del dataset E-1 **[independiente]**
- [x] 3.1 Crear el esquema SQLAlchemy de las tablas E-1 + nuevas (`bitacoras`, `recomendaciones`, `rubrica_versiones`, `reportes_direccion`)
  - Mapear tipos y nulabilidad segÃºn el diccionario de datos E-1.
  - _Requirements: 4.1_
- [x] 3.2 Implementar `RelationalRepo` (interfaz + implementaciÃ³n Postgres/SQLite) con CRUD y consultas base
  - _Requirements: 4.7, 13.2_
- [x] 3.3 Escribir el script de seed que carga el dataset E-1 y un test que valida conteos contra `distribucion_y_validacion`
  - _Requirements: 10.8, 11.5_
- [ ] 3.4 MÃ³dulo B â€” AÃ±adir consultas agregadas para el reporte de direcciÃ³n a `RelationalRepo`
  - Implementar consultas que el MÃ³dulo G consumirÃ¡ vÃ­a interfaz: conteos subieron/mantuvieron/bajaron por sala, distribuciÃ³n por nivel y dominio, conteo de observaciones/bitÃ¡coras total y por educadora, alertas de retroceso y de inactividad (14 dÃ­as).
  - _Requirements: 7.1, 7.3, 7.8_
- [x] 3.5 MÃ³dulo B â€” Tests de consultas agregadas con SQLite + dataset sembrado
  - Verificar cada agregaciÃ³n contra fixtures del seed; aislamiento total (sin otros mÃ³dulos).
  - _Requirements: 7.1, 7.3_
- [ ]* 3.6 MÃ³dulo B â€” DocumentaciÃ³n `docs/database/`
  - _Optional_ â€” escribir `docs/database/esquema.md` + `docs/database/README.md` (diccionario E-1 + tablas nuevas) con un diagrama ER en bloque ```mermaid```.
  - _Requirements: 12.4, 12.6_
- [x] 3.7 Módulo B — Implementar `DatasetLoader` del Dataset E-1 **oficial** (7 CSV + `consolidado.json`)
  - Leer los **siete CSV relacionales oficiales** (`jardines`, `educadoras`, `ninos`, `ruta_niveles`, `manifestaciones`, `observaciones`, `observacion_manifestaciones`) más `consolidado.json`; mapear cada fila a las entidades ORM del dominio (Módulo A) con `read_csvs()`, `read_consolidado()`, `to_entities()`.
  - Mantener `DatasetLoader` **encapsulado detrás de la frontera del seed** (`RelationalRepo`/`VectorRepo`), de modo que cambiar de dataset (oficial ↔ reducido casero) **no toque el código de los servicios**.
  - _Requirements: 10.8, 14.1_
- [x] 3.8 Módulo B — Adaptar el seed para cargar vía `DatasetLoader` (oficial E-1, 500 niños) y validar conteos
  - Sustituir la carga "un JSON por tabla" por la lectura del **zip público** `dataset_e1_publico.zip`; validar los conteos cargados contra `distribucion_y_validacion` y **rechazar con error en español** si algún conteo no coincide.
  - _Requirements: 10.8, 10.9, 14.1, 14.2_
- [x] 3.9 Módulo B — Verificación de reproducibilidad del Dataset E-1 oficial
  - Re-ejecutar `generador.py` con **semilla `20261013`** y **fecha de referencia `2026-10-13`** (Python 3.12.15, solo biblioteca estándar) y confirmar salida **idéntica bit a bit** / **hashes publicados coincidentes**, y que `validador.py` finaliza **sin errores**.
  - _Requirements: 10.10, 14.5_
- [ ]* 3.10 MÃ³dulo B â€” Test de carga completa del dataset oficial (500 niÃ±os) y ruta de abstenciÃ³n
  - _Optional_ â€” verificar que la carga procesa **sin error** a los 500 niÃ±os/as, incluidos los **60 con 1â€“2 observaciones** (ingreso reciente), y que los niÃ±os con **<5 observaciones** disparan la ruta de **abstenciÃ³n** del `RecommendationService` (datos insuficientes), sin interrumpir el procesamiento del resto; tratar nota/formato/manifestaciÃ³n ausente como ausencia de registro, no como dato invÃ¡lido.
  - _Requirements: 14.2, 14.3, 14.4_
- [ ]* 3.11 MÃ³dulo B â€” Resguardo de distribuciÃ³n del dataset (solo zip pÃºblico)
  - _Optional_ â€” asegurar (p. ej. test/chequeo de `.gitignore`) que **solo** `dataset_e1_publico.zip` se usa y versiona, que el **zip interno de validaciÃ³n NO** se incluye en el repositorio ni en los entregables, y que el dataset reducido/casero queda **solo como respaldo rÃ¡pido de pruebas**, nunca como fuente de verdad.
  - _Requirements: 14.7, 10.11_

<!-- ============================================================= -->
<!-- MÃ“DULO C Â· Vectorial + embeddings â€” Dev 2. Depende de: A.     -->
<!-- ============================================================= -->

- [x] 4. Módulo C — Base vectorial y proveedor de embeddings (AWS primario) **[independiente]**
- [x] 4.1 Implementar `EmbeddingProvider`: adaptador **Titan (AWS, primario)** + adaptador mock (secundario)
  - `titan_embeddings.py` invoca Amazon Titan vía Bedrock; `mock_embeddings.py` deriva vectores deterministas del texto para CI/local. Selección por `USE_MOCKS`.
  - _Requirements: 4.2, 4.5_
- [x] 4.2 Implementar `VectorRepo`: implementación **pgvector sobre Aurora (primaria)** + índice en memoria (secundaria)
  - `index(doc)` y `search(query_embedding, filtros, k)` con similitud coseno (`<=>`), metadatos `id_observacion, id_nino, dominio, nivel, fecha, formato`.
  - _Requirements: 4.3, 4.6, 4.7, 11.5_
- [x] 4.3 Implementar `EmbeddingService` (embeber texto e indexar) con manejo de fallo de indexación
  - Si falla el embedding o la indexación, conservar la observación relacional sin registro vectorial y devolver error de indexación no completada.
  - _Requirements: 4.2, 4.4_
- [ ]* 4.4 MÃ³dulo C â€” Tests de aislamiento con mock embeddings + Ã­ndice en memoria
  - Verificar que `search(id_observacion)` recupera exactamente un registro con los seis metadatos; intercambiabilidad de adaptadores.
  - _Requirements: 4.3, 4.5_
- [ ]* 4.5 MÃ³dulo C â€” Sonda del mÃ³dulo (opcional)
  - _Optional_ â€” script que embebe N observaciones del dataset E-1 (modo mock) e imprime los vecinos mÃ¡s cercanos, para probar el mÃ³dulo end-to-end dentro de su frontera.
  - _Requirements: 4.2, 4.3_
- [ ]* 4.6 MÃ³dulo C â€” DocumentaciÃ³n `docs/database/vectorial.md`
  - _Optional_ â€” documentar el documento-por-observaciÃ³n, pgvector y la bÃºsqueda semÃ¡ntica, con un diagrama ```mermaid```.
  - _Requirements: 12.4, 12.6_

<!-- ============================================================= -->
<!-- MÃ“DULO D Â· Ingesta + transcripciÃ³n â€” Dev 2/3. Depende de: A.  -->
<!-- ============================================================= -->

- [x] 5. MÃ³dulo D â€” Storage, transcripciÃ³n (Modelo 1) e ingesta (AWS primario) **[independiente]**
- [x] 5.1 Implementar `StorageRepo`: **S3 (AWS, primario)** + almacenamiento local (secundario)
  - `put(file) -> ref`, `get_url(ref)`; en AWS, cifrado en reposo y URLs prefirmadas de â‰¤300 s.
  - _Requirements: 1.2, 11.4_
- [x] 5.2 Implementar `TranscriptionProvider`: adaptador **AWS (Transcribe/Textract/Rekognition, primario)** + mock (secundario)
  - Enrutar por formato: audio/video â†’ Transcribe (es-CL), foto â†’ Textract (OCR), video â†’ tambiÃ©n metadatos de escena Rekognition. Reintentos â‰¤3 y marca de "pendiente de transcripciÃ³n" si persiste el fallo.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 2.8_
- [x] 5.3 Implementar `TranscriptionService` que valida formato/tamaÃ±o y enruta por `formato_captura`
  - Texto directo 1â€“50.000 chars sin transcripciÃ³n; validar lÃ­mites de tamaÃ±o (100 MB general, 10 MB foto, 500 MB video); errores en espaÃ±ol.
  - _Requirements: 1.4, 2.5, 2.6_
- [x] 5.4 Implementar `IngestionService` idempotente (orquesta dentro del mÃ³dulo con fakes de E y repos)
  - Flujo: `StorageRepo` â†’ `TranscriptionProvider` â†’ (interfaz `Classifier`) â†’ persistencia (interfaz `RelationalRepo`) â†’ embedding (interfaz `EmbeddingService`). Subir el mismo archivo dos veces no crea dos observaciones.
  - _Requirements: 1.1, 1.3, 1.5_
- [ ]* 5.5 MÃ³dulo D â€” Tests por formato en modo mock (texto/audio/foto/video) + idempotencia
  - Usar fakes para `Classifier`, `RelationalRepo`, `EmbeddingService`; sin importar implementaciones hermanas.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 1.1_
- [ ]* 5.6 MÃ³dulo D â€” Sonda del mÃ³dulo (opcional)
  - _Optional_ â€” script que ingesta un archivo de ejemplo de cada formato en modo mock y muestra la observaciÃ³n creada.
  - _Requirements: 1.1, 2.5_

<!-- ============================================================= -->
<!-- MÃ“DULO E Â· ClasificaciÃ³n â€” Dev 3. Depende de: A.              -->
<!-- ============================================================= -->

- [x] 6. Módulo E — Clasificación de observaciones **[independiente]**
- [x] 6.1 Implementar `Classifier` (adaptador basado en reglas/LLM) que estima `nivel_estimado` (1–9) y 1–5 dominios
  - Vincular 1–10 manifestaciones cuyo nivel = `nivel_estimado` y dominio ∈ dominios estimados; marcar baja confianza como "pendiente de clasificación manual".
  - _Requirements: 3.1, 3.2, 3.5_
- [x] 6.2 Implementar `ClassificationService`: devolver clasificación **propuesta** y soportar confirmación/corrección persistente
  - No persistir hasta que la educadora confirme/corrija; persistir vía interfaz `RelationalRepo`; conservar valores previos ante fallo de persistencia.
  - _Requirements: 3.3, 3.4, 3.6_
- [ ]* 6.3 MÃ³dulo E â€” Tests de clasificaciÃ³n y de vÃ­nculo con manifestaciones (fixtures E-1)
  - Aislamiento con fake de `RelationalRepo`.
  - _Requirements: 3.1, 3.2, 3.5_
- [ ]* 6.4 MÃ³dulo E â€” Sonda del mÃ³dulo (opcional)
  - _Optional_ â€” script que clasifica textos de ejemplo del dataset E-1 e imprime nivel/dominios/manifestaciones propuestas.
  - _Requirements: 3.1_

<!-- ============================================================= -->
<!-- MÃ“DULO F Â· BitÃ¡coras RAG+LLM + RÃºbrica + RecomendaciÃ³n         -->
<!-- Dev 3/4. Depende de: A, interfaces de B y C.                 -->
<!-- ============================================================= -->

- [~] 7. MÃ³dulo F â€” Proveedor LLM, bitÃ¡coras, rÃºbrica y recomendaciÃ³n **[independiente]** (consume interfaces de B/C vÃ­a fakes)
- [x] 7.1 Implementar `LlmProvider`: adaptador **Bedrock Claude (AWS, primario)** + mock (secundario)
  - SelecciÃ³n por `USE_MOCKS`; excepciÃ³n tipada `LlmError`.
  - _Requirements: 5.3, 5.10_
- [x] 7.2 Implementar `domain/rubrica.py` (`RubricaDecision`) **puramente determinista** que consume la **rÃºbrica oficial** desde `rubrica_versiones.criterios` (estructura tramo de sala Ã— nÃºcleo Ã— 8 niveles de progresiÃ³n Ã— conductas observables + descriptor + umbrales)
  - Derivar el **tramo de sala** (Sala Cuna / Nivel Medio / TransiciÃ³n) del rango etario del niÃ±o/a; mapear la **evidencia previa** del niÃ±o/a a las **conductas observables** del tramoÃ—nÃºcleoÃ—nivel actual (conducta **cubierta** si hay evidencia que la respalda, **pendiente** si no â€” sin inferir cumplimiento donde no hay evidencia).
  - Ramas de decisiÃ³n sobre la cobertura de conductas observables: **AVANZAR** si la fracciÃ³n cubierta â‰¥ umbral en los nÃºcleos requeridos, **MANTENER** si la cobertura es parcial, **RETROCEDER** si hay racha â‰¥3 por debajo del nivel. Devolver `tramo, nucleo, nivel_actual, decision, score, conductas_observables_cubiertas, conductas_observables_pendientes, evidencia, version_rubrica`.
  - _Requirements: 6.2, 6.3, 6.4, 6.5, 21.3, 21.6_
- [x] 7.2b Transcribir la rÃºbrica oficial (PDF) a la estructura JSON versionada de `rubrica_versiones.criterios`
  - Transcribir la **rÃºbrica oficial** (PDF entregado: nÃºcleo **Identidad y AutonomÃ­a** para **Sala Cuna, Nivel Medio y TransiciÃ³n**; 8 niveles de progresiÃ³n con descriptor y conductas observables) a la estructura JSON versionada de `rubrica_versiones.criterios`.
  - Capturar las **conductas observables verbatim** por tramoÃ—nivel para el nÃºcleo Identidad y AutonomÃ­a en los 3 tramos; dejar el esquema **listo para agregar mÃ¡s nÃºcleos como datos versionados** sin cambios de cÃ³digo.
  - _Requirements: 21.1, 21.2, 21.5_
- [x] 7.3 Sembrar la **versiÃ³n inicial de la rÃºbrica oficial** en `rubrica_versiones` (vÃ­a interfaz `RelationalRepo`)
  - Sembrar al menos el nÃºcleo **Identidad y AutonomÃ­a** para los 3 tramos (Sala Cuna, Nivel Medio, TransiciÃ³n), con sus **8 niveles de progresiÃ³n** y conductas observables.
  - Criterios versionados, modificables **sin cambios de cÃ³digo**; nÃºcleos adicionales se agregan como **nuevas versiones**.
  - _Requirements: 6.6, 21.1, 21.5_
- [ ]* 7.4 MÃ³dulo F â€” Property test del determinismo de la rÃºbrica
  - **Propiedad: Determinismo de la rÃºbrica** â€” misma entrada `(evidencia, version_rubrica)` â‡’ misma `decision` y `score` evaluados sobre las mismas conductas observables cubiertas/pendientes; el LLM nunca altera la decisiÃ³n.
  - **Valida: Requirement 6.2**
  - _Requirements: 21.6_
- [ ]* 7.5 MÃ³dulo F â€” Tests unitarios exhaustivos de cada rama de la rÃºbrica (fixtures E-1)
  - AVANZAR/MANTENER/RETROCEDER impulsados por la **cobertura de conductas observables** del tramoÃ—nÃºcleoÃ—nivel y por la **racha** de retroceso, con casos borde.
  - Incluir un test de que una **conducta observable sin evidencia cuenta como pendiente** (no se infiere cumplimiento donde no hay evidencia).
  - _Requirements: 6.3, 6.4, 21.6_
- [x] 7.6 Implementar `BitacoraService`: RAG (recuperar evidencia) + LLM con trazabilidad y estados
  - Recuperar observaciones del perÃ­odo (14 dÃ­as) vÃ­a `RelationalRepo` + hasta 20 similares vÃ­a `VectorRepo`; abortar con 422 si no hay evidencia; abortar con 503 si el LLM falla/excede 60 s; cada afirmaciÃ³n cita â‰¥1 observaciÃ³n/manifestaciÃ³n; persistir en estado "borrador".
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
- [x] 7.7 Soportar ediciÃ³n y aprobaciÃ³n de bitÃ¡cora
  - Editar mientras estÃ¡ en "borrador"; aprobar cambia a "aprobada"; rechazar ediciÃ³n de "aprobada" con HTTP 409.
  - _Requirements: 5.7, 5.8, 5.9_
- [ ]* 7.8 MÃ³dulo F â€” Property test de trazabilidad de bitÃ¡coras
  - **Propiedad: Trazabilidad** â€” toda afirmaciÃ³n evaluativa referencia al menos una observaciÃ³n/manifestaciÃ³n existente de la evidencia recuperada.
  - **Valida: Requirement 5.5**
- [x] 7.9 Implementar `RecommendationService`: recuperar evidencia previa (RAG) â†’ `RubricaDecision` (mapea a conductas observables y decide) â†’ LLM (argumenta) â†’ persistir con `version_rubrica`
  - Recuperar la **evidencia previa** del niÃ±o/a (RAG); `RubricaDecision` la mapea a las **conductas observables** del tramoÃ—nÃºcleoÃ—nivel y produce la decisiÃ³n; pasar al LLM como contexto las **conductas observables (cubiertas y pendientes)** + la evidencia, de modo que el LLM **argumente citando conductas observables y observaciones previas sin alterar la decisiÃ³n**.
  - Responder en â‰¤10 s una de AVANZAR/MANTENER/RETROCEDER e incluir **tramo/nÃºcleo/nivel** en la respuesta; abstenerse si <5 observaciones (indicador de datos insuficientes); conservar la decisiÃ³n determinista si el LLM falla/excede 10 s; registrar `decision_educadora` (aceptÃ³/rechazÃ³/ajustÃ³); sugerencia proactiva al cruzar el umbral.
  - _Requirements: 6.1, 6.4, 6.5, 6.7, 6.8, 6.9, 6.10, 6.11, 21.4_
- [ ]* 7.10 MÃ³dulo F â€” Tests de servicio con `MockLlmProvider` y fakes de repos
  - Verificar que la decisiÃ³n proviene de la **cobertura de conductas observables de la rÃºbrica** (no del LLM) y que el **argumento del LLM cita conductas observables**; abstenciÃ³n por datos insuficientes; aislamiento total.
  - _Requirements: 6.2, 6.8, 6.9, 21.4_
- [ ]* 7.11 MÃ³dulo F â€” Sonda del mÃ³dulo (opcional)
  - _Optional_ â€” script que genera una bitÃ¡cora y una recomendaciÃ³n de un `id_nino` del dataset en modo mock.
  - _Requirements: 5.1, 6.1_
- [ ]* 7.12 MÃ³dulo F â€” DocumentaciÃ³n `docs/backend/rubrica.md` y `servicios.md`
  - _Optional_ â€” documentar el **modelo de la rÃºbrica oficial** (tramoÃ—nÃºcleoÃ—8 nivelesÃ—conductas observables) en `docs/backend/rubrica.md`, junto con la rÃºbrica versionada y los servicios RAG/recomendaciÃ³n, con un diagrama ```mermaid```.
  - _Requirements: 12.2, 12.6_

- [ ] 8. Checkpoint â€” Asegurar que pasan los tests de los mÃ³dulos Aâ€“F
  - Ensure all tests pass, ask the user if questions arise.

<!-- ============================================================= -->
<!-- MÃ“DULO G Â· Reporte + API REST/routers + DI â€” Dev 4.           -->
<!-- Depende de: A, interfaces de B/D/E/F.                        -->
<!-- ============================================================= -->

- [ ] 9. MÃ³dulo G â€” Reporte de direcciÃ³n, API REST y contenedor DI **[integraciÃ³n]** (cablea B/D/E/F vÃ­a DI; integraciÃ³n real requiere esos mÃ³dulos funcionales)
- [ ] 9.1 Implementar `DirectorReportService` (Modelo 4): agrega mÃ©tricas vÃ­a `RelationalRepo` + resumen ejecutivo vÃ­a `LlmProvider`
  - Conteos subieron/mantuvieron/bajaron (cada niÃ±o en exactamente una categorÃ­a), distribuciÃ³n por sala/dominio, conteos de observaciones/bitÃ¡coras, alertas, KPI de tiempo ahorrado determinista; validar rango de fechas (inicio â‰¤ fin); cero sin datos; mÃ©tricas desde SQL (no inferidas por LLM); resumen opcional si el LLM falla.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
- [ ] 9.2 Implementar el contenedor de DI en `core/` que selecciona adaptadores/repos segÃºn `USE_MOCKS`
  - Mismo contenedor sirve en Lambda (producciÃ³n) y `uvicorn` local; inyecciÃ³n por `Depends()`.
  - _Requirements: 10.3, 10.7, 13.5_
- [ ] 9.3 Implementar routers FastAPI (ninos, observaciones, bitacoras, recomendaciones, reportes, ruta-niveles, health) con validaciÃ³n Pydantic
  - Contratos REST del diseÃ±o; envolver la app con **Mangum** (`handler = Mangum(app)`) para Lambda sin cambiar routers.
  - _Requirements: 1.1, 3.3, 3.4, 5.7, 5.8, 6.1, 6.7, 7.1, 8.1_
- [ ] 9.4 Manejo de errores en espaÃ±ol (400 formato, 404 no encontrado, 422 validaciÃ³n, 409 conflicto, 503 LLM)
  - Traducir excepciones tipadas de providers a respuestas HTTP sin filtrar detalles sensibles.
  - _Requirements: 1.3, 2.6, 5.2, 5.4, 5.9, 10.6_
- [ ]* 9.5 MÃ³dulo G â€” Tests de contrato con `TestClient` y servicios fake
  - CÃ³digos de estado, forma de respuesta y validaciÃ³n; aislamiento con fakes de B/D/E/F.
  - _Requirements: 1.3, 7.1, 8.1_
- [ ]* 9.6 MÃ³dulo G â€” Tests de agregaciones del reporte con dataset sembrado
  - _Requirements: 7.1, 7.3, 7.4_
- [ ]* 9.7 MÃ³dulo G â€” DocumentaciÃ³n `docs/backend/README.md`
  - _Optional_ â€” mapa de mÃ³dulos, contratos interface-first, DI y aplicaciÃ³n de SOLID, con un diagrama ```mermaid```.
  - _Requirements: 12.2, 12.6_

<!-- ============================================================= -->
<!-- TRANSVERSAL Â· Resguardo de datos sensibles. Depende de: A.    -->
<!-- ============================================================= -->

- [ ] 10. Transversal â€” Resguardo de datos sensibles (despersonalizaciÃ³n)
  - Garantizar seudonimizaciÃ³n (`id_nino`) en BD y en prompts; separar personal (relacional) y contenido (vectorial); bloquear envÃ­o al LLM si el prompt contiene nombre/RUT/direcciÃ³n/contacto, registrar el evento y devolver error.
  - _Requirements: 11.1, 11.2, 11.3, 11.5_
- [ ]* 10.1 Transversal â€” Property test de despersonalizaciÃ³n
  - **Propiedad: DespersonalizaciÃ³n** â€” ningÃºn prompt enviado al LLM contiene nombre real ni RUT; solo `id_nino` + texto + rÃºbrica.
  - **Valida: Requirements 11.1, 11.2**

<!-- ============================================================= -->
<!-- MÃ“DULO H Â· Infraestructura AWS (CDK) + despliegue + integraciÃ³n -->
<!-- Dev 1/4. Depende de: contrato de despliegue (handler Lambda). -->
<!-- Requiere credenciales AWS configuradas (`aws configure`).     -->
<!-- ============================================================= -->

- [ ] 11. MÃ³dulo H â€” Infraestructura AWS CDK, despliegue e integraciÃ³n cloud real **[independiente]** (implementaciÃ³n/synth aislados; despliegue real requiere credenciales)
- [ ] 11.1 Instalar y configurar el tooling AWS (AWS CLI + CDK en Python)
  - Instalar AWS CLI v2 y AWS CDK; `cdk bootstrap`. **Prerrequisito del usuario:** configurar credenciales con `aws configure` usando la cuenta de la hackathon antes de desplegar o correr integraciÃ³n cloud.
  - _Requirements: 10.1_
- [ ] 11.2 Escribir los stacks CDK (Python): `NetworkStack`, `DataStack`, `ComputeStack`, `AiIamStack`
  - Network: VPC mÃ­nima + endpoints. Data: Aurora Serverless v2 (Postgres + pgvector), bucket S3 cifrado, Secrets Manager. Compute: Lambda (FastAPI+Mangum) + HTTP API en API Gateway + env vars (`USE_MOCKS=false`). AiIam: permisos mÃ­nimos para Bedrock/Transcribe/Textract/Rekognition.
  - _Requirements: 10.1, 11.4, 11.6_
- [ ] 11.3 Desplegar (`cdk synth` â†’ `cdk deploy`), sembrar E-1 en Aurora y verificar `/health`
  - `/health` responde HTTP 200 en â‰¤5 s vÃ­a API Gateway; reporte de stack/recurso ante fallo de deploy dejando el entorno reintentar-able; registrar errores AWS en CloudWatch.
  - _Requirements: 10.2, 10.5, 10.6, 10.8_
- [ ]* 11.4 MÃ³dulo H â€” Pruebas de integraciÃ³n cloud REAL (bajo demanda)
  - _Optional_ â€” invocan Bedrock/Transcribe/Textract/S3/Aurora en cuenta sandbox (marcador dedicado, separadas de la suite rÃ¡pida). **Requieren credenciales AWS (`aws configure`).**
  - _Requirements: 10.3, 10.4_
- [ ]* 11.5 MÃ³dulo H â€” DocumentaciÃ³n `docs/cloud/`
  - _Optional_ â€” `README.md` (arquitectura serverless), `cdk.md` (stacks, IAM mÃ­nimos), `despliegue.md` (pasos + env vars), `integracion.md`, con un diagrama ```mermaid```.
  - _Requirements: 12.5, 12.6_

<!-- ============================================================= -->
<!-- FRONTEND Â· Tarea posterior (desde Figma). No bloquea backend. -->
<!-- ============================================================= -->

- [ ] 12. Frontend PWA â€” base y capa de servicios API (posterior) **[integraciÃ³n]** (consume la API REST que expone G)
  - Inicializar React + Vite como PWA (manifest, service worker), capa `api/` tipada, router por rol, `SelectorRol`, `BannerDatosSinteticos`, `IndicadorCarga`; mobile-first 320â€“1024 px, controles â‰¥44Ã—44 px, espaÃ±ol (Chile); indicador de progreso â‰¤100 ms; manejo de error/timeout 10 s sin descartar datos.
  - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.2, 9.3, 9.4, 9.6, 9.7_
- [ ] 13. Frontend â€” pantallas de educadora y dashboard de direcciÃ³n (estilo placeholder) **[integraciÃ³n]**
  - Educadora: MiSala, Capturar, ConfirmarClasificacion (con sugerencia proactiva), FichaNino (trayectoria + "Â¿Puede subir de nivel?" con 3 estados), Bitacoras (ver/editar/aprobar). Directora: DashboardDireccion (mÃ©tricas, KPI, resumen). Estilos placeholder; sin lÃ³gica de negocio en el cliente.
  - _Requirements: 8.2, 8.3, 9.5, 9.6_
- [ ]* 13.1 Frontend â€” DocumentaciÃ³n `docs/frontend/`
  - _Optional_ â€” `README.md` (pantallas, routing por rol) + `contrato-api.md`, marcado como pendiente de Figma, con un diagrama ```mermaid```.
  - _Requirements: 12.3, 12.6_

<!-- ============================================================= -->
<!-- DISPARADOR FIGMA Â· LISTO PARA ACTIVAR cuando llegue el PDF.    -->
<!-- No ejecutar hasta recibir los mockups refinados de Figma.     -->
<!-- No cambia la lÃ³gica de negocio ni el contrato REST (inmutable).-->
<!-- ============================================================= -->

- [ ] 14. â³ DISPARADOR (esperando PDF) â€” Ingesta de mockups de Figma al frontend **[integraciÃ³n]**
  - **Tarea-disparador: NO ejecutar hasta recibir el PDF de mockups refinados de Figma.** Al activarse, convierte el diseÃ±o visual en tareas concretas de frontend sin tocar el backend.
  - [ ] 14.1 Ingestar el PDF de Figma y extraer las pantallas y flujos representados en los mockups
    - _Requirements: 20.1_
  - [ ] 14.2 Gap-analysis de pantallas/flujos contra el **contrato REST existente**, identificando los endpoints que consume cada pantalla y las brechas detectadas
    - _Requirements: 20.2_
  - [ ] 14.3 Producir tareas de **componentes concretos** mapeados a las pantallas existentes
    - `MiSala`, `Capturar`, `ConfirmarClasificacion`, `FichaNino`, `Bitacoras`, `DashboardDireccion`.
    - _Requirements: 20.3_
  - [ ] 14.4 Implementar aplicando **estilos y tokens de diseÃ±o sobre la estructura existente**, sin alterar la lÃ³gica de negocio
    - **Invariante clave:** el **contrato de la API REST del Backend permanece sin cambios** como resultado de la ingesta de los mockups.
    - _Requirements: 20.4, 20.5_

<!-- ============================================================= -->
<!-- INTEGRACIÃ“N FINAL E2E Â· Depende de TODOS. Va al final.        -->
<!-- Solo cablea implementaciones reales vÃ­a DI; no reescribe.     -->
<!-- ============================================================= -->

- [ ] 15. IntegraciÃ³n final E2E â€” ensamblar y verificar el cruce entre mÃ³dulos **[integraciÃ³n]** (requiere TODOS los mÃ³dulos completos y funcionales)
- [ ] 15.1 Cablear implementaciones concretas vÃ­a el contenedor DI y validar lÃ­mites de interfaz
  - El ensamblaje falla e indica el mÃ³dulo/importaciÃ³n prohibida si un mÃ³dulo importa directamente la implementaciÃ³n concreta de otro (solo se permiten `base.py` de interfaz y el dominio A).
  - _Requirements: 13.5, 13.6_
- [ ]* 15.2 Property test de intercambiabilidad de adaptadores (LSP)
  - **Propiedad: Intercambiabilidad (LSP)** â€” cualquier test de servicio pasa indistintamente con el adaptador AWS o el mock inyectado, sin cambiar el cÃ³digo del servicio.
  - **Valida: Requirements 2.8, 4.5, 5.10, 10.3**
- [ ]* 15.3 Test E2E de ingesta en modo mock (texto/audio/foto/video)
  - Flujo completo storage â†’ transcripciÃ³n â†’ clasificaciÃ³n â†’ persistencia â†’ embedding, idempotente.
  - _Requirements: 1.1, 2.1, 3.4, 4.3_
- [ ] 15.4 VerificaciÃ³n de la demo en modo mock (un solo comando) y actualizaciÃ³n del README
  - Recorrer flujo educadora (capturar â†’ clasificar â†’ recomendaciÃ³n â†’ bitÃ¡cora â†’ aprobar) y flujo directora (reporte) con tests automatizados; README con guion de demo y pasos AWS opcionales.
  - _Requirements: 10.7, 10.9_

- [ ] 16. Checkpoint final â€” Asegurar que pasan todos los tests
  - Ensure all tests pass, ask the user if questions arise.

<!-- ============================================================= -->
<!-- TRANSVERSAL Â· Atributos de calidad (pilares de evaluaciÃ³n).    -->
<!-- Mezcla de tareas de mÃ³dulo (independientes) y de verificaciÃ³n  -->
<!-- del sistema ensamblado (integraciÃ³n). Verificable incremental. -->
<!-- ============================================================= -->

- [ ] 17. Atributos de calidad y escalabilidad (pilares de evaluaciÃ³n)
- [ ] 17.1 Test de anÃ¡lisis estÃ¡tico de importaciones (arquitectura) **[independiente]**
  - Probar que las clases de servicio importan **solo interfaces** (abstracciones) y **cero** implementaciones concretas de proveedores/repos hermanos; evidenciar OCP/ISP/DIP: agregar un proveedor/modelo nuevo se hace implementando una interfaz **sin editar servicios**.
  - _Requirements: 15.2, 15.5_
- [ ] 17.2 VerificaciÃ³n del KPI de impacto social y human-in-the-loop **[integraciÃ³n]**
  - Comprobar que el KPI de tiempo de documentaciÃ³n ahorrado (**~4 h/semana â†’ ~0 h**) se **calcula de forma determinista** y se **expone en el reporte de direcciÃ³n**, y que **ninguna** clasificaciÃ³n, bitÃ¡cora o recomendaciÃ³n se aplica automÃ¡ticamente sin **validaciÃ³n humana** (`decision_educadora` registrada antes de considerarla final).
  - _Requirements: 16.1, 16.2, 16.3, 16.5_
- [ ]* 17.3 Sonda de escalabilidad **[integraciÃ³n]**
  - _Optional_ â€” apuntar el sistema al **dataset completo de 500 niÃ±os** (y opcionalmente a un conjunto multiplicado mayor) y confirmar que **no requiere cambios de cÃ³digo ni de contratos de interfaz**; dejar nota de que `VectorRepo` es **sustituible por OpenSearch Serverless** sin tocar los servicios.
  - _Requirements: 18.1, 18.4, 18.5_
- [ ] 17.4 Chequeo de factibilidad y sustentabilidad **[independiente]**
  - Verificar **dependencias fijadas (pinned)** de modo que una instalaciÃ³n posterior reproduzca el mismo conjunto de versiones; **modo mock local a costo cloud cero** (sin llamadas de red a AWS con `USE_MOCKS=true`); **un Ãºnico flujo de IaC** (AWS CDK Python).
  - _Requirements: 17.1, 17.2, 17.3_
- [ ] 17.5 Calidad de presentaciÃ³n â€” guion de demo y documentaciÃ³n por Ã¡rea **[integraciÃ³n]**
  - Escribir el **guion de demo en el README** (demo mock de un solo comando + demo en vivo sobre AWS con `/health`) y asegurar que `docs/` existe **organizada por Ã¡rea** (`backend/`, `frontend/`, `database/`, `cloud/`), cada una con al menos un Markdown y un diagrama ```mermaid```.
  - _Requirements: 19.1, 19.2, 19.3, 19.4_

## Notes

- **Prerrequisito AWS:** antes de desplegar (MÃ³dulo H) o correr las pruebas de integraciÃ³n cloud, el usuario debe configurar credenciales con `aws configure` usando la cuenta de la hackathon. Sin credenciales, todo el resto se desarrolla y prueba en modo mock (`USE_MOCKS=true`).
- **AWS primero, mock secundario:** los adaptadores AWS (Bedrock Claude+Titan, Transcribe, Textract, Rekognition, S3, Aurora+pgvector) son la implementaciÃ³n principal; los mocks viven tras las mismas interfaces para desarrollo local/CI sin credenciales.
- **MÃ³dulos independientes y verificables con mocks:** cada mÃ³dulo (Bâ€“H) depende solo de las interfaces del MÃ³dulo A y trae su propio fake/mock, por lo que su suite de tests corre y pasa en aislamiento, sin importar la implementaciÃ³n concreta de otro mÃ³dulo.
- **Tareas completadas:** 1 (bootstrap), 2 (MÃ³dulo A) y 3.1â€“3.3 (MÃ³dulo B: esquema + `RelationalRepo` + seed inicial E-1) ya estÃ¡n implementadas. 2.1 aÃ±ade el alineamiento de contratos para las nuevas interfaces y 3.4 aÃ±ade las consultas agregadas que faltaban para el reporte.
- **Dataset E-1 OFICIAL como fuente de verdad (reproducible):** el seed migra de "un JSON por tabla" (tarea 3.3, ya hecha) a cargar el **Dataset E-1 oficial** vÃ­a `DatasetLoader` (**7 CSV relacionales + `consolidado.json`**, 500 niÃ±os/as) con validaciÃ³n de conteos contra `distribucion_y_validacion` (tareas 3.7â€“3.8), verificaciÃ³n de **reproducibilidad bit a bit** (semilla `20261013`, fecha `2026-10-13`, Python 3.12 stdlib; tarea 3.9) y la ruta de **abstenciÃ³n** para los 60 niÃ±os con <5 observaciones (tarea 3.10). Solo se versiona `dataset_e1_publico.zip`; el **zip interno de validaciÃ³n NO** se incluye, y el dataset reducido/casero queda **solo como respaldo rÃ¡pido de pruebas** (tarea 3.11).
- **RÃºbrica oficial como fuente de verdad del nivel (MÃ³dulo F):** la **rÃºbrica oficial** (tramo de sala Ã— nÃºcleo Ã— 8 niveles de progresiÃ³n, con **conductas observables** por nivel) es la **fuente de verdad de la decisiÃ³n de nivel**, versionada en `rubrica_versiones.criterios` (tareas 7.2b/7.3). `RubricaDecision` (7.2) mapea la evidencia previa a conductas observables y decide de forma determinista (AVANZAR/MANTENER/RETROCEDER); el **argumento de la recomendaciÃ³n cita conductas observables + evidencia previa** del niÃ±o/a para ahorrar tiempo a la educadora (**KPI**), sin que el LLM altere la decisiÃ³n.
- **Pilares de evaluaciÃ³n de primera clase (tarea 17):** la **innovaciÃ³n tÃ©cnica** (POO + encapsulamiento + puertos/adaptadores con SOLID: OCP/ISP/DIP), el **impacto social** (KPI 4 hâ†’~0 h + human-in-the-loop), la **factibilidad/sustentabilidad** (serverless scale-to-zero, deps pinned, mock a costo cero, un flujo IaC), la **escalabilidad** (Lambda sin estado, Aurora+pgvector, `VectorRepo` sustituible por OpenSearch) y la **calidad de presentaciÃ³n** (demo de un comando + guion en README + `docs/` por Ã¡rea con Mermaid) se verifican de forma incremental.
- **Ingesta de Figma = disparador (tarea 14):** estÃ¡ **lista para activar y a la espera del PDF** de mockups refinados. Al llegar, ejecuta extraer â†’ gap-analysis â†’ componentes â†’ estilos/tokens sobre el layout existente, **sin cambiar la lÃ³gica de negocio ni el contrato REST** (invariante del Requirement 20.5).
- **Independiente vs integraciÃ³n (ver matriz):** consulta la nueva **"Dependencias entre mÃ³dulos (matriz legible)"** en la secciÃ³n *Task Dependency Graph*. En resumen: **B, C, D, E, F, H son INDEPENDIENTES** (se implementan y prueban en aislamiento con fakes/mocks sobre los contratos de A), mientras que **G, el Frontend, las sondas de calidad del sistema (17.2/17.3/17.5) y la E2E (15) son de INTEGRACIÃ“N** y requieren que sus mÃ³dulos fuente estÃ©n completos y funcionales.
- **Reparto sugerido entre 4 personas (tras congelar A):**
  - Dev 1 â†’ MÃ³dulo B (cierre: 3.4â€“3.11, incl. `DatasetLoader` oficial + reproducibilidad) + MÃ³dulo H (infra/CDK).
  - Dev 2 â†’ MÃ³dulo C (vectorial/embeddings) + MÃ³dulo D (ingesta/transcripciÃ³n).
  - Dev 3 â†’ MÃ³dulo E (clasificaciÃ³n) + parte de MÃ³dulo F.
  - Dev 4 â†’ MÃ³dulo F (rÃºbrica/bitÃ¡cora/recomendaciÃ³n) + MÃ³dulo G (reporte/API/DI).
  - El Frontend (12â€“14) y la IntegraciÃ³n E2E (15) se toman cuando los mÃ³dulos estÃ©n listos.
- **Flujo de merge por mÃ³dulo:** cada dev trabaja su mÃ³dulo en una rama, lo implementa con sus fakes/mocks, corre sus tests de aislamiento (y, si quiere, la sonda `_Optional_`), verifica en verde y mergea a `main`. La integraciÃ³n E2E (15) se hace al final y es la Ãºnica que cruza mÃ³dulos reales vÃ­a DI.
- **Tareas opcionales (`_Optional_`):** sondas de mÃ³dulo y docs; dan confianza extra o cumplen Requirement 12 pero no gatean el mÃ³dulo. Los tests requeridos (sin `_Optional_`) son los que validan cada mÃ³dulo.
- **Checkpoints:** las tareas 8 y 16 son puntos de validaciÃ³n incremental.

## Task Dependency Graph

MÃ³dulo A es la raÃ­z compartida (solo interfaces) de la que dependen todos. Una vez **congelado A (2 + 2.1)**, los mÃ³dulos Bâ€“H pueden avanzar **en paralelo** (cada uno depende solo de los contratos de A). La integraciÃ³n E2E depende de todos.

```json
{
  "waves": [
    {
      "id": 0,
      "label": "MÃ³dulo A Â· Dominio + contratos (congelar primero)",
      "description": "Base compartida que debe congelarse antes de que arranquen Bâ€“H. Ãšnica fuente de verdad de interfaces y modelos.",
      "parallelizable": false,
      "tasks": ["2.1", "2.2"]
    },
    {
      "id": 1,
      "label": "MÃ³dulos B, C, D, E, F, H + transversal Â· en paralelo (4 personas) â€” INDEPENDIENTES",
      "description": "Una vez congelado A, estos mÃ³dulos dependen solo de las interfaces de A y traen sus propios fakes/mocks, asÃ­ que corren en paralelo sin bloquearse entre sÃ­. Incluye el seed del dataset E-1 OFICIAL (DatasetLoader de 7 CSV + consolidado.json) y los tests de arquitectura/factibilidad de nivel mÃ³dulo.",
      "parallelizable": true,
      "tasks": [
        "3.4", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11",
        "4.1", "4.2", "4.3", "4.4", "4.5", "4.6",
        "5.1", "5.2", "5.3", "5.4", "5.5", "5.6",
        "6.1", "6.2", "6.3", "6.4",
        "7.1", "7.2", "7.2b", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.9", "7.10", "7.11", "7.12",
        "10.1",
        "11.1", "11.2", "11.3", "11.4", "11.5",
        "17.1", "17.4"
      ]
    },
    {
      "id": 2,
      "label": "MÃ³dulo G Â· Reporte + API REST + DI â€” INTEGRACIÃ“N",
      "description": "Cablea las interfaces de servicios de B/D/E/F vÃ­a el contenedor DI; depende de que esos mÃ³dulos existan (al menos sus contratos implementados).",
      "parallelizable": true,
      "tasks": ["9.1", "9.2", "9.3", "9.4", "9.5", "9.6", "9.7"]
    },
    {
      "id": 3,
      "label": "Frontend + IntegraciÃ³n final E2E + verificaciÃ³n del sistema ensamblado â€” INTEGRACIÃ“N",
      "description": "Dependen del sistema ensamblado. El frontend consume la API de G; la integraciÃ³n E2E cruza todos los mÃ³dulos reales vÃ­a DI; las sondas de calidad verifican el sistema ensamblado (KPI, escalabilidad, presentaciÃ³n). La ingesta de Figma (14.x) es un disparador que espera el PDF.",
      "parallelizable": true,
      "tasks": ["13.1", "15.1", "15.2", "15.3", "17.2", "17.3", "17.5", "14.1", "14.2", "14.3", "14.4"]
    }
  ]
}
```

> Nota: dentro de cada wave las tareas son independientes y pueden repartirse entre las 4 personas del equipo; cada wave N solo arranca cuando terminan las waves 0..N-1. Las tareas de checkpoint (8, 16) y las tareas padre sin notaciÃ³n decimal no se incluyen en el grafo de waves.

```mermaid
graph TD
    A["MÃ³dulo A Â· Dominio + contratos (CONGELAR 1Âº)<br/>tareas 2, 2.1"]

    B["MÃ³dulo B Â· Relacional + seed E-1 OFICIAL<br/>[independiente] 3.4, 3.7â€“3.11"]
    C["MÃ³dulo C Â· Vectorial + embeddings<br/>[independiente] 4.1â€“4.3"]
    D["MÃ³dulo D Â· Ingesta + transcripciÃ³n<br/>[independiente] 5.1â€“5.4"]
    E["MÃ³dulo E Â· ClasificaciÃ³n<br/>[independiente] 6.1â€“6.2"]
    F["MÃ³dulo F Â· BitÃ¡coras + RÃºbrica oficial (tramoÃ—nÃºcleoÃ—nivelesÃ—conductas observables) + RecomendaciÃ³n<br/>[independiente] 7.1â€“7.9 (incl. 7.2b transcripciÃ³n rÃºbrica), 10"]
    G["MÃ³dulo G Â· Reporte + API + DI<br/>[integraciÃ³n] 9.1â€“9.4"]
    H["MÃ³dulo H Â· Infra AWS CDK + deploy<br/>[independiente] 11.1â€“11.3"]
    Q["Atributos de calidad (pilares)<br/>mÃ³dulo 17.1/17.4 + sistema 17.2/17.3/17.5"]
    FE["Frontend Â· PWA (posterior, desde Figma)<br/>[integraciÃ³n] 12â€“13"]
    FIG["â³ DISPARADOR Figma (espera PDF)<br/>[integraciÃ³n] 14.1â€“14.4"]
    E2E["IntegraciÃ³n final E2E<br/>[integraciÃ³n] 15.1â€“15.4"]

    A --> B
    A --> C
    A --> D
    A --> E
    A --> F
    A --> G
    A --> H

    B -. interfaz RelationalRepo .-> F
    C -. interfaz VectorRepo .-> F
    B -. interfaz RelationalRepo .-> G
    D -. interfaz TranscriptionProvider .-> G
    E -. interfaz Classifier .-> G
    F -. interfaces de servicios .-> G

    B --> E2E
    C --> E2E
    D --> E2E
    E --> E2E
    F --> E2E
    G --> E2E
    H -. despliega .-> E2E
    G --> FE
    FE -. estilos/tokens al llegar PDF .-> FIG
    E2E --> Q

    classDef done fill:#d4edda,stroke:#28a745,color:#155724;
    classDef trigger fill:#fff3cd,stroke:#ffc107,color:#856404;
    class A,B done;
    class FIG trigger;
```

> **Paralelismo explÃ­cito:** tras congelar A (tareas 2 y 2.1), 4 devs pueden tomar simultÃ¡neamente **B/H**, **C/D**, **E + parte de F**, y **F/G**. Las flechas punteadas son dependencias de **interfaz** (se usa un fake mientras el proveedor real se construye), no de implementaciÃ³n, asÃ­ que no bloquean el trabajo en paralelo. El Frontend y la IntegraciÃ³n E2E se ejecutan al final.

### Dependencias entre mÃ³dulos (matriz legible)

Esta matriz deja **claro, mÃ³dulo por mÃ³dulo**, si se puede implementar y probar **solo** (con fakes/mocks) o si **depende de otros mÃ³dulos completos y funcionales** para su **integraciÃ³n real**.

| MÃ³dulo | Tipo | Puede empezar cuando... | Depende de (funcional) para integrar | Tests propios (aislamiento) |
|---|---|---|---|---|
| **A Â· Dominio + contratos** | Base (se congela 1Âº) | Siempre â€” no depende de nadie | â€” (nadie; es la raÃ­z) | ValidaciÃ³n Pydantic de modelos/enums |
| **B Â· Relacional + seed E-1 oficial** | **INDEPENDIENTE** | A estÃ¡ **congelado** (interfaces) | â€” (solo contratos de A) | SQLite in-memory + dataset E-1 oficial; validaciÃ³n de conteos |
| **C Â· Vectorial + embeddings** | **INDEPENDIENTE** | A estÃ¡ congelado | â€” (solo contratos de A) | Ãndice en memoria + `MockEmbeddingProvider` |
| **D Â· Ingesta + transcripciÃ³n** | **INDEPENDIENTE** | A estÃ¡ congelado | â€” (usa fakes de `Classifier`, `RelationalRepo`, `EmbeddingService`) | Mocks de Transcribe/Textract/Rekognition/S3 por formato |
| **E Â· ClasificaciÃ³n** | **INDEPENDIENTE** | A estÃ¡ congelado | â€” (fake de `RelationalRepo`) | Fixtures de texto del dataset E-1 |
| **F Â· BitÃ¡coras + RÃºbrica + RecomendaciÃ³n** | **INDEPENDIENTE** | A estÃ¡ congelado | â€” (fakes de B/C y `MockLlmProvider`) | `MockLlmProvider` + fakes de repos |
| **G Â· Reporte + API + DI** | **INTEGRACIÃ“N** | Existan los **contratos** de B/D/E/F | **B, D, E, F funcionales** para integraciÃ³n real | `TestClient` + servicios **fake** (aislamiento del router) |
| **H Â· Infra AWS (CDK)** | **INDEPENDIENTE** | A estÃ¡ congelado + contrato de handler Lambda | Credenciales AWS para **desplegar** (no para `cdk synth`) | `cdk synth` + tests de sÃ­ntesis sin credenciales |
| **Calidad (17)** | Mixto | 17.1/17.4 con mÃ³dulos; 17.2/17.3/17.5 con sistema | Sistema **ensamblado** (G + E2E) para 17.2/17.3/17.5 | 17.1 anÃ¡lisis estÃ¡tico; 17.4 deps/mock aislados |
| **Frontend (12â€“13)** | **INTEGRACIÃ“N** | **G expone la API REST** | **G funcional** (API en vivo) | Smoke tests de render + capa de servicios API |
| **Figma (14)** | Disparador | **Llega el PDF** de mockups refinados | Frontend base (12â€“13) + API REST (inmutable) | VerificaciÃ³n de que el contrato REST no cambia |
| **E2E (15)** | **INTEGRACIÃ“N** | **Todos** los mÃ³dulos listos | **TODOS** los mÃ³dulos completos y funcionales | Cruce real vÃ­a DI (Ãºnica que integra mÃ³dulos reales) |

**Leyenda â€” dos clases de tarea:**
- **(i) Tareas de mÃ³dulo = INDEPENDIENTES.** Se implementan y prueban **en aislamiento** usando **fakes/mocks** de todo lo externo. Solo necesitan los **contratos (interfaces) de A**. Cada dev las construye, prueba y mergea **solo**, sin esperar a otro. Son B, C, D, E, F, H y los tests de mÃ³dulo 17.1/17.4.
- **(ii) Tareas de INTEGRACIÃ“N = dependen de otros mÃ³dulos reales.** Verifican el **sistema ensamblado** cruzando implementaciones reales: la parte real de G, el Frontend, la ingesta de Figma, las sondas de calidad 17.2/17.3/17.5 y la E2E (15). No pueden completarse hasta que los mÃ³dulos de los que dependen estÃ©n **completos y funcionales**.

**Ejemplo concreto (en palabras del equipo):** *"A, B y C son independientes: cada uno se implementa y prueba solo con fakes/mocks sobre los contratos de A. En cambio, G para su test de integraciÃ³n requiere que B, D, E y F estÃ©n completos y funcionales (no basta el contrato), y la E2E (15) requiere que **todos** los mÃ³dulos lo estÃ©n."* Dicho de otra manera, con las letras reales: **B, C, D, E, F, H son independientes** (fakes), mientras que **G y la E2E son de integraciÃ³n** y necesitan sus mÃ³dulos fuente reales.
