# Workflow State Machine (Vertical Slice)

Definicion de transiciones permitidas para el flujo minimo.

## Estados

- `draft`
- `in_review`
- `approved`
- `published`

## Eventos

- `draft_saved`
- `submitted`
- `approved`
- `published`

## Transiciones validas

| Desde       | Evento      | Hacia       | Actor          |
|-------------|-------------|-------------|----------------|
| `draft`     | `submitted` | `in_review` | `investigator` |
| `in_review` | `approved`  | `approved`  | `coordinator`  |
| `approved`  | `published` | `published` | `coordinator`  |

Notas:

- `draft_saved` no cambia estado; crea/actualiza revision.
- El estado `published` es terminal para esta version minima.
- Rechazo (`in_review` → `draft`) lo realiza un `coordinator` (ver API actual).

## Invariantes

- Solo el autor puede mutar contenido cuando el estado es `draft`.
- Si estado != `draft`, el contenido del escenario no se edita en esta fase.
- Cada transicion de estado agrega un registro en `review_events`.
