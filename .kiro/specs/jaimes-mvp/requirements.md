# Requirements Document

**jAImes MVP**

## Introduction

jAImes es una herramienta de IA para Fundación Integra (desafío "IA para el Desarrollo Infantil: de la Observación a la Acción", AWS Breaking Barriers Chile 2026). Su propósito es reducir el tiempo que las educadoras de párvulos ("tías") dedican a documentar (~4 h/semana) hacia ~0 h, convirtiendo automáticamente los recursos crudos que ya generan (texto, fotos de notas manuscritas, audios, videos) en observaciones estructuradas, trayectorias de desarrollo, bitácoras quincenales, recomendaciones de nivel y reportes de dirección.

El sistema se apoya en el **dataset oficial E-1** (sintético y seudonimizado, de uso pedagógico, no clínico ni diagnóstico): una ruta de 9 niveles de desarrollo × 5 dominios (cognitivo, lenguaje_comunicacion, motor_fino, motor_grueso, socioemocional) con 90 manifestaciones observables, y tablas relacionales de jardines, educadoras, niños, observaciones y vínculos de evidencia. El dataset oficial se distribuye como `dataset_e1_publico.zip` con siete CSV relacionales más `consolidado.json`, es reproducible de forma determinista con su generador y validable con su validador, y constituye la fuente de verdad para pruebas, validación y evaluación de los modelos de IA.

**Decisión arquitectónica central:** AWS es el camino **primario y real**, no una opción secundaria. El despliegue objetivo es **serverless** sobre AWS (API Gateway + Lambda con FastAPI envuelto por Mangum, Aurora Serverless v2 con PostgreSQL + pgvector, S3, Bedrock con Claude y Titan, Transcribe, Textract, Rekognition, Secrets Manager, CloudWatch), con Infraestructura como Código en **AWS CDK (Python)**. Los **mocks** siguen existiendo detrás de las mismas interfaces como camino **secundario** para desarrollo local y CI sin credenciales, no como la ruta principal.

**Restricciones transversales:**
- Datos sintéticos y seudonimizados; no es instrumento clínico ni diagnóstico.
- Backend en Python (FastAPI), POO + SOLID, arquitectura en 3 capas.
- Dos bases de datos lógicas: relacional (personas/entidades) y vectorial (transcripciones/embeddings para RAG), ambas sobre Aurora Serverless v2 (PostgreSQL + pgvector).
- Despliegue serverless primario en AWS mediante CDK; **modo mock** secundario que permite correr pruebas locales/CI sin credenciales AWS tras las mismas interfaces.
- Frontend mobile-first (PWA). El diseño visual seguirá los mockups de Figma (pendientes); la lógica la define el backend.
- **Dataset oficial E-1 como fuente de verdad:** el dataset sintético oficial (7 CSV + `consolidado.json`, 500 niños/as, reproducible de forma determinista) se usa para sembrar las bases, para las pruebas y para ejercitar y evaluar los 4 modelos de IA; el dataset reducido/casero queda solo como respaldo rápido de pruebas.
- **Rúbrica oficial como fuente de verdad de los criterios de decisión de nivel:** la rúbrica oficial (estructurada como tramo de sala × núcleo × 8 niveles de progresión, con un descriptor esperado y una lista de conductas observables por nivel) es la fuente de verdad de los criterios con que se decide AVANZAR/MANTENER/RETROCEDER. La decisión es determinista (la rúbrica decide), y el argumento de la recomendación se fundamenta citando las conductas observables aplicables y las observaciones/experiencias previas (evidencia vía RAG), de modo que ahorra tiempo a la educadora (ligado al KPI de reducción del tiempo de documentación). La rúbrica es multi-núcleo (iniciando con "Identidad y Autonomía") y se versiona en `rubrica_versiones.criterios`.

## Glossary

- **Sistema jAImes**: la aplicación completa (frontend PWA + backend FastAPI + bases de datos + proveedores de IA).
- **Backend**: la capa de lógica de negocio en FastAPI (routers, servicios, dominio, proveedores, repositorios).
- **Frontend**: la PWA React + Vite (capa de presentación).
- **Proveedor de IA (Provider)**: adaptador detrás de una interfaz (`TranscriptionProvider`, `EmbeddingProvider`, `LlmProvider`, `Classifier`) con implementación AWS primaria y mock secundaria.
- **Repositorio (Repo)**: abstracción de acceso a datos (`RelationalRepo`, `VectorRepo`, `StorageRepo`).
- **Rúbrica de decisión**: componente determinista y versionado (`RubricaDecision`) que decide AVANZAR/MANTENER/RETROCEDER.
- **Rúbrica oficial**: la rúbrica oficial del programa, estructurada como tramo de sala × núcleo × 8 niveles de progresión, donde cada nivel tiene un descriptor esperado y una lista de conductas observables. Es la fuente de verdad de los criterios de decisión de nivel, se versiona en `rubrica_versiones.criterios` y es multi-núcleo (iniciando con "Identidad y Autonomía"). La rúbrica define los criterios; `RubricaDecision` los aplica de forma determinista y el `LlmProvider` solo argumenta citándolos.
- **Tramo de sala**: segmento etario de la sala en que se agrupa a los niños/as, con exactamente tres valores: Sala Cuna, Nivel Medio y Transición. Determina qué conductas observables de la rúbrica oficial aplican a un niño/a según su rango etario.
- **Núcleo**: ámbito de desarrollo evaluado por la rúbrica oficial (por ejemplo, Identidad y Autonomía). La rúbrica es multi-núcleo; se inicia con "Identidad y Autonomía" y se agregan núcleos adicionales (p. ej. lenguaje, pensamiento matemático, corporalidad) como datos versionados, sin cambios de código.
- **Nivel de progresión**: cada uno de los 8 niveles de la rúbrica oficial dentro de un tramo×núcleo, en orden fijo: 1 Comenzando, 2 Explorando, 3 Desarrollando, 4 Afianzando, 5 Integrando, 6 Ampliando, 7 Consolidando, 8 Profundizando. Cada nivel incluye un descriptor de desarrollo y aprendizaje esperado.
- **Conducta observable**: comportamiento concreto esperado en un nivel de progresión (con ejemplos), que el sistema reconoce a partir de la evidencia (observaciones previas). Se usa como criterio de evidencia para la decisión de nivel: se marca como cubierta cuando hay evidencia que la respalde y como pendiente cuando no la hay.
- **Modo mock**: configuración `USE_MOCKS=true` que selecciona adaptadores mock e infraestructura local (SQLite + índice vectorial en memoria + almacenamiento local).
- **IaC**: Infraestructura como Código, implementada con AWS CDK en Python.
- **Dataset E-1**: datos sintéticos y seudonimizados de ruta de niveles, manifestaciones, jardines, educadoras, niños y observaciones.
- **Dataset E-1 oficial**: el dataset sintético (ficticio) oficial del desafío, de uso pedagógico y no clínico ni diagnóstico. Se distribuye a los participantes únicamente como `dataset_e1_publico.zip` (el zip interno de validación NO se distribuye) y contiene la carpeta `datos_publicos/` con SIETE CSV relacionales más `consolidado.json`, documentados por `diccionario_datos.md`, `ejemplos_trayectorias.md` y `distribucion_y_validacion.md`. Es reproducible de forma determinista con `generador.py` y validable con `validador.py` bajo Python 3.12.15 (solo biblioteca estándar), con semilla fija `20261013`, fecha de referencia `2026-10-13`, codificación UTF-8, saltos de línea LF y orden canónico, de modo que una segunda ejecución limpia produce una salida idéntica bit a bit (hashes publicados). Escala: 500 niños/as, de los cuales 60 tienen solo 1–2 observaciones (ingreso reciente) y 440 tienen entre 4 y 9. Una nota vacía significa ausencia de nota opcional; una observación, formato o manifestación ausente significa únicamente que no fue registrada.
- **Dataset reducido (casero)**: subconjunto o dataset mínimo generado localmente, usado solo como respaldo rápido para pruebas veloces, nunca como fuente de verdad.
- **id_nino**: identificador seudónimo de un niño/a (sin nombre real ni RUT).

---

## Requirements

### Requirement 1: Captura multi-formato de evidencia

**User Story:** Como educadora, quiero registrar lo que observo de un niño/a mediante texto, audio, foto o video desde mi celular, para no tener que escribir informes manualmente.

#### Acceptance Criteria
1. WHEN la educadora ha seleccionado un `id_nino` válido y envía contenido de tipo texto, audio, foto o video cuyo formato es soportado y cuyo tamaño no excede 100 MB THEN el Sistema jAImes SHALL aceptar el medio y SHALL crear exactamente una observación asociada al `id_nino` seleccionado y a la `id_educadora` de la sesión.
2. WHEN se acepta un medio no textual (audio, foto o video) THEN el Sistema jAImes SHALL almacenar el archivo original en object storage mediante `StorageRepo` (Amazon S3 en el camino AWS primario; almacenamiento local en modo mock) y SHALL asociar su ubicación a la observación creada.
3. IF la carga no incluye un `id_nino` seleccionado o una `id_educadora` de sesión THEN THE Sistema jAImes SHALL rechazar la carga con un código HTTP 400 y un mensaje de error en español, y SHALL NOT crear ninguna observación ni almacenar archivo alguno.
4. IF el formato del archivo no está entre los formatos soportados (texto: txt; audio: mp3, m4a, wav; foto: jpg, jpeg, png; video: mp4, mov) o su tamaño excede 100 MB THEN THE Sistema jAImes SHALL rechazar la carga con un código HTTP 400 y un mensaje de error en español que indique el formato o límite de tamaño admitido, y SHALL NOT crear ninguna observación ni almacenar archivo alguno.
5. WHEN se crea una observación THEN el Sistema jAImes SHALL registrar la fecha de observación y el `formato_captura` con exactamente uno de los valores: texto, audio, foto o video.

### Requirement 2: Transcripción y extracción de texto (Modelo 1)

**User Story:** Como educadora, quiero que mis audios, videos y fotos de notas se conviertan automáticamente en texto, para que el sistema pueda analizarlos sin que yo transcriba nada.

#### Acceptance Criteria
1. WHEN se sube un audio de tamaño menor o igual a 100 MB THEN el Sistema jAImes SHALL transcribirlo a texto en español mediante `TranscriptionProvider` (Amazon Transcribe en el camino AWS primario; mock en modo local) en un plazo máximo de 300 segundos.
2. WHEN se sube una foto de una nota manuscrita de tamaño menor o igual a 10 MB THEN el Sistema jAImes SHALL extraer el texto por OCR mediante `TranscriptionProvider` (Amazon Textract en el camino AWS primario; mock en modo local) en un plazo máximo de 60 segundos.
3. WHEN se sube un video de tamaño menor o igual a 500 MB THEN el Sistema jAImes SHALL transcribir su audio a texto en español mediante `TranscriptionProvider` (Amazon Transcribe en el camino AWS primario; mock en modo local).
4. WHEN se procesa un video THEN el Sistema jAImes SHALL obtener metadatos de escena mediante `TranscriptionProvider` (Amazon Rekognition en el camino AWS primario; mock en modo local).
5. WHEN el contenido es texto directo de entre 1 y 50.000 caracteres THEN el Sistema jAImes SHALL usarlo sin transcripción.
6. IF un medio excede el tamaño máximo de su formato, tiene un formato no soportado o está corrupto THEN THE Sistema jAImes SHALL rechazar la transcripción con un mensaje de error en español, sin crear texto transcrito ni alterar la observación.
7. IF la transcripción mediante `TranscriptionProvider` falla o excede su plazo máximo THEN THE Sistema jAImes SHALL reintentar hasta 3 veces y, si persiste el fallo, SHALL marcar la observación como pendiente de transcripción con un mensaje de error en español.
8. THE `TranscriptionProvider` SHALL exponerse como una interfaz con implementaciones AWS (primaria) y mock (secundaria) intercambiables, seleccionables por la configuración `USE_MOCKS`.

### Requirement 3: Clasificación automática de la observación

**User Story:** Como educadora, quiero que cada observación quede clasificada por dominio, nivel y manifestaciones, para que la evidencia se organice sola contra la rúbrica oficial.

#### Acceptance Criteria
1. WHEN existe el texto no vacío de una observación THEN el `Classifier` SHALL estimar el `nivel_estimado` como un entero entre 1 y 9 y entre 1 y 5 dominios del conjunto cerrado (cognitivo, lenguaje_comunicacion, motor_fino, motor_grueso, socioemocional).
2. WHEN el `Classifier` estima nivel y dominios THEN SHALL vincular la observación con entre 1 y 10 manifestaciones cuyo nivel sea igual al `nivel_estimado` y cuyo dominio pertenezca a los dominios estimados.
3. WHEN se completa la clasificación THEN el Sistema jAImes SHALL presentar a la educadora la clasificación propuesta sin persistirla definitivamente, para que la confirme o la corrija.
4. WHEN la educadora confirma o corrige la clasificación propuesta THEN el Sistema jAImes SHALL persistir los valores resultantes mediante `RelationalRepo`.
5. IF el texto de la observación está vacío o la confianza de la clasificación es baja THEN THE Sistema jAImes SHALL marcar la observación como pendiente de clasificación manual, conservando su texto sin descartarlo.
6. IF la persistencia mediante `RelationalRepo` falla THEN THE Sistema jAImes SHALL conservar los valores previos sin aplicar cambios parciales y SHALL devolver un mensaje de error en español.

### Requirement 4: Persistencia en bases de datos relacional y vectorial

**User Story:** Como sistema, necesito guardar los datos de personas en una base relacional y las transcripciones en una base vectorial, para soportar consultas estructuradas y búsqueda semántica (RAG).

#### Acceptance Criteria
1. THE base de datos relacional SHALL contener las tablas del dataset E-1 (`jardines`, `educadoras`, `ninos`, `ruta_niveles`, `manifestaciones`, `observaciones`, `observacion_manifestaciones`) más `bitacoras`, `recomendaciones`, `rubrica_versiones` y `reportes_direccion`.
2. WHEN se guarda una observación con su texto transcrito, THE Sistema jAImes SHALL generar un embedding del texto mediante la implementación activa de `EmbeddingProvider`.
3. WHEN se ha generado el embedding de una observación, THE Sistema jAImes SHALL indexarlo en la base vectorial con los metadatos `id_observacion`, `id_nino`, dominio, nivel, fecha y formato, de forma que una búsqueda posterior por `id_observacion` recupere exactamente un registro con esos seis metadatos.
4. IF la generación del embedding o su indexación en la base vectorial falla, THEN THE Sistema jAImes SHALL conservar la observación en la base relacional sin registro vectorial asociado y SHALL devolver un error indicando que la indexación vectorial no se completó.
5. THE `EmbeddingProvider` SHALL exponerse como una interfaz con dos implementaciones intercambiables mediante configuración: AWS (Amazon Titan) como primaria y mock como secundaria, de modo que al seleccionar una implementación todas las operaciones de embedding se dirijan solo a esa implementación.
6. THE base relacional y la base vectorial SHALL residir sobre Aurora Serverless v2 (PostgreSQL + pgvector) en el camino AWS primario, y sobre SQLite más un índice vectorial en memoria en modo mock.
7. THE repositorios relacional y vectorial SHALL accederse únicamente mediante las interfaces `RelationalRepo` y `VectorRepo`, de modo que los servicios no referencien directamente ningún SDK de base de datos.

### Requirement 5: Bitácora quincenal (Modelo 2, RAG + LLM)

**User Story:** Como educadora, quiero que el sistema redacte una bitácora quincenal de cada niño/a basada en la evidencia real, para revisarla y aprobarla en vez de escribirla.

#### Acceptance Criteria
1. WHEN se solicita la bitácora de un niño/a para un período quincenal definido por una fecha de inicio y una fecha de fin (ventana de 14 días) THEN el `BitacoraService` SHALL recuperar, mediante `RelationalRepo`, las observaciones del `id_nino` cuya fecha de observación esté dentro del período, y SHALL complementarlas mediante búsqueda semántica en `VectorRepo` recuperando hasta las 20 observaciones más similares del mismo `id_nino` restringidas a la ventana del período.
2. IF no existe ninguna observación del `id_nino` dentro del período solicitado THEN THE `BitacoraService` SHALL abortar la generación, SHALL no crear ninguna bitácora y SHALL devolver un código HTTP 422 con un mensaje de error en español indicando que no hay evidencia suficiente en el período.
3. WHEN se genera la bitácora THEN el `BitacoraService` SHALL usar un LLM mediante `LlmProvider` (Amazon Bedrock con Claude en el camino AWS primario; mock en modo local) con la evidencia recuperada en el criterio 1 y la rúbrica vigente como contexto.
4. IF la invocación al LLM mediante `LlmProvider` falla o excede un tiempo máximo de 60 segundos THEN THE `BitacoraService` SHALL abortar la generación, SHALL no crear ninguna bitácora en estado "borrador" y SHALL devolver un código HTTP 503 con un mensaje de error en español indicando que la generación no pudo completarse.
5. WHEN se genera la bitácora THEN cada afirmación evaluativa del texto generado SHALL citar al menos una observación o manifestación de la evidencia recuperada que la respalde, identificada por su `id_observacion` o por el identificador de la manifestación.
6. WHEN se genera una bitácora correctamente THEN el Sistema jAImes SHALL persistirla mediante `RelationalRepo` con estado "borrador".
7. WHILE una bitácora está en estado "borrador" THE Sistema jAImes SHALL permitir a la educadora editar su texto y persistir los cambios mediante `RelationalRepo`.
8. WHEN la educadora aprueba una bitácora que está en estado "borrador" THEN el Sistema jAImes SHALL cambiar su estado a "aprobada" y SHALL persistir el cambio mediante `RelationalRepo`.
9. IF la educadora intenta editar una bitácora que ya está en estado "aprobada" THEN THE Sistema jAImes SHALL rechazar la operación con un código HTTP 409 y un mensaje de error en español.
10. THE `LlmProvider` SHALL exponerse como una interfaz con implementaciones AWS (Amazon Bedrock, primaria) y mock (secundaria) intercambiables, seleccionables por la configuración `USE_MOCKS`.

### Requirement 6: Recomendación de nivel en tiempo real (Modelo 3, rúbrica + LLM)

**User Story:** Como educadora, quiero pedir en cualquier momento una recomendación de si un niño/a debe avanzar, mantenerse o retroceder de nivel, fundamentada en las conductas observables de la rúbrica oficial y en la evidencia previa del niño/a, para decidir sin leer punto por punto toda su trayectoria.

#### Acceptance Criteria
1. WHEN la educadora pulsa "¿Puede subir de nivel?" en la ficha de un niño/a THEN el `RecommendationService` SHALL devolver, en 10 segundos o menos, exactamente una de tres decisiones: AVANZAR, MANTENER o RETROCEDER.
2. THE decisión de nivel SHALL ser calculada de forma determinista por `RubricaDecision` aplicando las conductas observables y los umbrales de la rúbrica oficial definidos en `rubrica_versiones.criterios`, de modo que dos ejecuciones con los mismos datos de entrada y la misma `version_rubrica` produzcan siempre la misma decisión; el `LlmProvider` SHALL producir únicamente el argumento legible por humanos y SHALL NOT alterar la decisión.
3. WHEN se calcula la recomendación THEN `RubricaDecision` SHALL identificar el tramo de sala, el núcleo y el nivel de progresión actual del niño/a, y SHALL evaluar, para ese tramo × núcleo × nivel actual, cuáles conductas observables están cubiertas y cuáles pendientes, derivándolo de la evidencia previa del niño/a (observaciones y manifestaciones del `RelationalRepo` complementadas con la búsqueda semántica en `VectorRepo`).
4. WHEN se evalúa la cobertura THEN `RubricaDecision` SHALL decidir AVANZAR cuando el niño/a cubre el umbral requerido de conductas observables del nivel actual en los núcleos requeridos, MANTENER cuando la cobertura de conductas observables es parcial, y RETROCEDER cuando existe evidencia sostenida por debajo del nivel actual, definida como una racha de al menos 3 observaciones consecutivas con `nivel_estimado` por debajo del nivel asignado.
5. WHEN se devuelve una recomendación THEN el `RecommendationService` SHALL incluir la decisión, el tramo de sala, el núcleo, el nivel de progresión actual, el `score` como valor numérico entre 0.00 y 1.00, la lista de conductas observables cubiertas, la lista de conductas observables pendientes, la evidencia citada (observaciones referenciadas por su identificador) y la `version_rubrica` usada.
6. THE criterios de la rúbrica oficial (tramos, núcleos, niveles de progresión, descriptores, conductas observables y umbrales) SHALL almacenarse como configuración versionada en `rubrica_versiones.criterios`, modificable sin cambios de código, y cada recomendación SHALL referenciar la `version_rubrica` vigente al momento del cálculo.
7. WHEN se genera el argumento legible THEN el `LlmProvider` SHALL recibir como contexto las conductas observables cubiertas y pendientes y las observaciones/experiencias previas (evidencia vía RAG), y SHALL argumentar citando las conductas observables específicas y las observaciones previas (por su identificador) que justifican la decisión, sin alterar la decisión determinista.
8. WHEN se registra una observación o bitácora nueva que hace que el `score` del niño/a alcance o supere el umbral de avance definido en `rubrica_versiones.criterios` THEN el Sistema jAImes SHALL mostrar, en 5 segundos o menos tras completar el registro, una sugerencia proactiva de avance en la ficha del niño/a.
9. WHEN la educadora responde a una recomendación THEN el Sistema jAImes SHALL registrar su decisión final como uno de los valores aceptó, rechazó o ajustó en `decision_educadora`, persistiendo dicho valor de forma que la decisión final siempre sea humana.
10. IF al solicitar una recomendación el niño/a tiene menos de 5 observaciones registradas THEN el `RecommendationService` SHALL abstenerse de emitir una decisión, SHALL devolver un indicador de datos insuficientes señalando cuántas observaciones faltan y SHALL NOT persistir una recomendación.
11. IF el `LlmProvider` no logra generar el argumento legible dentro de 10 segundos o devuelve un error THEN el `RecommendationService` SHALL conservar y devolver la decisión determinista con sus conductas observables cubiertas y pendientes y su `score`, SHALL indicar que el argumento no está disponible y SHALL NOT descartar la decisión calculada.

### Requirement 7: Reporte de dirección (Modelo 4)

**User Story:** Como directora de jardín, quiero un reporte agregado de la actividad y los niveles de los niños/as de mi jardín, para supervisar el avance sin revisar caso por caso.

#### Acceptance Criteria
1. WHEN la directora solicita el reporte indicando un `id_jardin` y un período definido por fecha de inicio y fecha de fin (ambas inclusivas, con fecha de inicio menor o igual a la fecha de fin) THEN el `DirectorReportService` SHALL calcular, por jardín y por sala, el conteo de niños/as que subieron, mantuvieron o bajaron de nivel dentro del período, donde cada niño/a se cuenta en exactamente una de las tres categorías comparando su nivel al cierre del período contra su nivel al inicio del período.
2. IF el período solicitado tiene fecha de inicio posterior a la fecha de fin, o alguna de las fechas tiene formato inválido, THEN THE `DirectorReportService` SHALL rechazar la solicitud sin generar reporte y SHALL devolver un error en español que indique que el rango de fechas es inválido, preservando el estado de datos sin cambios.
3. WHEN se genera el reporte THEN el `DirectorReportService` SHALL incluir la distribución de niveles por sala y por dominio, el conteo de observaciones y bitácoras (total y por educadora), las alertas de niños/as con señal de retroceso (una o más observaciones con `nivel_estimado` bajo el nivel asignado dentro del período) y las alertas de niños/as sin observaciones registradas en los últimos 14 días previos a la fecha de fin del período.
4. WHEN se genera el reporte THEN el `DirectorReportService` SHALL incluir el KPI de tiempo de documentación ahorrado a nivel jardín, calculado de forma determinista a partir del volumen de observaciones y bitácoras generadas en el período.
5. WHEN existen métricas agregadas del período THEN el `DirectorReportService` SHALL producir un resumen ejecutivo narrativo en español mediante `LlmProvider` a partir únicamente de dichas métricas agregadas.
6. IF `LlmProvider` no logra producir el resumen ejecutivo narrativo THEN THE `DirectorReportService` SHALL entregar el reporte con las métricas agregadas calculadas y SHALL indicar que el resumen narrativo no está disponible, sin descartar las métricas ya calculadas.
7. WHEN un jardín o una sala no tiene datos en el período solicitado THEN el `DirectorReportService` SHALL generar el reporte con conteos y distribuciones en cero para ese jardín o sala, sin producir un error.
8. THE métricas agregadas SHALL calcularse desde la base de datos relacional mediante `RelationalRepo`, sin ser inferidas por el `LlmProvider`.

### Requirement 8: Roles y navegación

**User Story:** Como usuario, quiero que la app muestre las funciones según mi rol (educadora o directora), para ver solo lo que me corresponde.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL soportar exactamente dos roles mutuamente excluyentes: `educadora` y `directora`.
2. WHEN el rol activo es `educadora`, THE Frontend SHALL mostrar únicamente las secciones Mi sala, Capturar, Ficha del niño/a, Bitácoras y Recomendaciones, y SHALL ocultar el Dashboard de dirección.
3. WHEN el rol activo es `directora`, THE Frontend SHALL mostrar únicamente la sección Dashboard de dirección, y SHALL ocultar las secciones Mi sala, Capturar, Ficha del niño/a, Bitácoras y Recomendaciones.
4. WHERE el entorno es la demo, THE Frontend SHALL permitir la selección de rol mediante un selector con las dos opciones (`educadora` y `directora`), sin requerir autenticación real.
5. IF ningún rol ha sido seleccionado, THEN THE Frontend SHALL impedir el acceso a las secciones específicas de rol y SHALL mostrar un indicador que solicite seleccionar un rol.
6. WHEN el usuario cambia el rol activo mediante el selector, THE Frontend SHALL actualizar las secciones visibles conforme al nuevo rol en un máximo de 1 segundo.

### Requirement 9: Frontend mobile-first (PWA)

**User Story:** Como educadora, quiero usar la app cómodamente desde el celular estando de pie en la sala, para registrar observaciones sin fricción.

#### Acceptance Criteria
1. THE Frontend SHALL ser una PWA mobile-first construida con React y Vite, con diseño responsivo usable en anchos de viewport desde 320 px hasta 1024 px, cubriendo celular y tablet.
2. THE Frontend SHALL presentar controles interactivos (botones y campos táctiles) con un área mínima de 44 x 44 px CSS, operables mediante toque, y con contenido textual en español (Chile).
3. WHEN la educadora inicia una acción que requiere procesamiento (envío o guardado de una observación), THE Frontend SHALL mostrar un indicador visual de progreso en un plazo máximo de 100 ms desde la interacción y mantenerlo hasta recibir la respuesta del Backend.
4. WHILE cualquier pantalla de la aplicación esté visible, THE Frontend SHALL mostrar un banner visible y persistente que indique que los datos son sintéticos y de uso pedagógico.
5. THE diseño visual SHALL seguir los mockups de Figma una vez disponibles; hasta entonces, el Frontend SHALL implementarse con estilo placeholder que respete las pantallas y flujos definidos. El Frontend es una tarea posterior construida a partir de los mockups de Figma.
6. THE Frontend SHALL comunicarse con el Backend únicamente mediante la API REST, sin ejecutar lógica de negocio en el cliente.
7. IF una solicitud a la API REST del Backend falla o no responde dentro de 10 segundos, THEN THE Frontend SHALL mostrar un mensaje de error que indique que la operación no pudo completarse y SHALL conservar los datos ingresados por la educadora sin descartarlos.

### Requirement 10: Despliegue AWS serverless primario y modo demo

**User Story:** Como equipo de la hackathon, quiero que el sistema se despliegue en una arquitectura cloud AWS real y básica, y además pueda correr localmente sin credenciales, para demostrarlo en vivo contra servicios reales y, de forma secundaria, tener respaldo offline si la red falla.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL desplegarse en AWS como arquitectura serverless primaria mediante Infraestructura como Código con AWS CDK en Python (API Gateway + Lambda con FastAPI y Mangum, Aurora Serverless v2 con pgvector, S3, Bedrock, Transcribe, Textract, Rekognition, Secrets Manager, CloudWatch).
2. WHEN se ejecuta el flujo de despliegue documentado (`cdk synth` seguido de `cdk deploy`) THEN el Sistema jAImes SHALL quedar accesible mediante API Gateway y SHALL responder al endpoint `/health` con código HTTP 200 en 5 segundos o menos.
3. WHEN el sistema está desplegado en AWS con `USE_MOCKS=false` THEN el Sistema jAImes SHALL enrutar todas las operaciones de IA y almacenamiento a los servicios AWS reales (Bedrock, Transcribe, Textract, Rekognition, S3, Aurora) a través de las interfaces de proveedores y repositorios.
4. THE Sistema jAImes SHALL incluir pruebas de integración cloud que invoquen servicios AWS reales (Bedrock, Transcribe, Textract, S3, Aurora) en una cuenta sandbox, ejecutables bajo demanda mediante un marcador o comando dedicado y separadas de la suite rápida de CI.
5. IF el despliegue mediante `cdk deploy` falla THEN THE Sistema jAImes SHALL reportar el stack y el recurso que causó el fallo y SHALL dejar el entorno en un estado que permita reintentar el despliegue.
6. IF una invocación a un servicio AWS real falla cuando `USE_MOCKS=false` THEN THE Sistema jAImes SHALL registrar el error en CloudWatch y SHALL devolver al cliente un mensaje de error en español sin exponer detalles sensibles.
7. WHERE la configuración es `USE_MOCKS=true` THEN todos los proveedores de IA (transcripción, embeddings, LLM) y de almacenamiento SHALL devolver respuestas derivadas del dataset E-1 sin realizar llamadas de red a AWS.
8. THE Sistema jAImes SHALL incluir un script de seed que carga el **Dataset E-1 oficial** (los siete CSV relacionales más `consolidado.json`) como fuente de verdad en la base relacional y en la vectorial, adaptando el cargador para leer los siete CSV en lugar de archivos JSON individuales, ejecutable tanto en el entorno AWS como en modo mock.
9. WHEN se ejecuta el script de seed del Dataset E-1 oficial THEN el Sistema jAImes SHALL validar los conteos cargados contra los valores de referencia de `distribucion_y_validacion` y SHALL rechazar el seed con un mensaje de error en español si algún conteo no coincide.
10. THE Sistema jAImes SHALL incluir una verificación de reproducibilidad del Dataset E-1 oficial que vuelva a ejecutar `generador.py` con la semilla fija `20261013` y la fecha de referencia `2026-10-13` y SHALL confirmar que la salida es idéntica bit a bit a la publicada (hashes coincidentes) y que `validador.py` pasa sin errores.
11. WHERE se requiera una ejecución de pruebas veloz THEN el Sistema jAImes SHALL permitir usar un dataset reducido (casero) únicamente como respaldo rápido de pruebas, sin reemplazar al Dataset E-1 oficial como fuente de verdad.
12. THE Sistema jAImes SHALL poder iniciarse localmente mediante un único comando documentado (por ejemplo docker-compose up) y SHALL incluir un README con las instrucciones de despliegue AWS y de ejecución local.

### Requirement 11: Resguardo de datos sensibles

**User Story:** Como institución, necesito que la información sensible de los niños/as esté protegida, para cumplir con el resguardo exigido por el desafío.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL identificar a los niños/as únicamente mediante el identificador seudónimo `id_nino`, sin almacenar ni transmitir nombres reales, RUT u otros datos directamente identificatorios, tanto en la base de datos relacional como en los prompts enviados al LLM.
2. WHEN el Sistema jAImes construye un prompt para el LLM, THE Sistema jAImes SHALL incluir exclusivamente texto despersonalizado (sin nombres reales, RUT, direcciones ni datos de contacto) junto con la rúbrica aplicable.
3. IF un prompt destinado al LLM contiene algún dato directamente identificatorio (nombre real, RUT, dirección o dato de contacto), THEN THE Sistema jAImes SHALL bloquear el envío del prompt al LLM, registrar el evento y devolver un error indicando que el contenido contiene datos no permitidos, sin transmitir el dato al LLM.
4. WHERE el camino es AWS, WHEN el Sistema jAImes almacena un archivo de medios, THE Sistema jAImes SHALL guardarlo cifrado en reposo en S3 y SHALL servirlo únicamente mediante URLs prefirmadas con una vigencia máxima de 300 segundos.
5. THE Sistema jAImes SHALL mantener los datos personales (almacén relacional) y el contenido (almacén vectorial) en almacenes separados, de modo que cada almacén sea accedido exclusivamente por su repositorio respectivo.
6. WHERE el camino es AWS, THE Sistema jAImes SHALL almacenar las credenciales de base de datos y las claves en AWS Secrets Manager, sin incrustarlas en código fuente, variables de entorno en texto plano ni archivos de configuración versionados, y SHALL asignar a cada rol IAM de Lambda únicamente los permisos requeridos por su función (privilegios mínimos).

### Requirement 12: Documentación de arquitectura organizada por área

**User Story:** Como miembro del equipo, quiero que la documentación de arquitectura esté organizada por área bajo `docs/`, para encontrar rápidamente las notas y diagramas de mi módulo.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL mantener la documentación de arquitectura bajo el directorio `docs/`, organizada en subcarpetas por área: `backend/`, `frontend/`, `database/` y `cloud/`.
2. THE subcarpeta `docs/backend/` SHALL contener al menos un documento Markdown que describa la lógica de negocio: servicios, dominio, puertos/adaptadores, DI, aplicación de SOLID y los contratos interface-first.
3. THE subcarpeta `docs/frontend/` SHALL contener al menos un documento Markdown que describa la estructura de la PWA, las pantallas por rol y el consumo de la API REST, marcado como pendiente del refinamiento de Figma.
4. THE subcarpeta `docs/database/` SHALL contener al menos un documento Markdown que describa el modelo relacional del dataset E-1, las tablas nuevas y el índice vectorial pgvector.
5. THE subcarpeta `docs/cloud/` SHALL contener al menos un documento Markdown que describa la arquitectura serverless AWS, los stacks CDK, IAM de mínimos privilegios, los pasos de despliegue y las pruebas de integración cloud.
6. THE cada subcarpeta de `docs/` SHALL incluir al menos un diagrama expresado como bloque de código Mermaid (```mermaid```) de su área.
7. WHEN la documentación está completa THEN las cuatro subcarpetas (`backend/`, `frontend/`, `database/`, `cloud/`) SHALL existir, cada una con al menos un documento Markdown y al menos un diagrama Mermaid.
8. IF alguna subcarpeta esperada de `docs/` no existe o no contiene su documento Markdown y su diagrama Mermaid THEN THE documentación SHALL considerarse incompleta para esa área.

### Requirement 13: Arquitectura modular interface-first para trabajo paralelo

**User Story:** Como equipo de 4 personas, quiero que el backend esté organizado en módulos independientes definidos por interfaces, para desarrollar y probar cada módulo en paralelo sin bloquearnos entre nosotros.

#### Acceptance Criteria
1. THE Backend SHALL organizarse en 8 módulos independientes, cada uno en su propio paquete, correspondientes a dominio compartido (A), relacional + seed (B), vectorial + embeddings (C), ingesta + transcripción (D), clasificación (E), bitácoras + rúbrica + recomendación (F), reporte + API + DI (G) e infraestructura AWS CDK (H), de modo que ningún módulo importe en tiempo de ejecución la implementación concreta de otro módulo.
2. WHEN un módulo necesita una capacidad provista por otro módulo, THE Backend SHALL resolver esa dependencia únicamente a través de una interfaz abstracta declarada en `providers/*/base.py` o `repositories/*/base.py`, de forma que un análisis estático de importaciones detecte cero importaciones de módulos de implementación hermanos (solo se permiten importaciones de los `base.py` de interfaz y del módulo de dominio A).
3. THE módulo de dominio (A) SHALL publicarse como única fuente de verdad compartida de modelos y enums antes de que cualquier módulo dependiente (B–H) comience su implementación, y una vez publicado sus definiciones existentes SHALL permanecer sin cambios incompatibles mientras los módulos dependientes estén en desarrollo.
4. THE cada módulo (B–H) SHALL incluir su propio fake o mock de las interfaces que consume, de modo que su suite de pruebas unitarias SHALL ejecutarse y pasar en aislamiento con cero importaciones de la implementación concreta de otro módulo.
5. WHEN se ensambla el sistema end-to-end, THE integración SHALL cablear las implementaciones concretas de cada interfaz mediante el contenedor de inyección de dependencias, sin modificar el código de los módulos ni introducir importaciones directas entre implementaciones.
6. IF durante el ensamblaje end-to-end se detecta que un módulo importa directamente la implementación concreta de otro módulo (en lugar de su interfaz), THEN THE Backend SHALL fallar el ensamblaje e indicar el módulo y la importación prohibida que violan el límite de interfaz.

### Requirement 14: Dataset oficial E-1 como fuente de verdad para pruebas y entrenamiento

**User Story:** Como equipo, quiero usar el Dataset E-1 oficial, reproducible y completo (500 niños/as, 7 CSV + `consolidado.json`), para las pruebas, la validación y el entrenamiento/evaluación de los modelos de IA, de modo que los resultados sean realistas y reproducibles.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL cargar el Dataset E-1 oficial a partir de los siete CSV relacionales y de `consolidado.json` como única fuente de verdad, poblando tanto la base relacional como la base vectorial mediante las interfaces `RelationalRepo` y `VectorRepo`.
2. WHEN se carga el Dataset E-1 oficial THEN el Sistema jAImes SHALL procesar sin error a los 500 niños/as, incluyendo los 60 niños/as con solo 1–2 observaciones (ingreso reciente) y los 440 con entre 4 y 9 observaciones.
3. IF un niño/a cargado del Dataset E-1 oficial tiene menos de 5 observaciones registradas THEN el `RecommendationService` SHALL abstenerse de emitir una decisión conforme al criterio de datos insuficientes del Requirement 6, sin producir error ni interrumpir el procesamiento del resto del dataset.
4. WHEN una observación del Dataset E-1 oficial carece de nota opcional, de formato o de manifestación vinculada THEN el Sistema jAImes SHALL interpretarlo como ausencia de registro y SHALL continuar la carga sin tratarlo como dato inválido.
5. WHEN se ejecuta la verificación de reproducibilidad del Dataset E-1 oficial THEN el Sistema jAImes SHALL volver a ejecutar `generador.py` con la semilla fija `20261013` y la fecha de referencia `2026-10-13` y SHALL confirmar que la salida es idéntica bit a bit a la publicada (hashes coincidentes) y que `validador.py` finaliza sin errores.
6. THE Sistema jAImes SHALL usar el Dataset E-1 oficial para ejercitar y evaluar los cuatro modelos de IA (transcripción, clasificación, bitácora y recomendación de nivel) tanto en modo mock como en modo AWS, a través de las mismas interfaces de proveedores.
7. THE Sistema jAImes SHALL distribuir y versionar únicamente `dataset_e1_publico.zip` y SHALL NOT incluir el zip interno de validación en el repositorio ni en los artefactos entregables.

### Requirement 15: Innovación técnica y arquitectura extensible

**User Story:** Como evaluador del desafío, quiero que la solución demuestre innovación técnica mediante una arquitectura extensible basada en SOLID y puertos y adaptadores, para valorar su calidad de ingeniería.

#### Acceptance Criteria
1. THE Backend SHALL aplicar programación orientada a objetos, encapsulamiento y el patrón de puertos y adaptadores, exponiendo cada capacidad de IA y de datos detrás de una interfaz abstracta.
2. WHEN se agrega un nuevo proveedor de IA, un nuevo modelo o una nueva fuente de datos THEN el Sistema jAImes SHALL incorporarlo implementando la interfaz correspondiente sin modificar el código de las clases de servicio existentes (principio Abierto/Cerrado).
3. THE Backend SHALL definir interfaces pequeñas y segregadas por capacidad (`TranscriptionProvider`, `EmbeddingProvider`, `LlmProvider`, `Classifier`, `RelationalRepo`, `VectorRepo`, `StorageRepo`), de modo que ningún consumidor dependa de métodos que no usa (principio de Segregación de Interfaces).
4. THE clases de servicio SHALL depender únicamente de abstracciones (interfaces), inyectadas por el contenedor de inyección de dependencias, sin referenciar implementaciones concretas (principio de Inversión de Dependencias).
5. WHEN se realiza un análisis estático de importaciones sobre las clases de servicio THEN el Sistema jAImes SHALL evidenciar que los servicios importan solo interfaces (abstracciones) y no implementaciones concretas de proveedores o repositorios.

### Requirement 16: Impacto social y seguridad pedagógica

**User Story:** Como evaluador del desafío, quiero que la solución demuestre impacto social medible y seguridad pedagógica, para valorar su contribución al desarrollo infantil sin reemplazar el juicio profesional.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL orientarse al indicador clave de reducción del tiempo de documentación desde aproximadamente 4 horas por semana hacia aproximadamente 0 horas, convirtiendo la tarea de la educadora de redactar a revisar y aprobar.
2. THE Sistema jAImes SHALL mantener a la educadora como responsable de la decisión final (human-in-the-loop), de modo que ninguna clasificación, bitácora ni recomendación de nivel se aplique de forma automática sin validación humana.
3. WHEN se genera el reporte de dirección THEN el Sistema jAImes SHALL calcular de forma determinista y mostrar el KPI de tiempo de documentación ahorrado a nivel jardín.
4. WHILE cualquier pantalla de la aplicación esté visible THE Frontend SHALL mostrar un banner persistente que indique que los datos son sintéticos, de uso pedagógico y que el sistema no constituye un diagnóstico.
5. WHEN el `RecommendationService` emite una recomendación de nivel THEN el Sistema jAImes SHALL registrar la decisión humana (aceptó, rechazó o ajustó) antes de considerarla final, sin aplicar la recomendación automáticamente.

### Requirement 17: Factibilidad y sustentabilidad

**User Story:** Como evaluador del desafío, quiero que la solución sea factible y sustentable con bajo costo operativo, para valorar su viabilidad más allá de la demo.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL desplegarse como una arquitectura serverless con escalado a cero en reposo, desplegable mediante un único flujo de Infraestructura como Código (AWS CDK en Python).
2. WHERE la configuración es `USE_MOCKS=true` THEN el Sistema jAImes SHALL ejecutarse localmente sin credenciales de nube y sin incurrir en costo de servicios AWS.
3. THE Sistema jAImes SHALL fijar (pin) las versiones de sus dependencias de software, de modo que una instalación posterior reproduzca el mismo conjunto de versiones.
4. THE Sistema jAImes SHALL apoyarse en el Dataset E-1 oficial reproducible de forma determinista como base de datos de referencia para pruebas y evaluación.
5. WHEN se ejecuta el flujo de despliegue documentado THEN el Sistema jAImes SHALL quedar operativo en AWS, y SHALL poder ejecutarse en modo mock local sin requerir credenciales.

### Requirement 18: Escalabilidad

**User Story:** Como evaluador del desafío, quiero que la solución escale desde la demo hasta muchos jardines sin cambios de arquitectura, para valorar su potencial de crecimiento.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL escalar desde el dataset de demostración hasta un volumen de muchos jardines, salas y niños/as sin requerir cambios en su arquitectura.
2. THE capa de cómputo SHALL ejecutarse como funciones Lambda sin estado, de modo que el procesamiento concurrente escale horizontalmente mediante instancias adicionales administradas por la plataforma.
3. THE capa de datos SHALL apoyarse en Aurora Serverless v2 con autoescalado y en un índice vectorial pgvector, de modo que el crecimiento del volumen de datos no requiera cambios de código.
4. WHEN se apunta el sistema a un dataset de mayor tamaño THEN el Sistema jAImes SHALL operar sin cambios en el código de los servicios ni en los contratos de las interfaces.
5. WHERE se requiera un almacén vectorial de mayor escala THEN el Sistema jAImes SHALL permitir sustituir la implementación de `VectorRepo` (por ejemplo, de pgvector a OpenSearch Serverless) sin modificar los servicios que la consumen.

### Requirement 19: Calidad de la presentación y demo

**User Story:** Como evaluador del desafío, quiero que la solución sea fácil de presentar y demostrar en vivo, con documentación clara, para valorar la calidad de la presentación.

#### Acceptance Criteria
1. THE Sistema jAImes SHALL proveer una demo local en modo mock iniciable mediante un único comando documentado, sin requerir credenciales de nube.
2. THE Sistema jAImes SHALL proveer un camino de demo en vivo sobre AWS que levante el servidor y responda al endpoint `/health`.
3. THE README SHALL incluir un guion de demostración (demo script) que describa los pasos para presentar la solución en vivo.
4. THE Sistema jAImes SHALL mantener la documentación bajo `docs/` organizada por área (`backend/`, `frontend/`, `database/`, `cloud/`), cada una con al menos un documento Markdown y al menos un diagrama expresado como bloque de código Mermaid.
5. THE Frontend SHALL presentar su contenido textual en español (Chile) con una experiencia de uso clara y consistente.

### Requirement 20: Ingesta de mockups de Figma

**User Story:** Como equipo, cuando entreguemos los mockups refinados de Figma (en formato PDF), quiero que el sistema los convierta en tareas concretas de implementación de frontend, para que la UI coincida con el diseño sin tocar la lógica del backend.

#### Acceptance Criteria
1. WHEN se proporciona un PDF con los mockups de Figma THEN el diseño y las tareas SHALL actualizarse para extraer las pantallas y los flujos representados en los mockups.
2. WHEN se procesan los mockups de Figma THEN el Sistema jAImes SHALL realizar un análisis de brechas (gap-analysis) de las pantallas y flujos contra la API REST existente, identificando los endpoints que cada pantalla consume y las brechas detectadas.
3. WHEN se completa el análisis de los mockups THEN las tareas SHALL producir componentes concretos mapeados a las pantallas existentes (`MiSala`, `Capturar`, `ConfirmarClasificacion`, `FichaNino`, `Bitacoras`, `DashboardDireccion`).
4. WHEN se implementa el frontend a partir de los mockups THEN el Frontend SHALL aplicar los estilos y tokens de diseño sobre la estructura existente sin alterar la lógica de negocio.
5. THE contrato de la API REST del Backend SHALL permanecer sin cambios como resultado de la ingesta de los mockups de Figma.

### Requirement 21: Rúbrica oficial como fuente de verdad de criterios de nivel

**User Story:** Como equipo, quiero que la rúbrica oficial (tramo de sala × núcleo × 8 niveles de progresión, con conductas observables por nivel) se almacene como fuente de verdad versionada, para que la recomendación de nivel y su argumento se fundamenten en los criterios oficiales y en la evidencia previa del niño/a.

#### Acceptance Criteria
1. THE rúbrica oficial SHALL modelarse como una estructura versionada en `rubrica_versiones.criterios` que contenga el tramo de sala, el núcleo, los 8 niveles de progresión en orden fijo (1 Comenzando, 2 Explorando, 3 Desarrollando, 4 Afianzando, 5 Integrando, 6 Ampliando, 7 Consolidando, 8 Profundizando) y, por cada nivel, el descriptor de desarrollo y aprendizaje esperado y la lista de conductas observables.
2. THE modelo de la rúbrica oficial SHALL soportar múltiples núcleos (iniciando con "Identidad y Autonomía") y los tres tramos de sala (Sala Cuna, Nivel Medio, Transición) sin cambios de código, agregando núcleos y tramos como datos versionados en `rubrica_versiones.criterios`.
3. WHEN se evalúa a un niño/a THEN `RubricaDecision` SHALL determinar su tramo de sala a partir de su rango etario y SHALL usar las conductas observables del núcleo y del nivel de progresión correspondientes como criterios de la decisión.
4. WHEN se genera la recomendación o la bitácora THEN el `LlmProvider` SHALL recibir como contexto las conductas observables aplicables y las observaciones previas del niño/a (evidencia) y SHALL argumentar citándolas, sin alterar la decisión determinista calculada por `RubricaDecision`.
5. THE script de seed SHALL cargar al menos el núcleo "Identidad y Autonomía" para los tres tramos de sala (Sala Cuna, Nivel Medio, Transición) como versión inicial de la rúbrica oficial en `rubrica_versiones.criterios`, y los núcleos adicionales SHALL agregarse como nuevas versiones sin cambios de código.
6. WHERE una conducta observable del nivel evaluado no tenga evidencia asociada en las observaciones del niño/a THEN `RubricaDecision` SHALL contarla como pendiente, sin inferir su cumplimiento.

### Requirement 22: Rezago relativo a la composición de la sala

**User Story:** Como educadora, quiero que el sistema me avise cuando un niño/a queda rezagado respecto del nivel de la mayoría de su propia sala, para detectar a tiempo a quienes necesitan apoyo adicional dentro de su grupo-curso.

Este requisito amplía el Requirement 7.3 agregando un criterio de "rezago relativo a la sala", complementario al rezago individual por racha ya definido en el Requirement 6.4.

#### Acceptance Criteria
1. WHEN se evalúa el estado de una sala (identificada por `id_jardin` y `sala_grupo`) para un núcleo dado THEN el Sistema jAImes SHALL calcular, mediante `RelationalRepo`, el nivel predominante de la sala como el nivel de progresión en que se encuentra la mayoría de los niños/as de esa sala en ese núcleo.
2. WHEN se dispone del nivel predominante de la sala THEN el Sistema jAImes SHALL marcar como rezagado relativo a cada niño/a cuyo nivel de progresión en ese núcleo esté al menos un umbral configurable de niveles por debajo del nivel predominante de la sala, siendo dicho umbral por defecto de 2 niveles.
3. WHEN uno o más niños/as de una sala quedan marcados como rezagados relativos THEN el Sistema jAImes SHALL levantar una alerta automática dirigida a la educadora de esa sala que identifique a los niños/as rezagados por su `id_nino`, el núcleo afectado, su nivel y el nivel predominante de la sala.
4. THE criterio de rezago relativo a la sala SHALL ser independiente y adicional al rezago individual por racha del Requirement 6.4, de modo que un niño/a pueda señalarse por cualquiera de los dos criterios o por ambos.
5. IF una sala no tiene suficientes niños/as con nivel asignado en el núcleo para determinar un nivel predominante THEN el Sistema jAImes SHALL abstenerse de calcular el rezago relativo para esa sala y núcleo, sin producir error.

### Requirement 23: Vista de grupo-curso (nivel predominante de la sala por núcleo)

**User Story:** Como educadora, quiero ver en qué nivel está la mayoría de los niños/as de mi sala en cada núcleo, para tener una visión de grupo-curso además de la ficha individual.

Este requisito amplía el Requirement 7.3 agregando una vista agregada de grupo-curso para la educadora.

#### Acceptance Criteria
1. WHEN la educadora solicita la vista de grupo-curso de una sala (identificada por `id_jardin` y `sala_grupo`) THEN el Sistema jAImes SHALL exponer, mediante la API REST, el nivel predominante de la sala por núcleo, calculado por agregación en `RelationalRepo`.
2. WHEN se calcula el nivel predominante de un núcleo en una sala THEN el Sistema jAImes SHALL determinarlo como el nivel de progresión en que se encuentra la mayor cantidad de niños/as de la sala en ese núcleo, incluyendo además la distribución de niños/as por nivel de ese núcleo.
3. WHEN una sala no tiene niños/as con nivel asignado en un núcleo THEN el Sistema jAImes SHALL devolver la vista con ese núcleo marcado como sin datos, sin producir error.
4. THE vista de grupo-curso SHALL calcularse exclusivamente mediante `RelationalRepo` y SHALL NOT ser inferida por el `LlmProvider`.

### Requirement 24: Vista de jardín (comparación entre salas equivalentes)

**User Story:** Como directora de jardín, quiero comparar salas del mismo tramo entre sí, para detectar un grupo-curso que esté más rezagado que sus equivalentes y actuar sobre él.

Este requisito amplía el Requirement 7 agregando al `DirectorReportService` la comparación entre salas del mismo tramo de sala.

#### Acceptance Criteria
1. WHEN se genera el reporte de dirección de un `id_jardin` para un período THEN el `DirectorReportService` SHALL agrupar las salas del jardín por tramo de sala (Sala Cuna, Nivel Medio, Transición) y SHALL comparar entre sí las salas que pertenecen al mismo tramo.
2. WHEN existen dos o más salas del mismo tramo THEN el `DirectorReportService` SHALL calcular, para cada sala, una métrica de avance agregada comparable (por ejemplo, el nivel de progresión promedio o predominante del grupo-curso) mediante `RelationalRepo`.
3. WHEN una sala presenta una métrica de avance al menos un umbral configurable por debajo de la mediana de las salas de su mismo tramo THEN el `DirectorReportService` SHALL levantar una alerta dirigida a la directora que identifique la sala rezagada, su tramo y la diferencia respecto de sus equivalentes.
4. IF un tramo tiene una sola sala en el jardín THEN el `DirectorReportService` SHALL omitir la comparación entre salas equivalentes para ese tramo, sin producir error ni alerta.
5. THE comparación entre salas equivalentes SHALL calcularse mediante `RelationalRepo` y SHALL NOT ser inferida por el `LlmProvider`.

### Requirement 25: Nivel general del niño/a derivado del promedio por núcleo

**User Story:** Como educadora, quiero ver un nivel general del niño/a además de su nivel por núcleo, para tener una lectura rápida de su desarrollo global sin perder el detalle por núcleo.

Este requisito amplía el Requirement 21: el nivel de progresión sigue siendo por núcleo; el nivel general es un valor derivado.

#### Acceptance Criteria
1. THE nivel de progresión de un niño/a SHALL seguir determinándose por núcleo conforme al Requirement 21, y el nivel general SHALL ser un valor derivado, sin reemplazar a los niveles por núcleo.
2. WHEN un niño/a tiene nivel de progresión asignado en uno o más núcleos THEN `RubricaDecision` SHALL derivar su nivel general como el promedio de los niveles de progresión de los distintos núcleos con nivel asignado.
3. WHEN se expone la ficha del niño/a THEN el Sistema jAImes SHALL incluir tanto el nivel de progresión por núcleo como el nivel general derivado.
4. IF un niño/a no tiene nivel de progresión asignado en ningún núcleo THEN el Sistema jAImes SHALL indicar que el nivel general no está disponible, sin producir error.

### Requirement 26: Evolución individual en el tiempo (serie temporal por núcleo)

**User Story:** Como educadora, quiero ver cómo ha evolucionado en el tiempo el nivel de un niño/a en cada núcleo, para graficar su trayectoria en la ficha del niño/a.

Este requisito amplía el Requirement 6 y la ficha del niño/a agregando la trayectoria temporal del nivel por núcleo.

#### Acceptance Criteria
1. WHEN se solicita la trayectoria temporal de un niño/a (identificado por `id_nino`) THEN el Sistema jAImes SHALL exponer, mediante la API REST, la serie temporal del nivel de progresión por núcleo a partir del histórico de recomendaciones y observaciones del niño/a mediante `RelationalRepo`.
2. WHEN se construye la serie temporal de un núcleo THEN el Sistema jAImes SHALL devolver, en orden cronológico ascendente, los puntos con su fecha y el nivel de progresión del niño/a en ese núcleo en esa fecha.
3. WHEN un niño/a no tiene histórico suficiente para un núcleo THEN el Sistema jAImes SHALL devolver la serie temporal vacía para ese núcleo, sin producir error.
4. THE serie temporal SHALL calcularse mediante `RelationalRepo` y SHALL NOT ser inferida por el `LlmProvider`.

### Requirement 27: Consentimiento y retención de grabaciones (extraer y borrar)

**User Story:** Como institución, necesito que las grabaciones de audio y video de los niños/as solo se procesen con consentimiento del apoderado y que no se retengan en el tiempo, para proteger la privacidad conservando únicamente el texto despersonalizado.

Este requisito es nuevo y revisa el Requirement 1.2 y el Requirement 11.4. Resuelve el conflicto con el Requirement 1.2 (que exige almacenar el archivo original) acotando el borrado tras la extracción exclusivamente a los medios de audio y video de niños/as.

#### Acceptance Criteria
1. IF una carga de audio o video no incluye una marca de consentimiento de apoderado válida THEN THE Sistema jAImes SHALL rechazar el procesamiento de ese medio con un mensaje de error en español, SHALL NOT transcribirlo y SHALL NOT retener el archivo original.
2. WHEN se procesa un audio o video de un niño/a con consentimiento de apoderado válido THEN el Sistema jAImes SHALL extraer el texto y los metadatos conforme al Requirement 2 y, una vez completada la extracción, SHALL eliminar la grabación original del almacenamiento, conservando únicamente el texto despersonalizado y los metadatos asociados a la observación.
3. THE borrado del medio original tras la extracción SHALL aplicarse exclusivamente a los medios de audio y video de niños/as; los demás medios (por ejemplo, fotos de notas manuscritas) SHALL seguir el almacenamiento definido en el Requirement 1.2 y el Requirement 11.4.
4. WHEN se registra el consentimiento de apoderado de un medio THEN el Sistema jAImes SHALL persistir dicha marca de consentimiento asociada a la observación mediante `RelationalRepo`, sin almacenar datos directamente identificatorios del apoderado conforme al Requirement 11.
5. IF la extracción de texto de un audio o video falla tras agotar los reintentos del Requirement 2.7 THEN THE Sistema jAImes SHALL conservar temporalmente la grabación original marcada como pendiente de transcripción y SHALL eliminarla una vez que la extracción se complete o la observación se descarte, sin retenerla indefinidamente.

### Requirement 28: Resolución del post-it manuscrito al id_nino por nombre

**User Story:** Como educadora, quiero que al fotografiar un post-it manuscrito con el nombre de un niño/a, el sistema lo asocie automáticamente al niño/a correcto de mi sala, sin que su nombre quede guardado ni se envíe al LLM.

Este requisito amplía el Requirement 2.2 y el Requirement 11 agregando la resolución de nombre escrito a `id_nino` con resguardo de datos.

#### Acceptance Criteria
1. WHEN el OCR de un post-it individual (conforme al Requirement 2.2) extrae un nombre escrito THEN el Sistema jAImes SHALL resolver ese nombre a un `id_nino` existente dentro de la sala del contexto activo (`id_jardin` y `sala_grupo`).
2. IF dentro de la sala existen varios niños/as con el mismo nombre THEN THE Sistema jAImes SHALL desambiguar usando el apellido escrito y, si aún persiste la ambigüedad, SHALL solicitar a la educadora que seleccione el `id_nino` correcto, sin asociar la observación de forma automática.
3. IF el nombre escrito no corresponde a ningún niño/a de la sala THEN THE Sistema jAImes SHALL marcar la observación como pendiente de vinculación manual con un mensaje en español, sin descartar el texto extraído.
4. THE nombre escrito usado para la resolución SHALL emplearse únicamente para resolver el `id_nino` y SHALL NOT persistirse en la base de datos ni incluirse en ningún prompt enviado al `LlmProvider`, conforme al Requirement 11.1 y el Requirement 11.2.
5. WHEN se resuelve el `id_nino` a partir del post-it THEN el Sistema jAImes SHALL asociar la observación resultante a ese `id_nino` seudónimo, descartando el nombre escrito tras la resolución.

### Requirement 29: Pasos a seguir por nivel y núcleo (alcance futuro)

**User Story:** Como equipo, quiero que el esquema de la rúbrica esté preparado para incorporar los "pasos a seguir" (conductas a observar en próximas actividades) cuando Fundación Integra entregue la rúbrica completa, para no requerir cambios de código al incorporarlos.

Este requisito amplía el Requirement 21.1 agregando un campo opcional de "pasos a seguir". Está marcado como alcance futuro conforme a la FAQ de Fundación Integra.

#### Acceptance Criteria
1. THE estructura versionada `rubrica_versiones.criterios` SHALL admitir, por cada nivel de progresión de un tramo × núcleo, un campo opcional de "pasos a seguir" (conductas a observar en próximas actividades), sin requerir cambios de código para incorporarlo.
2. WHERE una versión de la rúbrica no incluya los "pasos a seguir" de un nivel THEN el Sistema jAImes SHALL operar normalmente, tratando dicho campo como ausente, sin producir error.
3. WHEN una versión de la rúbrica incluya "pasos a seguir" para un nivel THEN el Sistema jAImes SHALL poder exponerlos como parte de los criterios de ese nivel, sin alterar la decisión determinista de `RubricaDecision` definida en el Requirement 6.2.