import { getFetchErrorMessage, request } from "./api";

export type CatalogEntry = { id: string; label: string };

export type AdminCatalogEntry = CatalogEntry & {
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type AdminUserSummary = {
  user_id: string;
  nickname: string;
  email_normalized: string;
  role: string;
};

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function listAdminClassification(token: string): Promise<{ items: AdminCatalogEntry[] }> {
  return request("/admin/catalog/scenario-classification", { headers: authHeaders(token) });
}

export async function createAdminClassification(
  token: string,
  payload: { label: string; sort_order?: number },
): Promise<AdminCatalogEntry> {
  return request("/admin/catalog/scenario-classification", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function patchAdminClassification(
  token: string,
  entryId: string,
  payload: { label?: string; sort_order?: number; is_active?: boolean },
): Promise<AdminCatalogEntry> {
  return request(`/admin/catalog/scenario-classification/${entryId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function listAdminEthicalRisks(token: string): Promise<{ items: AdminCatalogEntry[] }> {
  return request("/admin/catalog/ethical-risks", { headers: authHeaders(token) });
}

export async function createAdminEthicalRisk(
  token: string,
  payload: { label: string; sort_order?: number },
): Promise<AdminCatalogEntry> {
  return request("/admin/catalog/ethical-risks", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function patchAdminEthicalRisk(
  token: string,
  entryId: string,
  payload: { label?: string; sort_order?: number; is_active?: boolean },
): Promise<AdminCatalogEntry> {
  return request(`/admin/catalog/ethical-risks/${entryId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function listAdminUsers(token: string, role?: string): Promise<AdminUserSummary[]> {
  const q = role ? `?role=${encodeURIComponent(role)}` : "";
  return request(`/admin/users/summary${q}`, { headers: authHeaders(token) });
}

export async function listReviewerInvestigators(
  token: string,
  reviewerId: string,
): Promise<{ reviewer_user_id: string; investigator_user_ids: string[] }> {
  return request(`/admin/reviewers/${reviewerId}/investigators`, { headers: authHeaders(token) });
}

export async function assignInvestigator(token: string, reviewerId: string, investigatorId: string): Promise<void> {
  const response = await fetch(
    `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/admin/reviewers/${reviewerId}/investigators/${investigatorId}`,
    { method: "PUT", headers: authHeaders(token) },
  );
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
}

export async function unassignInvestigator(
  token: string,
  reviewerId: string,
  investigatorId: string,
): Promise<void> {
  const response = await fetch(
    `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/admin/reviewers/${reviewerId}/investigators/${investigatorId}`,
    { method: "DELETE", headers: authHeaders(token) },
  );
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
}

export async function fetchActiveCategories(token: string): Promise<{ items: CatalogEntry[] }> {
  return request("/catalog/scenario-classification", { headers: authHeaders(token) });
}

export async function fetchActiveEthicalRisks(token: string): Promise<{ items: CatalogEntry[] }> {
  return request("/catalog/ethical-risks", { headers: authHeaders(token) });
}

export type AdminEvaluationModerationTarget = {
  scenario_id: string;
  title: string;
  published_at: string;
  evaluation_count: number;
};

export async function listAdminEvaluationModerationTargets(
  token: string,
): Promise<{ items: AdminEvaluationModerationTarget[] }> {
  return request("/admin/evaluations/moderation-targets", { headers: authHeaders(token) });
}

export type AuditCatalogOption = { value: string; label: string };

export type AdminAuditEvent = {
  id: string;
  actor_user_id: string;
  actor_nickname: string | null;
  actor_email_normalized: string | null;
  actor_role: string;
  action_type: string;
  subject_type: string;
  subject_id: string;
  previous: Record<string, unknown> | null;
  current: Record<string, unknown> | null;
  created_at: string;
};

export type AdminAuditListParams = {
  actor_user_id?: string;
  action_type?: string;
  subject_type?: string;
  subject_id?: string;
  created_from?: string;
  created_to?: string;
  page?: number;
  page_size?: number;
};

function auditQuery(params: AdminAuditListParams): string {
  const search = new URLSearchParams();
  if (params.actor_user_id) search.set("actor_user_id", params.actor_user_id);
  if (params.action_type) search.set("action_type", params.action_type);
  if (params.subject_type) search.set("subject_type", params.subject_type);
  if (params.subject_id) search.set("subject_id", params.subject_id);
  if (params.created_from) search.set("created_from", params.created_from);
  if (params.created_to) search.set("created_to", params.created_to);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  const q = search.toString();
  return q ? `?${q}` : "";
}

export async function fetchAuditCatalog(token: string): Promise<{
  action_types: AuditCatalogOption[];
  subject_types: AuditCatalogOption[];
}> {
  return request("/admin/audit-events/catalog", { headers: authHeaders(token) });
}

export async function listAdminAuditEvents(
  token: string,
  params: AdminAuditListParams = {},
): Promise<{ items: AdminAuditEvent[]; total: number; page: number; page_size: number }> {
  return request(`/admin/audit-events${auditQuery(params)}`, { headers: authHeaders(token) });
}

export async function getAdminAuditEvent(token: string, eventId: string): Promise<AdminAuditEvent> {
  return request(`/admin/audit-events/${eventId}`, { headers: authHeaders(token) });
}
