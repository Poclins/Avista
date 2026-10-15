# Esquema relacional (dataset E-1 + tablas nuevas)

Fuente de verdad: `backend/app/repositories/schema.py` (SQLAlchemy 2.0). Tipos y nulabilidad siguen el diccionario de datos E-1: fechas `AAAA-MM-DD`; `observaciones.nota_breve` admite vacío; `observaciones.nivel_estimado` y `edad_meses` opcionales hasta clasificar/derivar. Las estructuras (criterios de rúbrica, métricas, listas de dominios) se guardan como `JSON` para portar entre SQLite (demo) y Postgres (AWS).

## Tablas del dataset E-1

| Tabla | PK | Campos clave | FKs |
|---|---|---|---|
| `jardines` | `id_jardin` | nombre_fantasia, comuna, region, numero_salas, numero_educadoras | — |
| `educadoras` | `id_educadora` | rol, anios_experiencia | `id_jardin` |
| `ninos` | `id_nino` | fecha_nacimiento, sexo_registrado, sala_grupo, fecha_ingreso | `id_jardin` |
| `ruta_niveles` | `nivel` (1–9) | nombre_nivel, edad_min_meses, edad_max_meses, dominios (JSON), descripcion | — |
| `manifestaciones` | `id_manifestacion` | nivel, dominio, texto_observable | `nivel` |
| `observaciones` | `id_observacion` | fecha_observacion, formato_captura, nivel_estimado?, nota_breve?, edad_meses? | `id_nino`, `id_educadora` |
| `observacion_manifestaciones` | (id_observacion, id_manifestacion) | — | ambos FKs |

## Tablas nuevas (Modelos 2, 3 y 4)

| Tabla | PK | Campos clave | FKs |
|---|---|---|---|
| `bitacoras` | `id_bitacora` | periodo, texto_generado, estado (borrador/aprobada), fecha | `id_nino`, `id_educadora` |
| `recomendaciones` | `id_recomendacion` | decision, score, dominios_cubiertos (JSON), dominios_pendientes (JSON), argumento_ia, decision_educadora?, fecha | `id_nino`, `id_educadora`, `version_rubrica` |
| `rubrica_versiones` | `version_rubrica` | criterios (JSON), vigente_desde, descripcion | — |
| `reportes_direccion` | `id_reporte` | periodo, metricas (JSON), resumen_ejecutivo, fecha | `id_jardin` |

## Notas de privacidad

`ninos` no tiene columnas de nombre real ni RUT (Requirement 11.1). `recomendaciones.decision` la calcula la rúbrica determinista; `argumento_ia` lo redacta el LLM; `decision_educadora` registra la decisión humana final y puede ser `NULL` hasta que la educadora resuelva.
