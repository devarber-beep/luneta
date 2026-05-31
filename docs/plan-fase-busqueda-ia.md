# Plan: búsqueda (RF-7) e IA (RF-9)

Estado de referencia: rama `feat/evaluations` (evaluaciones RF-8, sugerencias anónimas RF-4.1.5, admin moderación).

## Hecho recientemente (no repetir)

| Bloque | Estado |
|--------|--------|
| RF-4 sugerencias + colaboradores | Implementado |
| RF-8 evaluaciones + moderación admin | Implementado (`feat/evaluations`) |
| RF-7.2 lectura pública lista/detalle | Lista simple sin búsqueda ni paginación |
| RF-7.3 `/scenarios/mine` | Implementado |
| RF-9 / RF-3.4 / RF-10.9–10.10 | **No implementado** |

## Pendiente global (visión corta)

1. **RF-7.1** — Búsqueda pública con texto, filtros, orden, paginación.
2. **RF-9.1** — Revisión de datos sensibles antes de enviar a revisión (bloqueo + mensajes sin filtrar PII).
3. **RF-9.2** — Detección de similitud con IA al crear/editar (RF-3.4, RF-10.9).
4. **RF-10** — UI de auditoría (consultas RF-10.8); hoy solo escritura parcial.
5. **RF-8.3** — Alinear aspectos de evaluación con catálogo completo del doc (si se mantiene alcance).
6. **Notificaciones in-app** (RF-4.4.3 canal interno).
7. **Merge** `feat/evaluations` → `main` cuando el PR esté listo.

## Fase actual: RF-7.1 (esta rama)

### Entregables MVP

| ID | Entregable |
|----|------------|
| 7.1.1 | Parámetro `q` sobre título, descripción pública y resumen (y keywords si existen). |
| 7.1.2 | Filtros `author_user_id`, rango `published_from` / `published_to`, `category_ids`, `ethical_risk_ids`. |
| 7.1.3 | Filtros por propiedades = categorías + riesgos éticos del escenario (MVP). |
| 7.1.4 | Orden por `published_at` descendente. |
| 7.1.5 | Respuesta paginada (`page`, `page_size`, `total`, `items`). |
| 7.1.6 | Mismo endpoint usable sin login; autenticados ven catálogo publicado de otros. |

### API prevista

- `GET /public/scenarios` — pasa a devolver `{ items, total, page, page_size }` con query opcionales (rompe array plano; actualizar front).
- Tests HTTP con fake DB.

### UI prevista

- Buscador en **home** sobre escenarios publicados (paginación vía API).
- Buscador en **mis escenarios** y **cola de revisión** (filtrado en cliente sobre la lista cargada).

## Siguiente fase: RF-9 (después de 7.1)

### Decisiones a tomar antes de codificar

- Proveedor IA (OpenAI, Azure, local, mock en dev).
- Embeddings vs LLM para similitud (RF-9.2).
- Reglas/heurísticas para PII (RF-9.1) vs modelo.
- Modelo de persistencia: `ai_assistance_runs`, `sensitive_data_checks` (RF-10.9, RF-10.10).

### Orden sugerido RF-9

1. **RF-9.1** — Comprobación determinista + extensible (emails, teléfonos, DNI…) en `submit-review`; registro RF-10.10.
2. **RF-9.2** — Puerto `SimilarityProvider` + implementación mock/stub; UI en editor; registro RF-10.9.
3. Integración proveedor real y afinado de umbrales.

## Criterios de “fase 7.1 cerrada”

- Tests API verdes para búsqueda, filtros y paginación.
- Home, mis escenarios y cola de revisión con buscador integrado.
- Doc RF-7.1 sin huecos obvios respecto al MVP descrito arriba.
