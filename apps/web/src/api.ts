const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type SignupPayload = {
  email: string;
  password: string;
  role: "author" | "reviewer";
};

export type ScenarioResponse = {
  id: string;
  slug: string;
  title: string;
  body_markdown: string;
  author_user_id: string;
  state: "draft" | "in_review" | "approved" | "published";
  current_revision_number: number;
  created_at: string;
  updated_at: string;
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
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
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

export async function me(token: string): Promise<{ user_id: string; email: string; role: string }> {
  return request("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function createScenario(
  token: string,
  payload: { slug: string; title: string; body_markdown: string },
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

export async function reviewQueue(token: string): Promise<{
  items: Array<{ scenario_id: string; slug: string; title: string; state: string }>;
}> {
  return request("/workflow/review-queue", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function approveScenario(token: string, id: string): Promise<{ state: string }> {
  return request(`/workflow/scenarios/${id}/approve`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function publishScenario(token: string, id: string): Promise<{ state: string }> {
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
}> {
  return request(`/public/scenarios/${slug}`);
}

export type ScenarioSummary = {
  id: string;
  slug: string;
  title: string;
  state: string;
  updated_at: string;
};

export async function listMyScenarios(token: string): Promise<ScenarioSummary[]> {
  return request("/scenarios/mine", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export type PublicComment = {
  id: string;
  author_user_id: string;
  body_markdown: string;
  revision_number: number | null;
  section_key: string | null;
  field_path: string | null;
  created_at: string;
  updated_at: string;
};

export async function listPublicComments(slug: string): Promise<{ scenario_id: string; slug: string; items: PublicComment[] }> {
  return request(`/public/scenarios/${slug}/comments`);
}

export async function postPublicComment(
  token: string,
  slug: string,
  payload: { body_markdown: string; revision_number?: number | null },
): Promise<PublicComment> {
  return request(`/public/scenarios/${slug}/comments`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}
