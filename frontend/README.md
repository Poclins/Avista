# jAImes — Frontend (PWA React + Vite)

PWA **mobile-first** en español de Chile que consume **únicamente** la API REST
del backend (Módulo G). El cliente no contiene lógica de negocio: solo UI +
llamadas REST (Requirement 9.6).

Esta es la **base del frontend (Tarea 12)**: inicialización PWA, capa de
servicios API tipada, router por rol y componentes transversales. Las pantallas
definitivas (MiSala, Capturar, ConfirmarClasificacion, FichaNino, Bitacoras,
DashboardDireccion) son **placeholder** y se completan en la **Tarea 13** a
partir de los mockups de Figma (Requirement 9.5).

## Stack

- **React 18 + Vite 5** (TypeScript).
- **vite-plugin-pwa** para el web app manifest y el service worker.
- **react-router-dom** para el enrutamiento por rol.

## Estructura

```
frontend/
├─ index.html
├─ vite.config.ts            # React + PWA (manifest + service worker)
├─ public/favicon.svg
└─ src/
   ├─ api/                   # capa de servicios API tipada
   │  ├─ types.ts            # tipos del contrato REST
   │  ├─ client.ts           # fetch + timeout 10 s + ApiError en español
   │  ├─ endpoints.ts        # una función por endpoint del contrato
   │  ├─ client.test.ts      # pruebas del cliente (vitest)
   │  └─ index.ts
   ├─ roles/RolContext.tsx   # rol activo (educadora | directora)
   ├─ routes/                # router por rol + guard + inicio
   ├─ layout/AppLayout.tsx   # banner + selector de rol + navegación
   ├─ components/            # SelectorRol, BannerDatosSinteticos,
   │                         # IndicadorCarga, MensajeError
   ├─ hooks/useAccionApi.ts  # carga/error sin descartar datos del formulario
   ├─ screens/               # pantallas placeholder (Tarea 13 desde Figma)
   └─ styles/global.css      # mobile-first 320–1024 px, controles ≥44×44 px
```

## Contrato REST consumido

```
POST   /ninos/{id}/observaciones
PATCH  /observaciones/{id}/clasificacion
GET    /ninos/{id}/observaciones
GET    /ninos/{id}
GET    /ninos?sala=...
POST   /ninos/{id}/bitacoras
GET    /ninos/{id}/bitacoras
PATCH  /bitacoras/{id}
POST   /ninos/{id}/recomendaciones
POST   /recomendaciones/{id}/decision
GET    /jardines/{id}/reportes
GET    /ruta-niveles
GET    /health
```

## Decisiones de UX (Requirements 8 y 9)

- **Roles mutuamente excluyentes** `educadora`/`directora` con `SelectorRol`
  (sin autenticación real en la demo); guard que exige elegir rol.
- **Banner persistente** de datos sintéticos de uso pedagógico en todas las
  pantallas (`BannerDatosSinteticos`).
- **Indicador de progreso** (`IndicadorCarga`) que se activa de forma síncrona
  (≤100 ms) y se mantiene hasta la respuesta del backend.
- **Timeout de 10 s** por solicitud; ante fallo o timeout se muestra un mensaje
  en español y **no se descartan** los datos ingresados (`useAccionApi` +
  `MensajeError`).
- **Mobile-first** 320–1024 px; controles táctiles ≥ 44 × 44 px CSS.

## Comandos

Requiere **Node.js 18+**.

```bash
cd frontend
cp .env.example .env     # ajustar VITE_API_BASE_URL si es necesario
npm install
npm run dev              # servidor de desarrollo (proxy /api → :8000)
npm run build            # typecheck + build de producción (genera el SW)
npm run preview          # previsualizar el build
npm run lint             # ESLint
npm run test             # pruebas (vitest)
```

Variable de entorno:

- `VITE_API_BASE_URL` — base de la API REST. En desarrollo puede quedar en
  `/api` para usar el proxy de Vite hacia `http://localhost:8000`.
