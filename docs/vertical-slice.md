# Vertical slice: auth → revisión → publicación

Este documento describe el **recorrido mínimo ya implementado** en la API y el flujo principal de escenarios. La **especificación funcional de producto** (roles, **RF-1** a **RF-10**) está en [requisitos-funcionales-luneta.md](requisitos-funcionales-luneta.md). La visión en una frase: [README.md](../README.md).

Cuando el código y los RF divergen, **este archivo refleja el código**; los RF marcan el objetivo acordado (p. ej. estados extra del workflow, sugerencias, evaluación ética, cartera revisor–investigador).

## Objetivo

Entregar un recorrido usable de punta a punta:

1. Registro (`signup`) con rol inicial **`registered`**
2. Verificación de correo electrónico
3. Inicio de sesión (cuenta verificada y activa)
4. Promoción a **`investigator`** / **`reviewer`** / **`admin`** por operaciones de **admin** (el registro público no crea investigadores)
5. Crear borrador y editar (propietario y colaboradores con permiso)
6. Enviar a revisión (desde `draft` o desde `published` si hay cambios pendientes de republicación)
7. Cola de revisión y decisión del **revisor** (o **admin**): publicar o devolver a borrador
8. Lectura pública del contenido **publicado** (snapshot en vivo)

Con esto se validan autenticación, RBAC, workflow, persistencia, permisos contextuales sobre escenarios, objetos en MinIO y correo transaccional básico.

## Actores: acceso público y roles de plataforma

### Acceso sin sesión

No es un rol persistido. La política expone permisos de lectura pública vía `permissions_for_anonymous()` en `app/core/rbac_policy.py` (equivalente funcional a **usuario anónimo** en los RF, **RF-7.2** / **RF-7.3**).

- Listar y leer detalle de escenarios **publicados** (`GET /public/scenarios`, `GET /public/scenarios/{slug}`).

### Roles en `UserRole` (`app/domain/enums.py`)

| Rol en producto (RF) | Valor en API | Resumen en el slice |
|----------------------|--------------|---------------------|
| Usuario registrado | `registered` | Cuenta verificada; perfil propio; aún **no** crea escenarios en este slice salvo que se promueva. |
| Investigador | `investigator` | Crea borradores, edita los suyos (y colaboración en `draft`), envía a revisión, borra borradores. |
| Revisor | `reviewer` | Todo lo del investigador **más** cola en revisión, editar en `in_review`, publicar y rechazar (con salvaguardas de autor). |
| Admin | `admin` | Permisos de revisor **más** alta de investigadores, cambio de rol y activar/desactivar cuentas. |

Los permisos atómicos viven en `app/domain/authz_permissions.py`; el mapa rol → permisos en `app/core/rbac_policy.py`. Las reglas **por escenario** (propietario, colaborador, estado) en `app/core/scenario_access.py`.

**Pendiente respecto a los RF:** cartera revisor–investigador (**RF-6.1**), filtro de cola por investigadores a cargo, estados `changes_requested` / `not_suitable`, sugerencias (**RF-4**), evaluación ética (**RF-8**), registro de actividad consultable (**RF-10**).

### Propietario y colaborador (sobre el escenario)

No son roles de plataforma. En persistencia, el escenario tiene `author_user_id` y la lista `collaborators`:

- **`owner`**: coincide con el autor creador; envía a revisión y gestiona colaboradores.
- **`editor`**: puede editar contenido y recursos **solo en `draft`** (no envía a revisión ni gestiona colaboradores).

En **`published`**, solo el **owner** edita la copia de trabajo respecto al snapshot público (republicación). El modelo de **colaborador por sugerencia aceptada** en escenarios publicados (**RF-4**) aún no está en este slice.

## Estados del escenario (implementados)

- `draft`
- `in_review`
- `published`

No hay, en código hoy, `en cola de revisión`, `con cambios requeridos`, `realizando los cambios requeridos` ni `no apto` (**RF-5.1**). Al publicar se actualiza el snapshot público (`public_title`, `public_body_markdown`, `public_slug`, …) en el mismo paso; no hay estado “aprobado sin publicar”.

Transiciones detalladas: [workflow-state-machine.md](workflow-state-machine.md).

## Snapshot público vs borrador de trabajo

- Lo que ve quien accede **sin sesión** es el **snapshot** (`public_*`, `published_at`).
- Con el escenario en `published`, el **owner** puede editar la **working copy** (`title`, `body_markdown`, `slug`, …). Si difiere del snapshot, hay cambios pendientes de republicación (`has_republication_pending` en dominio).
- En **`in_review`**, las respuestas autenticadas pueden exponer `live_public_*` para contrastar lo sometido a revisión con lo que sigue en vivo.

## Reglas de negocio (resumen)

- Solo cuentas con correo **verificado** y **activas** usan rutas autenticadas (salvo las públicas). Login rechaza cuentas no verificadas o desactivadas (**RF-2.1**).
- Cuentas **investigador** creadas por **admin** llevan `must_change_password`: el token de sesión restringe el uso hasta cambiar contraseña (**RF-1.2.3**–**RF-1.2.4**); ver `app/deps/authz.py`.
- Lectura de un escenario autenticado: participantes; **revisor**/**admin** si está `in_review`; cualquiera con permiso público si está `published`.
- **Edición de contenido**
  - `draft`: **owner** y **editors**.
  - `in_review`: permiso `scenario_update_in_review` (**revisor** / **admin**).
  - `published`: solo **owner** (working copy).
- Solo el **owner** puede `submit-review` desde `draft`; desde `published`, solo si ya hubo publicación y hay cambios pendientes de republicación.
- Solo **revisor** / **admin** (con salvaguardas de autor) publican desde `in_review` o rechazan a `draft`. No hay aún “marcar no apto” ni reapertura (**RF-5.8**–**RF-5.9**).
- El **revisor** no puede publicar ni rechazar un escenario en `in_review` del que es **`author_user_id`** (evita auto-revisión). El **admin** sigue las mismas comprobaciones de autor en el código actual salvo evolución explícita.
- Borrado: solo **borrador**, solo el **autor** (`soft delete` con `deleted_at`).
- Cada guardado relevante crea snapshot en `scenario_revisions` y un evento en `review_events` (`draft_saved`, `update_in_review`, `submitted`, `published`, `rejected`, colaboradores, etc.). La consulta global de eventos para **admin** (**RF-10**) no está expuesta aún como producto.
- Imágenes (portada e inline) en MinIO; URLs de lectura firmadas para quien puede leer el escenario.

## Colecciones MongoDB relevantes

- `users`, `email_verification_tokens`
- `scenarios` (colaboradores, assets, campos públicos y de workflow)
- `scenario_revisions`, `review_events`
- `orgs` (listado auxiliar; no forma parte del workflow de escenarios)

## API del slice (prefijos reales)

Rutas relativas al origen de la API (p. ej. `http://localhost:8000`). Esquemas: OpenAPI en `/docs` (FastAPI) y `packages/contracts` si aplica.

### Auth

- `POST /auth/signup`
- `POST /auth/verify-email`
- `POST /auth/login`
- `GET /auth/me`
- `PATCH /auth/me`
- `POST /auth/me/avatar`
- `DELETE /auth/me/avatar`
- `POST /auth/me/change-password`
- `GET /auth/dev/last-email-verification` (solo desarrollo)

### Admin (RF-1)

- `POST /admin/users/investigators` — alta directa de investigador (contraseña temporal, `must_change_password`)
- `PATCH /admin/users/{user_id}/role` — p. ej. `registered` → `investigator`, `investigator` → `reviewer`
- `PATCH /admin/users/{user_id}/account-status` — activar / desactivar

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

### Workflow (revisor / admin)

- `GET /workflow/review-queue` — hoy lista todos los `in_review` (sin filtro por cartera)
- `POST /workflow/scenarios/{scenario_id}/publish`
- `POST /workflow/scenarios/{scenario_id}/reject` — vuelve a `draft`

### Público (sin auth)

- `GET /public/scenarios`
- `GET /public/scenarios/{slug}`

## Correo transaccional (implementado en el slice)

Implementación: `app/services/mailer_service.py`.

- Verificación de registro y confirmación de correo verificado.
- Aviso al cambiar contraseña.
- Aviso al **revisor** verificado cuando un escenario pasa a `in_review`.
- Aviso al **autor** verificado cuando se publica (con slug público).

Ampliaciones previstas (sugerencias, cambios requeridos, no apto, etc.): [email-notificaciones-ampliaciones-futuras.md](email-notificaciones-ampliaciones-futuras.md).

## Fuera de alcance de este slice (véase RF completos)

| Ámbito | Referencia RF |
|--------|----------------|
| Sugerencias de cambio y colaboración por sugerencia aceptada | **RF-4** |
| Estados de workflow ampliados, nota estructurada de cambios, no apto / reapertura | **RF-5** |
| Asignación revisor–investigador y cola acotada por cartera | **RF-6** |
| Búsqueda pública con filtros avanzados; listado propio con colaborador por RF-4 | **RF-7** |
| Evaluación ética, catálogo de riesgos, moderación | **RF-8** |
| Validación de datos sensibles e IA de similitud | **RF-9** |
| Registro de actividad consultable y eventos obligatorios completos | **RF-10** |
| Recuperación de contraseña por correo, autosave, editor rico, panel analytics | backlog / ampliaciones |

## Máquina de estados

Transiciones e invariantes del **código actual**: [workflow-state-machine.md](workflow-state-machine.md).
