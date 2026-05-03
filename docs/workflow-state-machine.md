# Máquina de estados del workflow (vertical slice)

Definición de estados, eventos de auditoría y transiciones permitidas según `app/domain/enums.py`, `app/core/permissions.py` y los servicios de escenario/workflow.

## Estados

- `draft`
- `in_review`
- `published`

## Grafo de transiciones (por estado destino)

| Desde       | Hacia       | Quién / condición |
|-------------|-------------|-------------------|
| `draft`     | `in_review` | Owner envía a revisión (`submit-review`). |
| `published` | `in_review` | Owner envía a revisión **solo si** hay cambios pendientes respecto al snapshot público (republicación). |
| `in_review` | `published` | Coordinador publica (no si es el autor del escenario). |
| `in_review` | `draft`     | Coordinador rechaza (no si es el autor del escenario). |

`ALLOWED_WORKFLOW_TRANSITIONS` en `app/core/permissions.py` codifica los destinos permitidos desde cada estado.

## Eventos en `review_events` (tipos)

Incluye, entre otros (ver `ReviewEventType`):

- `create_draft`
- `draft_saved` — guardado en `draft` (y revision bump + snapshot)
- `submitted` — pasa a `in_review`
- `update_in_review` — guardado de contenido mientras está `in_review` (p. ej. ajustes del coordinador)
- `rejected` — vuelta a `draft`
- `published` — pasa a `published` y actualiza snapshot público
- `collaborator_added` / `collaborator_removed`

## Notas de dominio

- **`draft_saved` vs `update_in_review`**: en ambos casos se versiona en `scenario_revisions`; el tipo de evento refleja si el estado previo era `draft` o `in_review`.
- **Publicar**: actualiza en el mismo paso `public_title`, `public_body_markdown`, `public_slug`, marcas de tiempo de publicación/aprobación y `public_revision_number`.
- **Republicación**: con el escenario en `published`, el owner edita la working copy; si difiere del snapshot, puede volver a `in_review`. La versión pública sigue siendo el snapshot hasta la siguiente publicación.
- Cada transición de estado explícita en workflow genera un `review_events` coherente con `from_state` / `to_state`.

## Invariantes de autorización

- Solo **owner** puede enviar a revisión desde `draft` o desde `published` (con cambios pendientes).
- En **`draft`**, owner y **editors** pueden editar contenido y assets; solo el owner gestiona colaboradores y borra el borrador.
- En **`in_review`**, la edición de contenido la permite el permiso `scenario_update_in_review` (rol **coordinador** en la política actual); el investigador dueño **no** edita el texto en esta fase salvo evolución futura de producto.
- En **`published`**, solo el **owner** edita la working copy (no los editores).
- El coordinador **no** puede publicar ni rechazar si es el `author_user_id` del escenario en `in_review`.
- Endpoints públicos solo exponen escenarios efectivamente publicados (snapshot), no borradores ni colas.
