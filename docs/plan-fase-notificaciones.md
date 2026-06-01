# Plan: notificaciones (canal in-app + email)

Estado: rama `feat/notifications`. Canal in-app + email (donde aplica en `MailerService`) implementados.

## Modelo (`notifications` en Mongo)

Un documento **por destinatario y evento**. Campos principales: `recipient_user_id`, `notification_type`, `title`, `message`, `entity_type` + `entity_id`, `scenario_id` opcional, `actor_user_id`, `link_path`, `payload`, `read_at`, `created_at`.

## Catálogo de tipos (`NotificationType`)

| Tipo | Destinatario | Origen lógico / RF |
|------|--------------|-------------------|
| `suggestion_received` | Propietario | Nueva sugerencia (RF-4.4.1) |
| `suggestion_accepted` | Sugerente | Sugerencia aceptada (RF-4.4.2) |
| `suggestion_rejected` | Sugerente | Sugerencia rechazada (RF-4.4.2) |
| `scenario_submitted_for_review` | Revisores asignados al autor | Envío a cola (RF-5.3.3) |
| `scenario_review_published` | Propietario | Publicación (RF-5.4.5) |
| `scenario_review_changes_required` | Propietario | Cambios requeridos (RF-5.4.4, 5.5.3) |
| `scenario_review_not_suitable` | Propietario | No apto (RF-5.4.3, 5.8.3) |
| `scenario_reopened` | Propietario | Reapertura admin (RF-5.9.3) |
| `collaborator_added` | Nuevo colaborador | Alta como colaborador (lógica producto) |
| `investigator_invited` | Nuevo investigador | Alta por admin |
| `account_disabled` / `account_reactivated` | Usuario afectado | Desactivación / reactivación |
| `user_role_changed` | Usuario afectado | Promoción de rol |
| `scenario_evaluation_received` | Propietario | Nueva evaluación ética en publicado |
| `password_changed` | Usuario | Cambio de contraseña |

## Orden de implementación

1. ~~Modelo + repositorio~~ (hecho)
2. ~~`NotificationService`: crear in-app + delegar email existente~~ (hecho)
3. ~~API: `GET /notifications`, marcar leída, contador no leídas~~ (hecho)
4. ~~UI: campana / bandeja en SPA~~ (hecho; barra fija en rutas autenticadas vía `SessionToolbar`)
5. ~~Enganchar disparadores~~ (hecho: sugerencias, escenarios, workflow, evaluaciones, admin, cambio de contraseña)
6. ~~Tests HTTP por disparador~~ (`tests/http/test_notification_triggers.py`)

## Criterio RF-4.4.3

Cada disparador debe generar **fila in-app** y, si el usuario tiene email verificado, el **correo** ya implementado (o ampliado) en `MailerService`.
