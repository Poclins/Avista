# Implementation Plan — jAImes MVP

- [ ] 1. Preparar estructura del proyecto y configuración base
  - Crear estructura `backend/app/{api,services,domain,providers,repositories,core}` y `frontend/`.
  - Configurar `pyproject`/requirements (FastAPI, pydantic, boto3, sqlalchemy, pgvector, uvicorn), `.env.example` con `USE_MOCKS`, y settings en `core/`.
  - Añadir `docker-compose` (backend + Postgres/pgvector) y README inicial con pasos de ejecución.
  - _Requirements: 10.3, 10.4_

- [ ] 2. Definir modelos de dominio y enums (POO)
  - Implementar `domain/models.py` con las entidades y enums (FormatoCaptura, Dominio, DecisionNivel, EstadoBitacora, Rol).
  - Escribir tests unitarios de construcción/validación de los modelos.
  - _Requirements: 1.4, 3.1, 4.1_

- [ ] 3. Implementar el esquema relacional y el seed del dataset E-1
- [ ] 3.1 Crear el esquema SQLAlchemy de las tablas E-1 + nuevas (bitacoras, recomendaciones, rubrica_versiones, reportes_direccion)
  - Mapear tipos y nulabilidad según el diccionario de datos E-1.
  - _Requirements: 4.1_
- [ ] 3.2 Implementar `RelationalRepo` (interfaz + implementación Postgres/SQLite) con CRUD y consultas base
  - _Requirements: 4.4_
- [ ] 3.3 Escribir el script de seed que carga el dataset E-1 y un test que valida conteos contra distribucion_y_validacion
  - _Requirements: 10.2_

- [ ] 4. Implementar la base vectorial y el proveedor de embeddings
- [ ] 4.1 Definir `EmbeddingProvider` (base) con adaptadores Titan (AWS) y mock
  - _Requirements: 4.3_
- [ ] 4.2 Implementar `VectorRepo` (interfaz + pgvector e índice en memoria) con index/search por similitud + filtros
  - _Requirements: 4.2_
- [ ] 4.3 Implementar `EmbeddingService` (embeber texto e indexar) con tests usando el mock
  - _Requirements: 4.2, 4.3_

- [ ] 5. Implementar el proveedor de transcripción (Modelo 1)
- [ ] 5.1 Definir `TranscriptionProvider` (base) con adaptadores AWS (Transcribe/Textract/Rekognition) y mock
  - _Requirements: 2.1, 2.2, 2.3, 2.5_
- [ ] 5.2 Implementar `StorageRepo` (S3 + local) y `TranscriptionService` que enruta por formato
  - _Requirements: 1.2, 2.4, 11.3_
- [ ] 5.3 Tests del servicio de transcripción por cada formato (modo mock)
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 6. Implementar la clasificación de observaciones
- [ ] 6.1 Implementar `ClassificationService`: estimar nivel/dominio y vincular manifestaciones del dataset
  - _Requirements: 3.1, 3.2_
- [ ] 6.2 Devolver clasificación propuesta y soportar confirmación/corrección persistente
  - _Requirements: 3.3, 3.4_
- [ ] 6.3 Tests de clasificación y de vínculo con manifestaciones
  - _Requirements: 3.1, 3.2_

- [ ] 7. Orquestar la ingesta end-to-end
  - Implementar `IngestionService`: storage → transcripción → clasificación → persistencia relacional → embedding, de forma idempotente.
  - Test de flujo completo con mocks (texto/audio/foto/video).
  - _Requirements: 1.1, 1.2, 1.3, 2.*, 3.*, 4.2_

- [ ] 8. Implementar la rúbrica determinista (Modelo 3 - núcleo)
- [ ] 8.1 Implementar `domain/rubrica.py` (`RubricaDecision`) con criterios versionados y las ramas AVANZAR/MANTENER/RETROCEDER
  - _Requirements: 6.2, 6.3, 6.5_
- [ ] 8.2 Sembrar una versión inicial de rúbrica en `rubrica_versiones`
  - _Requirements: 6.5_
- [ ] 8.3 Tests unitarios exhaustivos de la rúbrica (determinismo + cada decisión) con fixtures del dataset E-1
  - _Requirements: 6.1, 6.3, 6.4_

- [ ] 9. Implementar el proveedor LLM y el servicio de bitácoras (Modelo 2)
- [ ] 9.1 Definir `LlmProvider` (base) con adaptadores Bedrock (AWS) y mock
  - _Requirements: 5.6_
- [ ] 9.2 Implementar `BitacoraService`: RAG (recuperar evidencia) + LLM, con trazabilidad a observaciones/manifestaciones
  - _Requirements: 5.1, 5.2, 5.3, 5.4_
- [ ] 9.3 Soportar edición y aprobación de bitácora; tests del flujo con mock
  - _Requirements: 5.5_

- [ ] 10. Implementar el servicio de recomendación (Modelo 3 - integración)
  - `RecommendationService`: recuperar evidencia → rúbrica (decide) → LLM (argumenta) → persistir con version_rubrica.
  - Registrar decisión final de la educadora; sugerencia proactiva al cruzar umbral.
  - Tests que verifican que la decisión proviene de la rúbrica y no del LLM.
  - _Requirements: 6.1, 6.4, 6.6, 6.7_

- [ ] 11. Implementar el reporte de dirección (Modelo 4)
  - `DirectorReportService`: consultas agregadas (subieron/mantuvieron/bajaron, distribución, conteos, alertas, KPI) + resumen ejecutivo (LLM).
  - Tests de las agregaciones con el dataset sembrado.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 12. Exponer la API REST (routers) y el contenedor de DI
- [ ] 12.1 Implementar el contenedor de DI en `core/` que selecciona adaptadores/repos según `USE_MOCKS`
  - _Requirements: 2.5, 4.3, 4.4, 5.6, 10.1, 10.4_
- [ ] 12.2 Implementar routers de ninos, observaciones, bitacoras, recomendaciones, reportes, ruta-niveles con validación Pydantic
  - _Requirements: 1.1, 3.3, 3.4, 5.*, 6.*, 7.*, 8.*_
- [ ] 12.3 Manejo de errores en español y tests de contrato con TestClient
  - _Requirements: 1.3, 9.5_

- [ ] 13. Resguardo de datos sensibles (transversal)
  - Garantizar seudonimización (`id_nino`) en BD y en prompts; separar personal/contenido; URLs prefirmadas en camino AWS.
  - Test que verifica ausencia de PII en los prompts construidos.
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 14. Frontend PWA — base y capa de servicios API
  - Inicializar React + Vite como PWA (manifest, service worker), capa `api/` tipada, router por rol, `SelectorRol` y `BannerDatosSinteticos`.
  - _Requirements: 8.1, 8.2, 8.4, 9.1, 9.3, 9.5_

- [ ] 15. Frontend — pantallas de educadora (estructura, estilo placeholder)
  - Implementar MiSala, Capturar, ConfirmarClasificacion (con sugerencia proactiva), FichaNino (trayectoria + botón "¿Puede subir de nivel?" con 3 estados), Bitacoras (ver/editar/aprobar).
  - Marcar estilos como placeholder a refinar con Figma.
  - _Requirements: 1.1, 3.3, 5.5, 6.1, 6.6, 9.2, 9.4_

- [ ] 16. Frontend — dashboard de dirección (estructura, estilo placeholder)
  - Implementar DashboardDireccion con métricas agregadas, KPI y resumen ejecutivo.
  - _Requirements: 7.*, 8.3, 9.4_

- [ ] 17. Integración end-to-end en modo mock y verificación de la demo
  - Levantar todo con un comando; recorrer el flujo educadora (capturar → clasificar → recomendación → bitácora → aprobar) y el flujo directora (reporte).
  - Actualizar README con el guion de demo y los pasos AWS opcionales.
  - _Requirements: 10.1, 10.3_

- [ ] 18. (Al recibir mockups) Refinar el frontend al diseño de Figma
  - Analizar mockups, hacer el gap analysis contra la API y aplicar estilos/tokens al layout existente sin cambiar la lógica.
  - _Requirements: 9.4_
