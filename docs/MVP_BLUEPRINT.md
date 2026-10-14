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

(Las 7 primeras vienen del dataset; `bitacoras` es nueva para persistir la salida del Modelo 2.)

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

Para la demo: el disparo quincenal se expone también como botón manual ("Generar bitácora ahora"). En producción: **EventBridge Scheduler → Lambda**.

---

## 7. Frontend (UX/UI) — mobile-first

**Stack:** React + Vite, PWA instalable.

**Pantallas del MVP:**
1. **Inicio / Mi sala** — lista de niños/as del grupo, con indicador de última observación.
2. **Capturar** — botón grande central: grabar audio, tomar foto, grabar video, o escribir.
3. **Ficha del niño/a** — trayectoria (línea de tiempo de niveles por dominio), observaciones recientes.
4. **Bitácoras** — lista por estado (borrador / aprobada); detalle con edición en línea y botón **Aprobar**.
5. **Confirmación de observación** — tras subir un medio, muestra la clasificación propuesta para confirmar o corregir.

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
        ninos.py
    services/       # Capa 2 — casos de uso
      transcription_service.py
      classification_service.py
      embedding_service.py
      bitacora_service.py        # RAG + LLM
      ingestion_service.py
    domain/         # Modelos de dominio (POO)
      models.py
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

## 10. Qué entrega la demo

- App PWA levantable con un comando, usable desde el celular.
- Backend FastAPI con los 2 modelos cableados (mock por defecto, AWS opcional).
- Las 2 BDs sembradas con el dataset E-1.
- Flujo completo: capturar audio → transcribir → clasificar → ver en ficha → generar bitácora → aprobar.
- Script de seed + README.

---

## 11. Otras instancias importantes para el MVP

- **Pantalla de "confirmar clasificación"** (la IA propone, el humano valida).
- **Datos de seed realistas** desde el dataset E-1.
- **Modo offline / mocks** (hackathon: wifi inestable).
- **Métrica visible del KPI** (contador "tiempo ahorrado" 4h→0h).
- **Trazabilidad de evidencia en la bitácora** (anti-alucinación, auditable).
- **README y arquitectura documentada**.
- **Accesibilidad y español de Chile**.
