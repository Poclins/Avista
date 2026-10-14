# Requirements — jAImes MVP

## Introducción

jAImes es una herramienta de IA para Fundación Integra (desafío "IA para el Desarrollo Infantil: de la Observación a la Acción", AWS Breaking Barriers Chile 2026). Su propósito es reducir el tiempo que las educadoras de párvulos ("tías") dedican a documentar (~4 h/semana) hacia ~0 h, convirtiendo automáticamente los recursos crudos que ya generan (texto, fotos de notas manuscritas, audios, videos) en observaciones estructuradas, trayectorias de desarrollo, bitácoras quincenales, recomendaciones de nivel y reportes de dirección.

El sistema se apoya en el dataset sintético E-1: una ruta de 9 niveles de desarrollo × 5 dominios (cognitivo, lenguaje_comunicacion, motor_fino, motor_grueso, socioemocional) con 90 manifestaciones observables, y tablas relacionales de jardines, educadoras, niños, observaciones y vínculos de evidencia.

**Restricciones transversales:**
- Datos sintéticos y seudonimizados; no es instrumento clínico ni diagnóstico.
- Backend en Python (FastAPI), POO + SOLID, arquitectura en 3 capas.
- Dos bases de datos: relacional (personas/entidades) y vectorial (transcripciones/embeddings para RAG).
- Despliegue objetivo en AWS (Transcribe, Textract, Rekognition, Bedrock, Titan Embeddings, S3, RDS/Aurora, OpenSearch), con **modo mock** que permite correr la demo sin credenciales AWS.
- Frontend mobile-first (PWA). El diseño visual seguirá los mockups de Figma (pendientes); la lógica la define el backend.

---

## Requirement 1 — Captura multi-formato de evidencia

**User Story:** Como educadora, quiero registrar lo que observo de un niño/a mediante texto, audio, foto o video desde mi celular, para no tener que escribir informes manualmente.

#### Acceptance Criteria
1. WHEN la educadora selecciona un niño/a y sube contenido de tipo texto, audio, foto o video THEN el sistema SHALL aceptar el medio y crear una observación asociada a ese `id_nino` y a la `id_educadora`.
2. WHEN se sube un medio no textual THEN el sistema SHALL almacenar el archivo original en object storage (S3 en AWS; almacenamiento local en modo mock).
3. IF el formato del archivo no es soportado THEN el sistema SHALL rechazar la carga con un mensaje de error claro en español.
4. WHEN se crea una observación THEN el sistema SHALL registrar la fecha de observación y el `formato_captura` (texto, audio, foto, video).

## Requirement 2 — Transcripción y extracción de texto (Modelo 1)

**User Story:** Como educadora, quiero que mis audios, videos y fotos de notas se conviertan automáticamente en texto, para que el sistema pueda analizarlos sin que yo transcriba nada.

#### Acceptance Criteria
1. WHEN se sube un audio THEN el sistema SHALL transcribirlo a texto en español (Amazon Transcribe en AWS; mock en local).
2. WHEN se sube una foto de una nota manuscrita THEN el sistema SHALL extraer el texto por OCR (Amazon Textract en AWS; mock en local).
3. WHEN se sube un video THEN el sistema SHALL transcribir su audio y SHALL obtener metadatos de escena (Amazon Rekognition en AWS; mock en local).
4. WHEN el contenido es texto directo THEN el sistema SHALL usarlo sin transcripción.
5. The transcription provider SHALL be accessed through an interface (`TranscriptionProvider`) with interchangeable AWS and mock implementations selectable by configuration (`USE_MOCKS`).

## Requirement 3 — Clasificación automática de la observación

**User Story:** Como educadora, quiero que cada observación quede clasificada por dominio, nivel y manifestaciones, para que la evidencia se organice sola contra la rúbrica oficial.

#### Acceptance Criteria
1. WHEN existe el texto de una observación THEN el sistema SHALL estimar el `nivel_estimado` (1–9) y el/los dominio(s) correspondientes.
2. WHEN se clasifica una observación THEN el sistema SHALL vincularla con una o más manifestaciones (`manifestaciones`) de su nivel.
3. WHEN se completa la clasificación THEN el sistema SHALL presentar a la educadora la clasificación propuesta para que la confirme o la corrija antes de guardarla definitivamente.
4. WHEN la educadora corrige la clasificación THEN el sistema SHALL persistir los valores corregidos.

## Requirement 4 — Persistencia en dos bases de datos

**User Story:** Como sistema, necesito guardar los datos de personas en una base relacional y las transcripciones en una base vectorial, para soportar consultas estructuradas y búsqueda semántica (RAG).

#### Acceptance Criteria
1. The relational database SHALL contain las tablas del dataset E-1 (`jardines`, `educadoras`, `ninos`, `ruta_niveles`, `manifestaciones`, `observaciones`, `observacion_manifestaciones`) más `bitacoras`, `recomendaciones`, `rubrica_versiones` y `reportes_direccion`.
2. WHEN se guarda una observación con su texto transcrito THEN el sistema SHALL generar un embedding del texto y SHALL indexarlo en la base vectorial junto con metadatos (`id_observacion`, `id_nino`, dominio, nivel, fecha, formato).
3. The embedding provider SHALL be accessed through an interface (`EmbeddingProvider`) with interchangeable AWS (Titan) and mock implementations.
4. The relational and vector repositories SHALL be accessed through repository interfaces (no direct SDK coupling in services).

## Requirement 5 — Bitácora quincenal (Modelo 2, RAG + LLM)

**User Story:** Como educadora, quiero que el sistema redacte una bitácora quincenal de cada niño/a basada en la evidencia real, para revisarla y aprobarla en vez de escribirla.

#### Acceptance Criteria
1. WHEN se solicita la bitácora de un niño/a para un período THEN el sistema SHALL recuperar las observaciones relevantes del período (relacional + búsqueda semántica).
2. WHEN se genera la bitácora THEN el sistema SHALL usar un LLM (Amazon Bedrock en AWS; mock en local) con la evidencia recuperada y la rúbrica como contexto.
3. WHEN se genera la bitácora THEN cada afirmación relevante SHALL ser trazable a las observaciones/manifestaciones que la respaldan.
4. WHEN se genera una bitácora THEN el sistema SHALL guardarla en estado "borrador".
5. WHEN la educadora revisa una bitácora THEN el sistema SHALL permitir editarla y cambiarla a estado "aprobada".
6. The LLM provider SHALL be accessed through an interface (`LlmProvider`) with interchangeable Bedrock and mock implementations.

## Requirement 6 — Recomendación de nivel en tiempo real (Modelo 3, rúbrica + LLM)

**User Story:** Como educadora, quiero pedir en cualquier momento una recomendación de si un niño/a debe avanzar, mantenerse o retroceder de nivel, con argumentos claros, para decidir sin leer punto por punto toda su trayectoria.

#### Acceptance Criteria
1. WHEN la educadora pulsa "¿Puede subir de nivel?" en la ficha de un niño/a THEN el sistema SHALL devolver una de tres decisiones: AVANZAR, MANTENER o RETROCEDER.
2. The decision SHALL be computed by a **deterministic rubric** (reglas y umbrales estrictos), NOT by the LLM. The LLM SHALL only produce the human-readable argument.
3. WHEN se calcula la recomendación THEN la rúbrica SHALL evaluar: cobertura de los 5 dominios del nivel actual, consistencia del `nivel_estimado` en las últimas N observaciones, tendencia (ascendente/estable/descendente) y señales de retroceso (observaciones sostenidas bajo el nivel asignado).
4. WHEN se devuelve una recomendación THEN el sistema SHALL incluir decisión, score, dominios cubiertos, dominios pendientes, evidencia citada y la `version_rubrica` usada.
5. The rubric criteria SHALL be stored as versioned configuration (`rubrica_versiones`), configurable without code changes.
6. WHEN se registra una observación/bitácora nueva que cruza el umbral de la rúbrica THEN el sistema SHALL mostrar una sugerencia proactiva de avance.
7. WHEN la educadora responde a una recomendación THEN el sistema SHALL registrar su decisión final (aceptó / rechazó / ajustó). La decisión final SHALL ser siempre humana.

## Requirement 7 — Reporte de dirección (Modelo 4)

**User Story:** Como directora de jardín, quiero un reporte agregado de la actividad y los niveles de los niños/as de mi jardín, para supervisar el avance sin revisar caso por caso.

#### Acceptance Criteria
1. WHEN la directora solicita el reporte de un período THEN el sistema SHALL calcular, por jardín/sala: cuántos niños/as subieron, mantuvieron o bajaron de nivel.
2. WHEN se genera el reporte THEN el sistema SHALL incluir la distribución de niveles (por sala y por dominio), el conteo de observaciones y bitácoras (total y por educadora), y alertas (niños/as con señal de retroceso o sin observaciones recientes).
3. WHEN se genera el reporte THEN el sistema SHALL incluir el KPI de tiempo de documentación ahorrado a nivel jardín.
4. WHEN se genera el reporte THEN el sistema SHALL producir un resumen ejecutivo narrativo (LLM) a partir de las métricas agregadas.
5. The aggregated metrics SHALL be computed from the relational database (not inferred by the LLM).

## Requirement 8 — Roles y navegación

**User Story:** Como usuario, quiero que la app muestre las funciones según mi rol (educadora o directora), para ver solo lo que me corresponde.

#### Acceptance Criteria
1. The system SHALL support two roles: `educadora` and `directora`.
2. WHEN el rol es educadora THEN la app SHALL mostrar Mi sala, Capturar, Ficha del niño/a, Bitácoras y Recomendaciones.
3. WHEN el rol es directora THEN la app SHALL mostrar el Dashboard de dirección.
4. For the demo, role selection SHALL be a simple selector (no real authentication required).

## Requirement 9 — Frontend mobile-first (PWA)

**User Story:** Como educadora, quiero usar la app cómodamente desde el celular estando de pie en la sala, para registrar observaciones sin fricción.

#### Acceptance Criteria
1. The frontend SHALL be a mobile-first PWA (React + Vite) usable desde celular/tablet.
2. The UI SHALL present botones grandes y accesibles, feedback inmediato de procesamiento, y estar en español (Chile).
3. The UI SHALL mostrar un banner permanente indicando que los datos son sintéticos y de uso pedagógico.
4. The visual design SHALL follow the provided Figma mockups once available; until then, the UI SHALL be implemented with placeholder styling that respects the pantallas y flujos definidos.
5. The frontend SHALL communicate with the backend solo vía la API REST (sin lógica de negocio en el cliente).

## Requirement 10 — Modo demo sin AWS y datos sembrados

**User Story:** Como presentador en la hackathon, quiero que todo el sistema corra sin credenciales AWS y con datos realistas, para demostrarlo de forma confiable aunque la red falle.

#### Acceptance Criteria
1. WHEN `USE_MOCKS=true` THEN todos los providers de IA (transcripción, embeddings, LLM) y de almacenamiento SHALL devolver respuestas plausibles sin llamar a AWS.
2. The system SHALL incluir un script de seed que carga el dataset E-1 en la base relacional y la vectorial.
3. The system SHALL correr con un único comando (p. ej. docker-compose) y SHALL incluir un README con instrucciones.
4. WHEN se proporcionan credenciales AWS y `USE_MOCKS=false` THEN el sistema SHALL usar los servicios AWS reales a través de las mismas interfaces.

## Requirement 11 — Resguardo de datos sensibles

**User Story:** Como institución, necesito que la información sensible de los niños/as esté protegida, para cumplir con el resguardo exigido por el desafío.

#### Acceptance Criteria
1. The system SHALL identificar a los niños/as solo por `id_nino` seudónimo (sin nombres reales ni RUT) en base de datos y en prompts al LLM.
2. The prompts enviados al LLM SHALL contener solo texto despersonalizado y la rúbrica.
3. The media files SHALL almacenarse cifrados en reposo (S3) y servirse mediante URLs prefirmadas de corta duración en el camino AWS.
4. The datos personales (relacional) y el contenido (vectorial) SHALL mantenerse en almacenes separados.
