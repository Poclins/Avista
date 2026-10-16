# jAImes — De la observación a la acción

**IA que le devuelve tiempo a las educadoras de párvulos para que se lo dediquen a los niños y niñas.**

Proyecto para el desafío *"IA para el Desarrollo Infantil"* · **Fundación Integra** · **AWS Breaking Barriers Chile 2026**.

> ⚠️ Todos los datos usados en la demo son **sintéticos (inventados) y seudonimizados** (dataset oficial E-1). jAImes es una herramienta **pedagógica**, no un instrumento clínico ni de diagnóstico.

---

## El problema, en una frase

Las educadoras de párvulos ("tías") dedican alrededor de **4 horas a la semana** a escribir informes a mano sobre cómo avanza cada niño o niña. Ese es tiempo que no están con los párvulos.

## Qué hace jAImes

jAImes toma lo que la educadora ya genera de forma natural durante el día — una nota escrita, una foto de un apunte, un audio o un video — y lo convierte **automáticamente** en:

- **Observaciones ordenadas**: clasifica cada registro por área de desarrollo y nivel.
- **Bitácoras quincenales**: redacta un borrador del informe de cada niño/a, listo para revisar y aprobar.
- **Recomendaciones de nivel**: sugiere si un niño/a puede *avanzar*, *mantenerse* o *retroceder*, siempre citando la evidencia real que respalda la sugerencia.
- **Reportes de dirección**: entrega a la directora del jardín un panorama agregado del avance de su jardín, sin tener que revisar caso por caso.

**La decisión final siempre es de una persona.** jAImes propone y fundamenta; la educadora confirma, corrige o rechaza. La IA nunca decide sola.

### ¿Cómo se traduce en impacto?

El objetivo es llevar esas ~4 horas semanales de documentación hacia **casi cero**, para que ese tiempo vuelva a la sala.

---

## Cómo probarlo en 1 comando (sin cuenta de AWS)

jAImes trae un **modo local** que funciona en tu computador sin internet ni credenciales de AWS: usa una base de datos local y versiones "de prueba" de los servicios de IA. Ideal para la demo.

**Requisitos:** [Python 3.12+](https://www.python.org/downloads/) y [Node.js 18+](https://nodejs.org/) instalados.

Desde la carpeta del proyecto, en PowerShell (Windows):

```powershell
powershell -ExecutionPolicy Bypass -File run_local.ps1
```

Ese comando se encarga de todo: prepara la base de datos con el dataset oficial E-1, levanta el backend y abre la aplicación. Cuando termine verás:

- **La aplicación** (lo que usa la educadora) en  http://localhost:5173
- **La API y su documentación interactiva** en  http://localhost:8000/docs

> Sugerencia para la demo: entra como educadora y elige el jardín `JAR-0009`, sala `SG-A` (19 niños/as).

### Alternativa con Docker

Si prefieres contenedores (incluye una base Postgres real con búsqueda vectorial):

```bash
docker-compose up --build
```

Levanta el backend en http://localhost:8000 y una base de datos `pgvector`.

---

## Cómo está construido (explicado simple)

jAImes está organizado en **3 capas** bien separadas, como una cocina de restaurante: quien atiende las mesas (la app) no toca las ollas (los datos); todo pasa por la cocina (la lógica).

```
Capa 1 · Lo que ve la persona   ->  frontend/   App móvil (PWA) en React
Capa 2 · La lógica del negocio  ->  backend/    API en Python (FastAPI)
Capa 3 · Dónde viven los datos  ->  bases de datos + archivos
Servicios de IA / nube          ->  AWS  (o versiones locales de prueba)
```

### La idea clave: "enchufes" intercambiables

Cada capacidad de IA (transcribir audio, entender imágenes, generar texto, clasificar) y cada almacén de datos está detrás de un **"enchufe" estándar** (una interfaz). Eso permite cambiar entre:

- **AWS real** (el camino principal, para producción), y
- **versiones locales de prueba** (para la demo, sin costo ni credenciales),

**sin cambiar el resto del código**. Es el mismo enchufe; cambia solo lo que conectas.

### Servicios de AWS que usa en modo real

Amazon **Bedrock** (modelos Claude y Titan) para generar texto y entender significado · **Transcribe** (audio a texto) · **Textract** (texto de fotos) · **Rekognition** (análisis de video) · **S3** (archivos) · **Aurora Serverless v2** con PostgreSQL + `pgvector` (datos y búsqueda inteligente). Todo desplegable con **AWS CDK** (infraestructura como código).

---

## Estado del proyecto

| Área | Estado |
|------|--------|
| Dominio y contratos (base del sistema) | ✅ Completo |
| Base de datos relacional + carga del dataset oficial E-1 | ✅ Completo |
| Base de datos vectorial + embeddings (búsqueda inteligente) | ✅ Completo |
| Captura y transcripción multi-formato (texto/audio/foto/video) | ✅ Completo |
| Clasificación de observaciones | ✅ Completo |
| Bitácoras, rúbrica de decisión y recomendaciones (IA + evidencia) | ✅ Completo |
| Reporte de dirección + API REST completa | ✅ Completo |
| Frontend PWA (app para educadora y directora) | ✅ Base funcional |
| Despliegue en AWS (infraestructura CDK) | 🚧 En curso |

La suite de pruebas automatizadas del backend está **en verde (408 pruebas en modo local)**. El plan de trabajo detallado vive en `.kiro/specs/jaimes-mvp/`.

---

## Estructura del repositorio

```
backend/            API en Python (FastAPI) — toda la lógica y la IA
  app/
    api/            Endpoints REST (lo que consume la app)
    services/       Casos de uso (bitácoras, recomendaciones, reportes)
    domain/         Modelos del negocio + rúbrica de decisión determinista
    providers/      "Enchufes" de IA + adaptadores AWS/local
    repositories/   Acceso a datos (relacional, vectorial, archivos)
    core/           Configuración + armado de dependencias
  tests/            Pruebas automatizadas
frontend/           App móvil (PWA) en React + Vite
docs/               Documentación por área (backend, base de datos, nube, frontend)
dataset_e1_publico/ Dataset oficial sintético E-1
docker-compose.yml  Demo con Docker (backend + Postgres/pgvector)
run_local.ps1       Demo local de 1 comando (Windows)
```

---

## Desarrollo

### Backend (sin Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # API en http://localhost:8000
pytest                          # correr las pruebas
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # app en http://localhost:5173
```

Más detalles en `frontend/README.md` y en `docs/`.

---

## Privacidad y uso responsable

- Los niños y niñas se identifican **solo con un seudónimo** (`id_nino`): nunca con nombre real ni RUT.
- Los datos personales y el contenido de las observaciones se guardan **por separado**.
- Antes de enviar cualquier texto a la IA, el sistema **bloquea** datos sensibles (nombres, RUT, direcciones, contactos).
- El dataset de la demo es **sintético**: ningún dato corresponde a una persona real.
