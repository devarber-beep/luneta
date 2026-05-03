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
  if (typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return "Request failed";
  }
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
      return formatFastApiDetail(parsed.detail);
    }
  } catch {
    // not JSON
  }
  return text.length > 800 ? `${text.slice(0, 800)}…` : text;
}

export type SignupPayload = {
  email: string;
  password: string;
  role: "investigator" | "coordinator";
  nickname: string;
};

export type ScenarioResponse = {
  id: string;
  slug: string;
  title: string;
  body_markdown: string;
  author_user_id: string;
  state: "draft" | "in_review" | "published";
  current_revision_number: number;
  created_at: string;
  updated_at: string;
  live_public_slug?: string | null;
  live_public_title?: string | null;
  live_public_body_markdown?: string | null;
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(await getFetchErrorMessage(response));
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

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export type MeProfile = {
  user_id: string;
  email: string;
  role: string;
  is_email_verified: boolean;
  email_verified_at: string | null;
  nickname: string;
  first_name: string | null;
  last_name: string | null;
  avatar: {
    bucket: string;
    object_key: string;
    version_id: string | null;
    content_type: string;
    size_bytes: number;
    updated_at: string;
  } | null;
  last_login_at: string | null;
};

export async function me(token: string): Promise<MeProfile> {
  return request("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function patchMyProfile(
  token: string,
  payload: { nickname: string; first_name?: string | null; last_name?: string | null },
): Promise<MeProfile> {
  return request("/auth/me", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
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
  payload: { title: string; body_markdown: string },
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
  payload: { title?: string; body_markdown?: string },
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
    slug: string;
    title: string;
    author_user_id: string;
    state: string;
    has_prior_approval: boolean;
    submitted_at?: string | null;
    live_public_slug?: string | null;
    live_public_title?: string | null;
    live_public_body_markdown?: string | null;
  }>;
}> {
  return request("/workflow/review-queue", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function rejectScenario(token: string, id: string): Promise<WorkflowActionResponse> {
  return request(`/workflow/scenarios/${id}/reject`, {
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

export type PublicScenarioListItem = {
  id: string;
  slug: string;
  title: string;
  published_at: string;
};

export async function listPublicScenarios(): Promise<PublicScenarioListItem[]> {
  return request("/public/scenarios");
}

export async function publicScenario(slug: string): Promise<{
  id: string;
  slug: string;
  title: string;
  body_markdown: string;
  published_at: string;
  cover_image?: ScenarioAssetWithUrl | null;
  inline_assets?: ScenarioAssetWithUrl[];
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
  slug: string;
  title: string;
  state: string;
  updated_at: string;
  first_published_at?: string | null;
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

