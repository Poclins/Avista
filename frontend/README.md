# Avista · Frontend (PWA)

React 19 + TypeScript + Vite 8 + Tailwind CSS v4, installable as a PWA (`vite-plugin-pwa`).
Visual language: "warm parchment notebook" (see [`docs/frontend/slite-style-reference.md`](../docs/frontend/slite-style-reference.md)).

```bash
npm install
npm run dev        # http://localhost:5173  (proxies /api → http://localhost:8000)
npm run build      # dist/ (served by FastAPI in the Lambda image)
npm run typecheck
```

| Folder | Contents |
|---|---|
| `src/components/` | One component per screen/modal: room, capture, radar, scaffolding, vision, practice bank, logs, recommendations, director, architecture |
| `src/services/aiService.ts` | AI plugs: `local_e1` (deterministic, offline) and `cloud_ia` (Gemini 2.5 Flash, falls back to local on error) |
| `src/services/privacyService.ts` | Avista Privacy Guard: masks RUT, phones, addresses and names before classification |
| `src/data/` | Embedded demo room (JAR-0009 · SG-A, 19 children) and the Integra practice bank |
| `src/hooks/usePWAInstall.ts` | Install prompt, iOS guide and online/offline status |

`VITE_GEMINI_API_KEY` (optional, see `.env.example`) enables the live mode. It is bundled into the client, so only use a restricted demo key.

See the [root README](../README.md) for the full architecture.
