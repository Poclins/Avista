# Documentación de jAImes

Documentación de arquitectura organizada por área para que no quede dispersa. Cada subcarpeta tiene su README y diagramas Mermaid.

- [`backend/`](backend/README.md) — Capa 2: servicios, dominio, puertos/adaptadores, DI, SOLID, módulos interface-first. Incluye [`rubrica.md`](backend/rubrica.md).
- [`database/`](database/README.md) — Capa 3: modelo relacional E-1 + tablas nuevas ([`esquema.md`](database/esquema.md)) y base vectorial pgvector ([`vectorial.md`](database/vectorial.md)).
- [`cloud/`](cloud/README.md) — Infra AWS serverless: [`cdk.md`](cloud/cdk.md), [`despliegue.md`](cloud/despliegue.md), [`integracion.md`](cloud/integracion.md).
- [`frontend/`](frontend/README.md) — Capa 1: PWA y consumo de la API (pendiente Figma).
- [`MVP_BLUEPRINT.md`](MVP_BLUEPRINT.md) — visión global del producto.

El spec formal (requirements, design, tasks) vive en `.kiro/specs/jaimes-mvp/`.
