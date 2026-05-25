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
