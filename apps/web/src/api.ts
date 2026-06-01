const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type FastApiValidationItem = {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
};

function formatFastApiDetail(detail: unknown): string {
  if (detail === null || detail === undefined) {
    return "Request failed";
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "object" && item !== null && "msg" in item) {
          const row = item as FastApiValidationItem;
          const path =
            Array.isArray(row.loc) && row.loc.length > 0
              ? row.loc
                  .map(String)
                  .filter((segment) => segment !== "body" && segment !== "query" && segment !== "path")
                  .join(".")
              : "";
          const msg = row.msg ?? "invalid";
          return path ? `${path}: ${msg}` : msg;
        }
        return typeof item === "string" ? item : JSON.stringify(item);
      })
      .join("; ");
  }
  if (typeof detail === "object" && detail !== null && "message" in detail) {
    const row = detail as {
      message?: unknown;
      code?: unknown;
      similar_titles?: unknown;
      candidates?: Array<{ title?: string }>;
    };
    let msg = typeof row.message === "string" ? row.message : "Request failed";
    if (row.code === "sensitive_data_detected" && typeof row.message === "string") {
      return row.message;
    }
    const titles =
      Array.isArray(row.similar_titles) && row.similar_titles.length
        ? row.similar_titles.filter((t): t is string => typeof t === "string")
        : Array.isArray(row.candidates)
          ? row.candidates
              .map((c) => c.title)
              .filter((t): t is string => typeof t === "string")
          : [];
    if (titles.length) {
      msg += `\n\nSimilar published scenario(s):\n${titles.map((t) => `• ${t}`).join("\n")}`;
    }
    return msg;
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return "Request failed";
  }
}

export type SensitiveFindingLocation = {
  finding_type: string;
  field: string;
  field_label: string;
  label: string;
  excerpt: string;
};

export type SimilarScenarioMatch = {
  scenario_id: string;
  title: string;
  score: number;
  public_path: string | null;
};

export type ContentPolicyDetail = {
  code: string;
  message: string;
  findings?: SensitiveFindingLocation[];
  candidates?: SimilarScenarioMatch[];
};

export class ContentPolicyError extends Error {
  readonly code: string;
  readonly findings?: SensitiveFindingLocation[];
  readonly similarCandidates?: SimilarScenarioMatch[];

  constructor(detail: ContentPolicyDetail) {
    super(detail.message);
    this.name = "ContentPolicyError";
    this.code = detail.code;
    this.findings = detail.findings;
    this.similarCandidates = detail.candidates;
  }
}

function parseContentPolicyDetail(detail: unknown): ContentPolicyDetail | null {
  if (typeof detail !== "object" || detail === null || !("code" in detail) || !("message" in detail)) {
    return null;
  }
  const row = detail as ContentPolicyDetail;
  if (typeof row.code !== "string" || typeof row.message !== "string") {
    return null;
  }
  if (row.code !== "sensitive_data_detected" && row.code !== "similar_scenarios_detected") {
    return null;
  }
  return row;
}

/** Readable message from a failed fetch (FastAPI JSON or plain text). */
export async function getFetchErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  const status = response.status;
  if (!text.trim()) {
    return `Request failed (${status})`;
  }
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (parsed.detail !== undefined) {
      const policy = parseContentPolicyDetail(parsed.detail);
      if (policy) {
        return policy.message;
      }
      return formatFastApiDetail(parsed.detail);
    }
  } catch {
    // not JSON
  }
  return text.length > 800 ? `${text.slice(0, 800)}…` : text;
}

export async function readApiError(response: Response): Promise<Error> {
  const text = await response.text();
  const status = response.status;
  if (!text.trim()) {
    return new Error(`Request failed (${status})`);
  }
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (parsed.detail !== undefined) {
      const policy = parseContentPolicyDetail(parsed.detail);
      if (policy) {
        return new ContentPolicyError(policy);
      }
      return new Error(formatFastApiDetail(parsed.detail));
    }
  } catch {
    // not JSON
  }
  return new Error(text.length > 800 ? `${text.slice(0, 800)}…` : text);
}

export type SignupPayload = {
  email: string;
  password: string;
  nickname: string;
};

export type ScenarioResponse = {
  id: string;
  title: string;
  description: string;
  category_ids: string[];
  ethical_risk_ids: string[];
  author_user_id: string;
  state:
    | "draft"
    | "queued"
    | "in_review"
    | "changes_required"
    | "applying_changes"
    | "published"
    | "not_suitable";
  review_feedback_note?: string | null;
  review_feedback_at?: string | null;
  not_suitable_reason?: string | null;
  current_revision_number: number;
  created_at: string;
  updated_at: string;
  live_public_title?: string | null;
  live_public_description?: string | null;
  can_create_suggestion?: boolean;
  my_participation_role?: "owner" | "collaborator" | null;
  cover_image?: ScenarioAsset | null;
  inline_assets?: ScenarioAsset[];
};

export type ScenarioAsset = {
  asset_id: string;
  storage_key: string;
  url?: string | null;
  alt_text?: string | null;
  width?: number | null;
  height?: number | null;
  mime_type: string;
  order: number;
};

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const raw = await response.text();
  if (!raw.trim()) {
    return undefined as T;
  }
  return JSON.parse(raw) as T;
}

export async function signup(payload: SignupPayload): Promise<{ user_id: string }> {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyEmail(token: string): Promise<{ verified: boolean }> {
  return request("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export async function login(
  email: string,
  password: string,
): Promise<{ access_token: string; must_change_password: boolean }> {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export type MeProfile = {
  user_id: string;
  email_normalized: string;
  role: string;
  account_status: string;
  email_verified_at: string | null;
  must_change_password: boolean;
  nickname: string;
  first_name: string | null;
  last_name: string | null;
  organization: string | null;
  biography: string | null;
  avatar: {
    bucket: string;
    object_key: string;
    version_id: string | null;
    content_type: string;
    size_bytes: number;
    updated_at: string;
  } | null;
  avatar_url: string | null;
  last_login_at: string | null;
};

export async function me(token: string): Promise<MeProfile> {
  return request("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export type ProfilePatchPayload = {
  nickname?: string;
  first_name?: string | null;
  last_name?: string | null;
  organization?: string | null;
  biography?: string | null;
};

export async function patchMyProfile(token: string, payload: ProfilePatchPayload): Promise<MeProfile> {
  return request("/auth/me", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function uploadMyAvatar(token: string, file: File): Promise<MeProfile> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_URL}/auth/me/avatar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
  const raw = await response.text();
  return JSON.parse(raw) as MeProfile;
}

export async function deleteMyAvatar(token: string): Promise<MeProfile> {
  return request("/auth/me/avatar", {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function changeMyPassword(
  token: string,
  payload: { current_password: string; new_password: string },
): Promise<void> {
  const response = await fetch(`${API_URL}/auth/me/change-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
}

export async function createScenario(
  token: string,
  payload: { title: string; description: string },
): Promise<ScenarioResponse> {
  return request("/scenarios", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function getScenario(token: string, id: string): Promise<ScenarioResponse> {
  return request(`/scenarios/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function patchScenario(
  token: string,
  id: string,
  payload: {
    title?: string;
    description?: string;
    category_ids?: string[];
    ethical_risk_ids?: string[];
  },
): Promise<ScenarioResponse> {
  return request(`/scenarios/${id}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function submitReview(token: string, id: string): Promise<{ state: string }> {
  return request(`/scenarios/${id}/submit-review`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export type SimilarityCandidate = {
  scenario_id: string;
  title: string;
  score: number;
};

export async function checkScenarioSimilarity(
  token: string,
  payload: { title: string; description: string; exclude_scenario_id?: string },
): Promise<{ provider: string; candidates: SimilarityCandidate[] }> {
  return request("/scenarios/similarity-check", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function deleteScenario(token: string, id: string): Promise<void> {
  const response = await fetch(`${API_URL}/scenarios/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
}

export type WorkflowActionResponse = {
  scenario_id: string;
  state: string;
  changed_at: string;
};

export async function reviewQueue(token: string): Promise<{
  items: Array<{
    scenario_id: string;
    title: string;
    author_user_id: string;
    state: string;
    has_prior_approval: boolean;
    submitted_at?: string | null;
    live_public_title?: string | null;
    live_public_description?: string | null;
    live_public_path?: string | null;
  }>;
}> {
  return request("/workflow/review-queue", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function startReviewScenario(token: string, id: string): Promise<WorkflowActionResponse> {
  return request(`/workflow/scenarios/${id}/start-review`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function requestChangesScenario(
  token: string,
  id: string,
  note: string,
): Promise<WorkflowActionResponse> {
  return request(`/workflow/scenarios/${id}/request-changes`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
}

export async function markNotSuitableScenario(
  token: string,
  id: string,
  reason?: string,
): Promise<WorkflowActionResponse> {
  return request(`/workflow/scenarios/${id}/mark-not-suitable`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export async function reopenScenario(token: string, id: string): Promise<WorkflowActionResponse> {
  return request(`/workflow/scenarios/${id}/reopen`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function publishScenario(token: string, id: string): Promise<WorkflowActionResponse> {
  return request(`/workflow/scenarios/${id}/publish`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function reviewedScenarios(token: string): Promise<{
  items: Array<{
    scenario_id: string;
    title: string;
    author_user_id: string;
    state: string;
    last_reviewed_at: string;
    last_review_outcome?: string | null;
    live_public_path?: string | null;
  }>;
}> {
  return request("/workflow/reviewed", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function startApplyingChanges(token: string, id: string): Promise<{ scenario_id: string; state: string }> {
  return request(`/scenarios/${id}/start-applying-changes`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export type PublicScenarioListItem = {
  id: string;
  title: string;
  published_at: string;
  public_path: string;
  author_user_id: string;
  author_nickname: string;
};

export type PublicScenarioSearchResult = {
  items: PublicScenarioListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type SearchPublicScenariosParams = {
  q?: string;
  author_user_id?: string;
  published_from?: string;
  published_to?: string;
  category_id?: string[];
  ethical_risk_id?: string[];
  page?: number;
  page_size?: number;
};

export type PublicCatalogEntry = { id: string; label: string };

export async function fetchPublicSearchCategories(): Promise<{ items: PublicCatalogEntry[] }> {
  return request("/public/catalog/categories");
}

export async function fetchPublicSearchEthicalRisks(): Promise<{ items: PublicCatalogEntry[] }> {
  return request("/public/catalog/ethical-risks");
}

export async function searchPublicScenarios(
  params: SearchPublicScenariosParams = {},
): Promise<PublicScenarioSearchResult> {
  const search = new URLSearchParams();
  if (params.q?.trim()) {
    search.set("q", params.q.trim());
  }
  if (params.author_user_id) {
    search.set("author_user_id", params.author_user_id);
  }
  if (params.published_from) {
    search.set("published_from", params.published_from);
  }
  if (params.published_to) {
    search.set("published_to", params.published_to);
  }
  for (const id of params.category_id ?? []) {
    search.append("category_id", id);
  }
  for (const id of params.ethical_risk_id ?? []) {
    search.append("ethical_risk_id", id);
  }
  if (params.page != null) {
    search.set("page", String(params.page));
  }
  if (params.page_size != null) {
    search.set("page_size", String(params.page_size));
  }
  const qs = search.toString();
  return request(`/public/scenarios${qs ? `?${qs}` : ""}`);
}

export async function listPublicScenarios(): Promise<PublicScenarioListItem[]> {
  const result = await searchPublicScenarios({ page_size: 100 });
  return result.items;
}

export type PublicScenarioParticipant = {
  user_id: string;
  nickname: string;
};

export async function publicScenario(slug: string): Promise<{
  id: string;
  author_user_id: string;
  author_nickname: string;
  title: string;
  description: string;
  published_at: string;
  cover_image?: ScenarioAssetWithUrl | null;
  inline_assets?: ScenarioAssetWithUrl[];
  collaborators: PublicScenarioParticipant[];
  summary?: string | null;
  categories?: Array<{ id: string; label: string }>;
  ethical_risks?: Array<{ id: string; label: string }>;
}> {
  return request(`/public/scenarios/${slug}`);
}

export type ScenarioAssetWithUrl = {
  asset_id: string;
  alt_text?: string | null;
  mime_type: string;
  order: number;
  signed_url: string;
};

export type ScenarioSummary = {
  id: string;
  title: string;
  state: string;
  updated_at: string;
  first_published_at?: string | null;
  public_path?: string | null;
  my_participation_role: "owner" | "collaborator";
};

export async function listMyScenarios(token: string): Promise<ScenarioSummary[]> {
  return request("/scenarios/mine", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function uploadScenarioCover(
  token: string,
  scenarioId: string,
  file: File,
  altText?: string,
): Promise<ScenarioResponse> {
  const form = new FormData();
  form.append("file", file);
  if (altText && altText.trim()) form.append("alt_text", altText.trim());
  const response = await fetch(`${API_URL}/scenarios/${scenarioId}/assets/cover`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
  return (await response.json()) as ScenarioResponse;
}

export async function uploadScenarioInline(
  token: string,
  scenarioId: string,
  file: File,
  order = 0,
  altText?: string,
): Promise<ScenarioResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("order", String(order));
  if (altText && altText.trim()) form.append("alt_text", altText.trim());
  const response = await fetch(`${API_URL}/scenarios/${scenarioId}/assets/inline`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
  return (await response.json()) as ScenarioResponse;
}

export async function deleteScenarioInlineAsset(token: string, scenarioId: string, assetId: string): Promise<ScenarioResponse> {
  return request(`/scenarios/${scenarioId}/assets/inline/${assetId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function deleteScenarioCoverAsset(token: string, scenarioId: string): Promise<ScenarioResponse> {
  return request(`/scenarios/${scenarioId}/assets/cover`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function reorderScenarioInlineAssets(
  token: string,
  scenarioId: string,
  assetIds: string[],
): Promise<ScenarioResponse> {
  return request(`/scenarios/${scenarioId}/assets/inline/reorder`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ asset_ids: assetIds }),
  });
}

export async function getScenarioAssetReadUrl(
  token: string,
  scenarioId: string,
  assetId: string,
): Promise<{ asset_id: string; signed_url: string; expires_in_seconds: number }> {
  return request(`/scenarios/${scenarioId}/assets/${assetId}/read-url`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export type SuggestionItem = {
  id: string;
  scenario_id: string;
  author_user_id: string;
  author_role: string;
  scope: "scenario" | "paragraph";
  kind: "comment" | "alternative_text";
  paragraph_index: number | null;
  body: string;
  status: "pending" | "accepted" | "rejected";
  scenario_state_at_creation: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  resolved_by_user_id?: string | null;
  applied_at?: string | null;
};

export async function getScenarioReviewFeedbackStatus(
  token: string,
  scenarioId: string,
): Promise<{ has_submitted_feedback: boolean }> {
  return request(`/scenarios/${scenarioId}/suggestions/review-feedback`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function listScenarioSuggestions(token: string, scenarioId: string): Promise<{ items: SuggestionItem[] }> {
  return request(`/scenarios/${scenarioId}/suggestions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function listScenarioParagraphs(token: string, scenarioId: string): Promise<{ paragraphs: string[] }> {
  return request(`/scenarios/${scenarioId}/suggestions/paragraphs`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function createScenarioSuggestion(
  token: string,
  scenarioId: string,
  payload: {
    scope: "scenario" | "paragraph";
    kind: "comment" | "alternative_text";
    paragraph_index?: number | null;
    body: string;
  },
): Promise<SuggestionItem> {
  return request(`/scenarios/${scenarioId}/suggestions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function acceptScenarioSuggestion(
  token: string,
  scenarioId: string,
  suggestionId: string,
): Promise<{ suggestion: SuggestionItem; scenario: ScenarioResponse }> {
  return request(`/scenarios/${scenarioId}/suggestions/${suggestionId}/accept`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function rejectScenarioSuggestion(
  token: string,
  scenarioId: string,
  suggestionId: string,
): Promise<SuggestionItem> {
  return request(`/scenarios/${scenarioId}/suggestions/${suggestionId}/reject`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function applyAcceptedSuggestionText(
  token: string,
  scenarioId: string,
  suggestionId: string,
): Promise<{ suggestion: SuggestionItem; scenario: ScenarioResponse }> {
  return request(`/scenarios/${scenarioId}/suggestions/${suggestionId}/apply-text`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export type EvaluationAspects = {
  children_age: "0-4" | "5-9" | "10-14" | "15_or_more" | "";
  duration_frequency:
    | "daily"
    | "once_a_week"
    | "several_times_a_day"
    | "several_times_a_week"
    | "once_a_month"
    | "";
  execution_place: "yes" | "no" | "";
  special_circumstances: "yes" | "no" | "";
  consent: "yes" | "no" | "";
};

export type EvaluationItem = {
  id: string;
  scenario_id: string;
  evaluator_user_id: string;
  evaluator_nickname?: string | null;
  risk_score: number;
  benefit_score: number;
  detected_ethical_risk_ids: string[];
  detected_ethical_risk_labels: string[];
  comment: string;
  aspects: EvaluationAspects;
  visibility: string;
  submitted_at: string;
};

export async function getMyScenarioEvaluation(
  token: string,
  scenarioId: string,
): Promise<{ evaluation: EvaluationItem | null; can_submit: boolean }> {
  return request(`/scenarios/${scenarioId}/evaluations/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function submitScenarioEvaluation(
  token: string,
  scenarioId: string,
  payload: {
    risk_score: number;
    benefit_score: number;
    detected_ethical_risk_ids: string[];
    comment: string;
    aspects: {
      children_age: Exclude<EvaluationAspects["children_age"], "">;
      duration_frequency: Exclude<EvaluationAspects["duration_frequency"], "">;
      execution_place: Exclude<EvaluationAspects["execution_place"], "">;
      special_circumstances: Exclude<EvaluationAspects["special_circumstances"], "">;
      consent: Exclude<EvaluationAspects["consent"], "">;
    };
  },
): Promise<EvaluationItem> {
  return request(`/scenarios/${scenarioId}/evaluations`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export type EvaluationSummary = {
  scenario_id: string;
  evaluation_count: number;
  average_risk_score: number | null;
  average_benefit_score: number | null;
  detected_ethical_risk_labels: string[];
  comments?: string[];
};

export async function getScenarioEvaluationSummary(
  token: string,
  scenarioId: string,
): Promise<EvaluationSummary> {
  return request(`/scenarios/${scenarioId}/evaluations/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function listScenarioEvaluations(
  token: string,
  scenarioId: string,
): Promise<{ items: EvaluationItem[] }> {
  return request(`/scenarios/${scenarioId}/evaluations`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchActiveEthicalRisks(token: string): Promise<{ items: Array<{ id: string; label: string }> }> {
  return request("/catalog/ethical-risks", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function moderateScenarioEvaluation(
  token: string,
  evaluationId: string,
  action: "hide" | "delete",
): Promise<void> {
  const response = await fetch(`${API_URL}/scenarios/evaluations/${evaluationId}/moderate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action }),
  });
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
  }
}

export type NotificationItem = {
  id: string;
  notification_type: string;
  title: string;
  message: string | null;
  entity_type: string;
  entity_id: string;
  scenario_id: string | null;
  actor_user_id: string | null;
  link_path: string | null;
  payload: Record<string, unknown> | null;
  read_at: string | null;
  created_at: string;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
  unread_count: number;
};

export async function listNotifications(
  token: string,
  params: { unread_only?: boolean; page?: number; page_size?: number } = {},
): Promise<NotificationListResponse> {
  const search = new URLSearchParams();
  if (params.unread_only) search.set("unread_only", "true");
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  const q = search.toString();
  return request(`/notifications${q ? `?${q}` : ""}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getNotificationUnreadCount(token: string): Promise<{ unread_count: number }> {
  return request("/notifications/unread-count", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function markNotificationRead(token: string, notificationId: string): Promise<NotificationItem> {
  return request(`/notifications/${notificationId}/read`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function markAllNotificationsRead(token: string): Promise<{ unread_count: number }> {
  return request("/notifications/read-all", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}
