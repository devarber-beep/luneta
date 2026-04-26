# Vertical Slice: Auth -> Review -> Publish

Este documento define el alcance funcional minimo del primer flujo usable de Luneta.

## Objetivo

Entregar un journey completo de punta a punta:

1. Signup
2. Verify email
3. Login
4. Crear draft
5. Submit review
6. Approve
7. Publish
8. Public read

Con este slice validamos auth, roles, workflow, persistencia, permisos y publicacion.

## Roles minimos

- `investigator`: crea y edita su draft; puede enviarlo a revision.
- `coordinator`: ve la cola de revision; aprueba, rechaza y publica.
- `public`: solo lectura de escenarios publicados, sin login.

## Estados minimos del escenario

- `draft`
- `in_review`
- `approved`
- `published`

## Reglas de negocio

- Solo usuario verificado puede usar endpoints autenticados.
- Solo el autor del escenario puede editar su `draft`.
- Solo `coordinator` puede aprobar y publicar.
- Solo escenarios `published` son visibles en endpoints publicos.
- Cada guardado de draft crea/actualiza una revision en `scenario_revisions`.
- Cada transicion de estado genera un evento en `review_events`.

## Colecciones MongoDB para el slice

- `users`
- `email_verification_tokens`
- `scenarios`
- `scenario_revisions`
- `review_events`

Separar `scenario_revisions` y `review_events` evita sobrecargar el documento principal de `scenarios` con historicos que crecen en el tiempo.

## Endpoints del slice

### Auth

- `POST /auth/signup`
- `POST /auth/verify-email`
- `POST /auth/login`
- `GET /auth/me`

### Investigator / Scenario

- `POST /scenarios`
- `GET /scenarios/{id}`
- `PATCH /scenarios/{id}`
- `POST /scenarios/{id}/submit-review`

### Workflow (coordinator)

- `GET /workflow/review-queue`
- `POST /workflow/scenarios/{id}/approve`
- `POST /workflow/scenarios/{id}/publish`

### Public

- `GET /public/scenarios/{slug}`

## Fuera de alcance en este slice

- Comentarios de review
- Rechazo con feedback complejo
- Autosave
- Editor rico avanzado
- IA asistida
- Notificaciones internas
- Panel admin generico
- Analytics
