# Vertical slice: auth → revisión → publicación

Este documento describe el **alcance funcional mínimo ya cubierto por la API y el flujo principal** de Luneta. La **especificación funcional alineada al código** (requisitos vigentes **RF-V-xxx**, backlog **US-xxx**, NFRs) está en [requisitos-funcionales-luneta.md](requisitos-funcionales-luneta.md). La visión en una frase: [README.md](../README.md).

## Objetivo

Entregar un recorrido usable de punta a punta:

1. Registro (`signup`)
2. Verificación de email
3. Inicio de sesión
4. Crear borrador y editar (solo autor y colaboradores con permiso)
5. Enviar a revisión (desde `draft` o desde `published` si hay cambios pendientes de republicación)
6. Cola de revisión y decisión del coordinador: publicar o devolver a borrador
7. Lectura pública del contenido **publicado** (snapshot en vivo)

Con esto se validan auth, roles, workflow, persistencia, permisos, objetos en MinIO y correo transaccional básico.

## Actores y roles

- **`investigator`**: crea borradores, edita los suyos (y los compartidos como editor en `draft`), envía a revisión cuando corresponde, puede borrar sus borradores.
- **`coordinator`**: incluye todo lo anterior **más** ver la cola en revisión, **editar escenarios en `in_review`**, publicar y rechazar. No puede publicar ni rechazar un escenario **del que es autor** mientras esté en revisión (evita auto-revisión).
- **Anónimo (`public`)**: solo lectura de escenarios publicados (lista y detalle por slug), sin sesión.

Los permisos atómicos viven en `app/domain/authz_permissions.py`; el mapa rol → permisos en `app/core/rbac_policy.py`.

## Colaboración en escenario

Cada escenario tiene una lista `collaborators` con roles:

- **`owner`**: siempre el autor (`author_user_id`); quien puede enviar a revisión y gestionar colaboradores.
- **`editor`**: puede editar contenido y recursos **solo en estado `draft`** (no puede enviar a revisión ni añadir/quitar colaboradores).

En **`published`**, solo el **owner** puede modificar el borrador de trabajo (título, cuerpo, slug, etc.) respecto al snapshot público; eso habilita la **republicación** (ver máquina de estados).

## Estados del escenario

- `draft`
- `in_review`
- `published`

No hay estado intermedio tipo “aprobado sin publicar”: al publicar se actualiza el snapshot público (`public_title`, `public_body_markdown`, `public_slug`, …) en el mismo paso.

## Snapshot público vs borrador de trabajo

- Lo que ve el visitante anónimo es el **snapshot** alineado con `public_*` y `published_at`.
- Mientras el escenario está `published`, el autor puede seguir editando **working copy** (`title`, `body_markdown`, `slug`, …). Si difiere del snapshot, hay “cambios pendientes de republicación” (`has_republication_pending` en dominio).
- En **`in_review`**, las respuestas autenticadas pueden exponer `live_public_*` para mostrar qué hay en vivo frente a lo sometido a revisión.

## Reglas de negocio (resumen)

- Solo usuarios con email verificado usan rutas que exigen autenticación (salvo las públicas).
- Lectura de un escenario: participantes (colaboradores + autor); coordinador si está `in_review`; cualquiera si está `published` vía rutas públicas.
- **Edición de contenido**
  - `draft`: owner y editors.
  - `in_review`: solo quien tenga permiso `scenario_update_in_review` (hoy: **coordinador**).
  - `published`: solo **owner** (editar working copy; no los editores).
- Solo el **owner** puede `submit-review` desde `draft`; desde `published`, solo si ya fue publicado al menos una vez y hay cambios pendientes de republicación.
- Solo el coordinador (con las salvaguardas de autor) publica desde `in_review` o rechaza a `draft`.
- Borrado: solo borrador, solo el **autor** (`soft delete` con `deleted_at`).
- Cada guardado relevante crea snapshot en `scenario_revisions` y un evento en `review_events` (tipos como `draft_saved`, `update_in_review`, etc.).
- Objetos de imagen (portada e inline) en MinIO; URLs de lectura firmadas para quien puede leer el escenario.

## Colecciones MongoDB relevantes

- `users`, `email_verification_tokens`
- `scenarios` (incl. colaboradores, assets, campos públicos y de workflow)
- `scenario_revisions`, `review_events`
- `orgs` (listado auxiliar para la app; no forma parte del workflow de escenarios)

## API del slice (prefijos reales)

Rutas relativas al origen de la API (p. ej. `http://localhost:8000`). Detalle de esquemas: OpenAPI en `packages/contracts` / `/docs` en FastAPI.

### Auth

- `POST /auth/signup`
- `POST /auth/verify-email`
- `POST /auth/login`
- `GET /auth/me`
- `PATCH /auth/me`
- `POST /auth/me/change-password`
- `GET /auth/dev/last-email-verification` (solo entorno de desarrollo)

### Organizaciones (auxiliar)

- `GET /orgs`

### Escenarios (autenticado)

- `POST /scenarios`
- `GET /scenarios/mine`
- `GET /scenarios/{scenario_id}`
- `PATCH /scenarios/{scenario_id}`
- `DELETE /scenarios/{scenario_id}`
- `POST /scenarios/{scenario_id}/submit-review`
- `GET /scenarios/{scenario_id}/collaborators`
- `POST /scenarios/{scenario_id}/collaborators`
- `DELETE /scenarios/{scenario_id}/collaborators/{user_id}`
- `POST /scenarios/{scenario_id}/assets/cover`
- `POST /scenarios/{scenario_id}/assets/inline`
- `DELETE /scenarios/{scenario_id}/assets/cover`
- `DELETE /scenarios/{scenario_id}/assets/inline/{asset_id}`
- `POST /scenarios/{scenario_id}/assets/inline/reorder`
- `GET /scenarios/{scenario_id}/assets/{asset_id}/read-url`

### Workflow (coordinador)

- `GET /workflow/review-queue`
- `POST /workflow/scenarios/{scenario_id}/publish`
- `POST /workflow/scenarios/{scenario_id}/reject`

### Público (sin auth)

- `GET /public/scenarios`
- `GET /public/scenarios/{slug}`

## Correo transaccional (implementado en el slice)

Implementación: `app/services/mailer_service.py` (`MailerService`).

- `send_verification_email` / `send_email_verified_confirmation` en el flujo de registro y verificación.
- `send_password_changed_notification` al cambiar contraseña.
- `send_scenario_submitted_for_review` a cada coordinador verificado al pasar a `in_review`.
- `send_scenario_live_to_author` al publicar (autor verificado, con slug público).

Ideas no implementadas o ampliaciones: [email-notificaciones-ampliaciones-futuras.md](email-notificaciones-ampliaciones-futuras.md).

## Fuera de alcance de este slice

- Comentarios de revisión y rechazo con feedback estructurado
- Autosave y editor rico avanzado
- IA asistida, detección de similitud, ratings en producción
- Panel de administración genérico y analytics
- Recuperación de contraseña por email (ver doc de ampliaciones)

## Máquina de estados

Transiciones e invariantes detalladas: [workflow-state-machine.md](workflow-state-machine.md).
