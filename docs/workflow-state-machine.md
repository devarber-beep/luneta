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

| Desde       | Evento      | Hacia       | Actor      |
|-------------|-------------|-------------|------------|
| `draft`     | `submitted` | `in_review` | `author`   |
| `in_review` | `approved`  | `approved`  | `reviewer` |
| `approved`  | `published` | `published` | `reviewer` |

Notas:

- `draft_saved` no cambia estado; crea/actualiza revision.
- El estado `published` es terminal para esta version minima.
- No se define evento de rechazo en esta fase.

## Invariantes

- Solo el autor puede mutar contenido cuando el estado es `draft`.
- Si estado != `draft`, el contenido del escenario no se edita en esta fase.
- Cada transicion de estado agrega un registro en `review_events`.
