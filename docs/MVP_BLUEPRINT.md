# jAImes — MVP Blueprint

**Desafío:** AWS Breaking Barriers Chile 2026 · Fundación Integra · Desafío 1 — "IA para el Desarrollo Infantil: de la Observación a la Acción"

**Objetivo (KPI estrella):** reducir el tiempo de documentación de las educadoras de ~4 h/semana a ~0 h, devolviéndoles tiempo en sala. La herramienta toma los recursos crudos que las tías ya generan (texto, fotos de notas manuscritas, audios, videos) y los convierte automáticamente en observaciones estructuradas, trayectorias de desarrollo y **bitácoras quincenales** por niño/a, resguardando datos sensibles.

> Datos sintéticos (dataset E-1). No es instrumento clínico ni diagnóstico; es apoyo pedagógico.

---

## 1. Visión del producto

Una educadora abre la app en su celular, aprieta grabar y habla ("Hoy Sofía clasificó las hojas por 3 colores…"), o le saca una foto a su post-it, o sube un video corto. En segundos:

1. El medio se **transcribe a texto** (Transcribe / Textract).
2. La IA **clasifica** la evidencia contra la ruta de 9 niveles × 5 dominios y la vincula a manifestaciones observables.
3. La observación queda registrada contra el niño/a, sin que la tía escriba nada.
4. Cada quincena, la IA **redacta una bitácora** por niño/a basada en la evidencia acumulada (RAG), lista para revisar y aprobar.

La tía pasa de *redactar* a *revisar y aprobar*. Ahí está el salto de 4 h → ~0 h.

---

## 2. Alcance del MVP

### Dentro del MVP (demo)
- Captura multi-formato: **texto, audio, foto (nota manuscrita), video**.
- **Transcripción** de audio/video a texto y **OCR** de fotos.
- **Clasificación automática** de la evidencia: dominio (5) + nivel (1–9) + manifestaciones vinculadas.
- Persistencia en **BD relacional** (personas/entidades) y **BD vectorial** (contenido/embeddings).
- **Generación de bitácora quincenal** por niño/a vía **RAG + LLM** (Bedrock/Claude).
- **Recomendación de nivel en tiempo real** (AVANZAR / MANTENER / RETROCEDER) por botón y automática al subir evidencia (reglas deterministas + LLM explicativo).
- **Reporte de dirección**: dashboard agregado por jardín/sala para la directora (quién subió/bajó, distribución de niveles, conteos, alertas, KPI de tiempo ahorrado).
- **Interfaz de bitácoras**: listar, ver detalle, editar/aprobar.
- **Flujo de automatización** de punta a punta (ingesta → transcripción → clasificación → indexado → bitácora).
- Frontend **mobile-first (PWA)**.
- Resguardo de datos sensibles (seudonimización por `id_nino`, sin nombres reales ni RUT).

### Fuera del MVP (futuro)
- Autenticación robusta / SSO institucional (en demo: login simulado).
- Multi-tenant a escala 1.200 jardines.
- Fine-tuning de modelos propios.
- App nativa iOS/Android.
- Panel analítico institucional avanzado.

---

## 3. Arquitectura (3 capas + cloud)

```
┌──────────────────────────────────────────────────────────────┐
│  CAPA 1 — PRESENTACIÓN (Frontend PWA mobile-first)             │
│  React + Vite. Captura (texto/audio/foto/video), ver/aprobar   │
│  bitácoras, trayectoria del niño/a.                            │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS / REST (JSON)
┌───────────────────────────┴──────────────────────────────────┐
│  CAPA 2 — LÓGICA DE NEGOCIO (Backend FastAPI, Python)          │
│  ┌──────────────┬──────────────┬──────────────┬─────────────┐ │
│  │ API Layer    │ Service Layer │ Domain Models │ Repositories│ │
│  │ (routers)    │ (casos de uso)│ (POO/SOLID)   │ (acceso datos)│
│  └──────────────┴──────────────┴──────────────┴─────────────┘ │
│  Servicios: Transcripción · Clasificación · Embeddings · RAG   │
│  · Generación de bitácoras · Orquestación del flujo            │
└──────┬───────────────┬───────────────┬───────────────┬────────┘
       │               │               │               │
┌──────┴─────┐  ┌──────┴──────┐ ┌──────┴──────┐ ┌───────┴───────┐
│ PostgreSQL │  │  Vector DB  │ │  AWS AI svc │ │ Object Storage│
│ (RDS/Aurora)│ │ (OpenSearch │ │ Transcribe  │ │ S3 (medios)   │
│ relacional │  │  / pgvector)│ │ Textract    │ │               │
│            │  │  embeddings │ │ Rekognition │ │               │
│            │  │             │ │ Bedrock LLM │ │               │
└────────────┘  └─────────────┘ └─────────────┘ └───────────────┘
```

**Capas:**
- **Presentación**: solo UI y llamadas a la API. Sin lógica de negocio.
- **Negocio**: casos de uso orquestados por servicios; modelos de dominio con POO; principios SOLID (interfaces/puertos para desacoplar proveedores de IA y de datos → se puede mockear AWS en local para la demo).
- **Datos**: repositorios que abstraen Postgres, la vector DB, S3 y los servicios de IA detrás de interfaces.

---

## 4. Modelos de IA (los dos)

### Modelo 1 — Transcripción / extracción de texto (media → texto)
| Entrada | Servicio AWS | Salida |
|---|---|---|
| Audio (.mp3/.wav/.m4a) | **Amazon Transcribe** (es-CL) | texto |
| Video (.mp4) | **Transcribe** (audio) + **Rekognition** (etiquetas de escena) | texto + metadatos |
| Foto de nota manuscrita | **Amazon Textract** (OCR) | texto |
| Texto directo | — (passthrough) | texto |

Interfaz `TranscriptionProvider` → implementaciones `AwsTranscriptionProvider` y `MockTranscriptionProvider` (para demo offline).

### Modelo 2 — Generación de bitácoras (RAG + LLM)
No se *entrena*: se usa **RAG**.
1. Cada observación transcrita se **embebe** (Amazon Titan Embeddings / Bedrock) y se guarda en la **vector DB**.
2. Al generar la bitácora quincenal de un niño/a: se **recuperan** sus observaciones del período por similitud semántica + filtros (fecha, dominio).
3. El contexto recuperado + la rúbrica (9 niveles, 5 dominios, manifestaciones) se pasan a **Bedrock (Claude)** con un prompt estructurado.
4. El LLM redacta la bitácora **anclada en evidencia real** (cita manifestaciones observadas), evitando alucinaciones.

Interfaz `LlmProvider` → `BedrockLlmProvider` y `MockLlmProvider`.

**Por qué RAG y no fine-tuning:** inviable entrenar en una hackathon, requiere datos etiquetados masivos y GPU; RAG da resultados fundamentados, trazables y auditables desde el día 1.

### Modelo 3 — Recomendación de nivel (rúbrica estricta + LLM explicativo)
Responde, por niño/a y bajo demanda, una de tres decisiones: **AVANZAR**, **MANTENER** o **RETROCEDER**, con justificación trazable.

**Principio rector (tres roles separados):**
- **La rúbrica decide** (reglas y métricas estrictas, deterministas).
- **La IA argumenta** (traduce el resultado de la rúbrica a lenguaje claro para la educadora, para que **no tenga que leer punto por punto** la trayectoria).
- **La educadora valida** (tiene siempre la última palabra; la recomendación es apoyo, nunca decisión automática).

**Enfoque híbrido (clave para que sea auditable):**
1. **Rúbrica de decisión (determinista y versionada)** calcula la señal objetiva desde la evidencia dura del dataset. Los criterios viven como una **rúbrica explícita y configurable** (ajustable con Integra sin tocar código), que evalúa:
   - cobertura de dominios en el nivel actual (¿hay manifestaciones vinculadas en los 5 dominios?),
   - consistencia del `nivel_estimado` en las últimas N observaciones,
   - tendencia (ascendente / estable / descendente),
   - señales de retroceso (observaciones sostenidas bajo el nivel asignado — el dataset incluye el caso de "baja acotada").
2. **Decisión** la toma la rúbrica (no el LLM) → `{ decision, score, dominios_cubiertos, dominios_pendientes, evidencia[], version_rubrica }`.
3. **LLM (Bedrock)** solo **redacta la explicación** en lenguaje natural y accionable para la educadora ("qué reforzar en sala"), citando la evidencia. No altera la decisión.
4. **Trazabilidad y decisión humana**: cada recomendación guarda con qué `version_rubrica` se calculó, y registra qué resolvió finalmente la educadora (aceptó / rechazó / ajustó), para auditoría y mejora continua.

**Lógica resumida:**
| Decisión | Condición | Ejemplo de salida |
|---|---|---|
| AVANZAR | evidencia en los 5 dominios del nivel actual + tendencia ascendente | "Cumple los 5 dominios del nivel 4; se recomienda avanzar al nivel 5." |
| MANTENER | avance parcial / faltan dominios / evidencia escasa | "Cognitivo y lenguaje consolidados; falta evidencia en motor grueso." |
| RETROCEDER | registros sostenidos bajo el nivel asignado | "3 registros bajo el nivel asignado; reforzar antes de avanzar." |

**Disparadores:**
- **Botón "¿Puede subir de nivel?"** en la ficha del niño/a → respuesta en segundos.
- **Automático al registrar nueva observación/bitácora**: si la nueva evidencia cruza el umbral, muestra una **sugerencia proactiva** ("Con esta observación ya cumple los 5 dominios del nivel 4 → ¿avanzar?").

Servicio dedicado `RecommendationService` (SOLID: separado de bitácoras). Corre en modo mock sin AWS (las reglas son 100% locales; solo la redacción usa el LLM, mockeable).

### Modelo 4 — Reporte de dirección (agregados + resumen ejecutivo)
Reporte periódico (quincenal/mensual) y bajo demanda para la **directora/jefa del jardín**, a nivel agregado (jardín / sala), distinto de la bitácora individual.

**Contenido:**
- Niños/as que **subieron / mantuvieron / bajaron** de nivel en el período.
- **Distribución de niveles** por sala y por dominio.
- **N° de observaciones y bitácoras** registradas (total y por educadora).
- **Alertas**: niños/as con señal de retroceso o sin observaciones recientes.
- **KPI de tiempo de documentación ahorrado** (4 h → ~0 h) a nivel jardín.

La parte numérica se calcula con consultas sobre la **BD relacional**; el **resumen ejecutivo narrativo** lo redacta el LLM a partir de esos agregados. Servicio dedicado `DirectorReportService`. Requiere un **rol** simple (`educadora` / `directora`) que en la demo se cambia con un selector, sin auth real.

---

## 5. Bases de datos (las 2)

### BD 1 — Relacional (PostgreSQL) · personas y entidades
Mapea 1:1 el dataset E-1. Tablas:

| Tabla | PK | Campos clave | FKs |
|---|---|---|---|
| `jardines` | `id_jardin` | nombre_fantasia, comuna, region, numero_salas, numero_educadoras | — |
| `educadoras` | `id_educadora` | rol, anios_experiencia | `id_jardin` |
| `ninos` | `id_nino` | fecha_nacimiento, sexo_registrado, sala_grupo, fecha_ingreso | `id_jardin` |
| `ruta_niveles` | `nivel` (1–9) | nombre_nivel, edad_min_meses, edad_max_meses, dominios, descripcion | — |
| `manifestaciones` | `id_manifestacion` | nivel, dominio, texto_observable | `nivel` |
| `observaciones` | `id_observacion` | fecha_observacion, formato_captura, nivel_estimado, nota_breve, edad_meses | `id_nino`, `id_educadora` |
| `observacion_manifestaciones` | (compuesta) | — | `id_observacion`, `id_manifestacion` |
| `bitacoras` | `id_bitacora` | periodo, texto_generado, estado (borrador/aprobada), fecha | `id_nino`, `id_educadora` |
| `recomendaciones` | `id_recomendacion` | decision (AVANZAR/MANTENER/RETROCEDER), score, dominios_cubiertos, dominios_pendientes, argumento_ia, version_rubrica, decision_educadora (aceptó/rechazó/ajustó), fecha | `id_nino`, `id_educadora` |
| `rubrica_versiones` | `version_rubrica` | criterios (JSON: N obs, dominios requeridos, umbrales), vigente_desde, descripcion | — |
| `reportes_direccion` | `id_reporte` | periodo, metricas (JSON agregado), resumen_ejecutivo, fecha | `id_jardin` |

(Las 7 primeras vienen del dataset; `bitacoras`, `recomendaciones`, `rubrica_versiones` y `reportes_direccion` son nuevas para persistir la salida de los Modelos 2, 3 y 4.)

### BD 2 — No relacional / vectorial · transcripciones y embeddings
- **OpenSearch Serverless** (nativo AWS) o **pgvector** (simplifica la demo, un solo motor).
- Documento por observación: `{ id_observacion, id_nino, texto_transcrito, embedding[], dominio, nivel, fecha, formato }`.
- Índice vectorial para búsqueda semántica (RAG) + metadatos para filtrado.

---

## 6. Flujo de automatización (end-to-end)

```
[Educadora en sala]
   │ sube texto / audio / foto / video
   ▼
[Frontend PWA] ──POST /observaciones──▶ [API FastAPI]
                                           │
                                           ▼
                              [Servicio de Ingesta]
                                 │ guarda medio en S3
                                 ▼
                       [Servicio de Transcripción]  (Modelo 1)
                          audio→Transcribe  foto→Textract  video→Transcribe+Rekognition
                                 │ texto plano
                                 ▼
                       [Servicio de Clasificación]
                          clasifica dominio+nivel, vincula manifestaciones
                                 │
                     ┌───────────┴────────────┐
                     ▼                         ▼
          [Repo Relacional]           [Servicio de Embeddings]
          guarda observación           embebe texto → Vector DB
          + vínculos                           │
                                               ▼
                                   ... (quincenalmente) ...
                                               ▼
                             [Servicio de Bitácoras]  (Modelo 2, RAG)
                               recupera evidencia del niño → Bedrock → bitácora
                                               │
                                               ▼
                             [Repo Relacional] guarda bitácora (borrador)
                                               │
                                               ▼
                     [Frontend] educadora revisa, edita y APRUEBA
```

**Flujo de recomendación de nivel (Modelo 3) — tiempo real:**
```
[Nueva observación guardada]  ó  [Botón "¿Puede subir de nivel?"]
                 │
                 ▼
   [RecommendationService]
     1. recupera evidencia del niño (relacional + RAG)
     2. aplica RÚBRICA estricta (determinista, versionada) → decisión + score
     3. LLM redacta el argumento (no decide)
                 │
                 ▼
   [Repo Relacional] guarda recomendación (con version_rubrica)
                 │
                 ▼
   [Frontend] muestra AVANZAR/MANTENER/RETROCEDER + argumento
              → la EDUCADORA acepta / rechaza / ajusta (última palabra)
```

**Flujo de reporte de dirección (Modelo 4):**
```
[Botón "Generar reporte" (rol directora)]  ó  [cron quincenal]
                 │
                 ▼
   [DirectorReportService]
     1. agrega métricas del jardín/sala (SQL sobre relacional):
        subieron/mantuvieron/bajaron, distribución niveles, conteos, alertas, KPI tiempo ahorrado
     2. LLM redacta resumen ejecutivo a partir de los agregados
                 │
                 ▼
   [Repo Relacional] guarda reporte
                 │
                 ▼
   [Dashboard de dirección] métricas + resumen ejecutivo
```

Para la demo: los disparos quincenales se exponen también como botones manuales ("Generar bitácora ahora", "¿Puede subir de nivel?", "Generar reporte"). En producción: **EventBridge Scheduler → Lambda**.

---

## 7. Frontend (UX/UI) — mobile-first

**Stack:** React + Vite, PWA instalable.

**Pantallas del MVP (rol educadora):**
1. **Inicio / Mi sala** — lista de niños/as del grupo, con indicador de última observación.
2. **Capturar** — botón grande central: grabar audio, tomar foto, grabar video, o escribir.
3. **Ficha del niño/a** — trayectoria (línea de tiempo de niveles por dominio), observaciones recientes, y botón **"¿Puede subir de nivel?"** que muestra la recomendación (AVANZAR/MANTENER/RETROCEDER) con el argumento de la IA y los dominios cubiertos/pendientes. La educadora acepta / rechaza / ajusta.
4. **Bitácoras** — lista por estado (borrador / aprobada); detalle con edición en línea y botón **Aprobar**.
5. **Confirmación de observación** — tras subir un medio, muestra la clasificación propuesta para confirmar o corregir; si la nueva evidencia cruza el umbral de la rúbrica, aparece la **sugerencia proactiva** de avance.

**Pantalla del MVP (rol directora):**
6. **Dashboard de dirección** — resumen del jardín/sala: cuántos subieron/mantuvieron/bajaron, distribución de niveles por dominio, N° de observaciones y bitácoras (total y por educadora), alertas (retroceso / sin observaciones recientes), KPI de tiempo ahorrado, y el resumen ejecutivo redactado por la IA. Botón **"Generar reporte"**.

En la demo el **rol** (educadora / directora) se cambia con un selector simple, sin auth real.

**Principios UX:** botones grandes, feedback inmediato, offline-friendly (PWA), accesible, español (Chile).

---

## 8. Backend — POO, SOLID, 3 capas

```
backend/
  app/
    api/            # Capa 1 (routers FastAPI) — presentación
      routers/
        observaciones.py
        bitacoras.py
        recomendaciones.py       # Modelo 3
        reportes.py              # Modelo 4 (dirección)
        ninos.py
    services/       # Capa 2 — casos de uso
      transcription_service.py
      classification_service.py
      embedding_service.py
      bitacora_service.py        # Modelo 2: RAG + LLM
      recommendation_service.py  # Modelo 3: rúbrica estricta + LLM explicativo
      director_report_service.py # Modelo 4: agregados + resumen ejecutivo
      ingestion_service.py
    domain/         # Modelos de dominio (POO)
      models.py
      rubrica.py                 # rúbrica de decisión versionada (reglas/umbrales)
    providers/      # Puertos + adaptadores (SOLID: DIP)
      transcription/ (base, aws, mock)
      llm/           (base, bedrock, mock)
      embeddings/    (base, titan, mock)
    repositories/   # Capa 3 — acceso a datos
      relational/    (postgres)
      vector/        (opensearch | pgvector)
      storage/       (s3)
    core/           # config, DI container, settings
    main.py
```

**SOLID aplicado:**
- **S** — cada servicio una responsabilidad.
- **O** — nuevos proveedores de IA se agregan sin tocar los servicios.
- **L** — adaptadores mock y AWS intercambiables.
- **I** — interfaces pequeñas por capacidad.
- **D** — los servicios dependen de interfaces, no de SDKs de AWS → demo sin credenciales AWS usando mocks.

**Modo demo sin AWS:** con `USE_MOCKS=true`, los providers devuelven respuestas plausibles a partir del dataset sintético.

---

## 9. Resguardo de datos sensibles

- Identificación por `id_nino` seudónimo; nunca nombres reales ni RUT.
- Medios en S3 cifrados; URLs prefirmadas de corta vida.
- Prompts al LLM reciben solo texto despersonalizado + rúbrica.
- Separación de datos personales (relacional) y contenido (vectorial).
- Banner permanente: datos sintéticos, uso pedagógico, no diagnóstico.

---

## 10. Resumen de los servicios de IA

| # | Servicio | Qué hace | Dispara | Decide / Argumenta |
|---|---|---|---|---|
| 1 | Transcripción | medio → texto (Transcribe/Textract/Rekognition) | al subir evidencia | — |
| 2 | Bitácora quincenal | narrativa por niño/a (RAG + LLM) | botón / cron | IA redacta |
| 3 | **Recomendación de nivel** | AVANZAR/MANTENER/RETROCEDER | botón + auto al subir evidencia | **rúbrica decide**, IA argumenta, educadora valida |
| 4 | **Reporte de dirección** | agregados del jardín + resumen ejecutivo | botón / cron | SQL agrega, IA redacta |

---

## 11. Qué entrega la demo

- App PWA levantable con un comando, usable desde el celular.
- Backend FastAPI con los **4 modelos/servicios de IA** cableados (mock por defecto, AWS opcional).
- Las 2 BDs sembradas con el dataset E-1.
- **Flujo educadora**: capturar audio → transcribir → clasificar → ver en ficha → **pedir recomendación de nivel** → generar bitácora → aprobar.
- **Flujo directora**: dashboard con subieron/bajaron, distribución de niveles, conteos, alertas, KPI y resumen ejecutivo.
- Script de seed + README.

---

## 12. Otras instancias importantes para el MVP

- **Rúbrica de decisión versionada** (criterios estrictos y auditables; la rúbrica decide, la IA argumenta, la educadora valida).
- **Pantalla de "confirmar clasificación"** (la IA propone, el humano valida).
- **Sugerencia proactiva de avance** al cruzar el umbral de la rúbrica.
- **Datos de seed realistas** desde el dataset E-1.
- **Modo offline / mocks** (hackathon: wifi inestable).
- **Métrica visible del KPI** (contador "tiempo ahorrado" 4h→0h, también en el dashboard de dirección).
- **Trazabilidad de evidencia** en bitácoras y recomendaciones (anti-alucinación, auditable; cada recomendación guarda su `version_rubrica` y la decisión final de la educadora).
- **Roles** educadora / directora (selector simple en la demo).
- **README y arquitectura documentada**.
- **Accesibilidad y español de Chile**.
