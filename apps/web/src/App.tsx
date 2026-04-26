import { type CSSProperties, type FormEvent, type ReactElement, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  approveScenario,
  changeMyPassword,
  createScenario,
  deleteScenarioCoverAsset,
  deleteScenarioInlineAsset,
  getScenario,
  getScenarioAssetReadUrl,
  listMyScenarios,
  listPublicScenarios,
  login,
  me,
  patchMyProfile,
  patchScenario,
  publicScenario,
  publishScenario,
  reviewQueue,
  reorderScenarioInlineAssets,
  signup,
  submitReview,
  uploadScenarioCover,
  uploadScenarioInline,
  verifyEmail,
} from "./api";
import { clearSession, getRole, getToken, setRole, setToken } from "./session";

const layoutStyle: CSSProperties = {
  maxWidth: "860px",
  margin: "0 auto",
  padding: "2rem",
  fontFamily: "system-ui, sans-serif",
};

function HomePage() {
  const token = getToken();
  const [published, setPublished] = useState<Array<{ id: string; slug: string; title: string; published_at: string }>>([]);
  const [catalogError, setCatalogError] = useState("");

  useEffect(() => {
    listPublicScenarios()
      .then(setPublished)
      .catch((e: Error) => setCatalogError(e.message));
  }, []);

  return (
    <main style={layoutStyle}>
      <h1>Luneta</h1>
      <p>
        Workflow: draft, save, submit for review (not editable while in review), approve and publish. Edits on a
        published scenario remain draft changes until the next review; the public page keeps showing the last approved
        version until then.
      </p>
      <nav style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginTop: "1rem" }}>
        <Link to="/signup">Signup</Link>
        <Link to="/verify-email">Verify email</Link>
        <Link to="/login">Login</Link>
        <Link to="/my-scenarios">My scenarios</Link>
        {getToken() ? <Link to="/my-profile">My profile</Link> : null}
        <Link to="/scenarios/new">New draft</Link>
        {getRole() === "reviewer" ? <Link to="/review">Review queue</Link> : null}
      </nav>
      {token ? <p style={{ marginTop: "1rem" }}>Active session.</p> : <p style={{ marginTop: "1rem" }}>No session.</p>}
      <section style={{ marginTop: "2rem" }}>
        <h2>Published</h2>
        {catalogError ? <p style={{ color: "crimson" }}>{catalogError}</p> : null}
        {!published.length && !catalogError ? <p>No published scenarios yet.</p> : null}
        <ul style={{ paddingLeft: "1.25rem" }}>
          {published.map((s) => (
            <li key={s.id}>
              <Link to={`/public/${s.slug}`}>{s.title}</Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

function SignupPage() {
  const [email, setEmail] = useState("author@luneta.dev");
  const [password, setPassword] = useState("Password123!");
  const [nickname, setNickname] = useState("");
  const [role, setCurrentRole] = useState<"author" | "reviewer">("author");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const nick = nickname.trim();
    if (nick.length < 2) {
      setMessage("Nickname must be at least 2 characters.");
      return;
    }
    try {
      const response = await signup({
        email,
        password,
        role,
        nickname: nick,
      });
      setMessage(`User created: ${response.user_id}. Check logs for the verification token.`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Signup</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" />
        <input value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="nickname" />
        <select value={role} onChange={(e) => setCurrentRole(e.target.value as "author" | "reviewer")}>
          <option value="author">author</option>
          <option value="reviewer">reviewer</option>
        </select>
        <button type="submit">Create user</button>
      </form>
      <p>{message}</p>
      <Link to="/">Back</Link>
    </main>
  );
}

function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [tokenValue, setTokenValue] = useState(() => searchParams.get("token") ?? "");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const response = await verifyEmail(tokenValue);
      setMessage(response.verified ? "Email verified." : "Not verified.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Verify Email</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
        <input value={tokenValue} onChange={(e) => setTokenValue(e.target.value)} placeholder="verification token" />
        <button type="submit">Verify</button>
      </form>
      <p>{message}</p>
      <Link to="/">Back</Link>
    </main>
  );
}

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("author@luneta.dev");
  const [password, setPassword] = useState("Password123!");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const auth = await login(email, password);
      setToken(auth.access_token);
      const profile = await me(auth.access_token);
      setRole(profile.role);
      setMessage(`Signed in as ${profile.role}`);
      if (profile.role === "reviewer") {
        navigate("/review");
      } else {
        navigate("/my-scenarios");
      }
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Login</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" />
        <button type="submit">Sign in</button>
      </form>
      <p>{message}</p>
      <Link to="/">Back</Link>
    </main>
  );
}

function RequireAuth({ children }: { children: ReactElement }) {
  const token = getToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function MyProfilePage() {
  const [nickname, setNickname] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [readOnlyEmail, setReadOnlyEmail] = useState("");
  const [readOnlyRole, setReadOnlyRole] = useState("");
  const [verified, setVerified] = useState(false);
  const [verifiedAt, setVerifiedAt] = useState<string | null>(null);
  const [lastLoginAt, setLastLoginAt] = useState<string | null>(null);
  const [avatarInfo, setAvatarInfo] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token) return;
    const profile = await me(token);
    setNickname(profile.nickname);
    setFirstName(profile.first_name ?? "");
    setLastName(profile.last_name ?? "");
    setReadOnlyEmail(profile.email);
    setReadOnlyRole(profile.role);
    setVerified(profile.is_email_verified);
    setVerifiedAt(profile.email_verified_at);
    setLastLoginAt(profile.last_login_at);
    setAvatarInfo(
      profile.avatar
        ? `${profile.avatar.bucket} / ${profile.avatar.object_key} (${profile.avatar.content_type})`
        : null,
    );
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, []);

  const onSaveProfile = async (event: FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    const nick = nickname.trim();
    if (nick.length < 2) {
      setMessage("Nickname must be at least 2 characters.");
      return;
    }
    try {
      await patchMyProfile(token, {
        nickname: nick,
        first_name: firstName.trim() || null,
        last_name: lastName.trim() || null,
      });
      setMessage("Profile saved.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onChangePassword = async (event: FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    if (newPassword.length < 8) {
      setMessage("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessage("New password and confirmation do not match.");
      return;
    }
    try {
      await changeMyPassword(token, { current_password: currentPassword, new_password: newPassword });
      setMessage("Password updated.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>My profile</h2>
      <p>Update your display name and password. Email cannot be changed here.</p>

      <section style={{ marginBottom: "1.5rem", padding: "0.75rem", background: "#f8f8f8", borderRadius: "6px" }}>
        <h3 style={{ marginTop: 0 }}>Account</h3>
        <p style={{ margin: "0.25rem 0" }}>
          <strong>Email:</strong> {readOnlyEmail || "—"}
        </p>
        <p style={{ margin: "0.25rem 0" }}>
          <strong>Role:</strong> {readOnlyRole || "—"}
        </p>
        <p style={{ margin: "0.25rem 0" }}>
          <strong>Email verified:</strong> {verified ? "Yes" : "No"}
          {verifiedAt ? ` (${new Date(verifiedAt).toLocaleString()})` : ""}
        </p>
        <p style={{ margin: "0.25rem 0" }}>
          <strong>Last login:</strong>{" "}
          {lastLoginAt ? new Date(lastLoginAt).toLocaleString() : "—"}
        </p>
        <p style={{ margin: "0.25rem 0" }}>
          <strong>Avatar (storage):</strong> {avatarInfo ?? "None"}
        </p>
        <p style={{ margin: "0.75rem 0 0", fontSize: "0.9rem", color: "#555" }}>
          Profile image upload is not wired in this UI yet; only metadata from the API is shown.
        </p>
      </section>

      <form onSubmit={onSaveProfile} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px", marginBottom: "2rem" }}>
        <h3 style={{ margin: 0 }}>Profile details</h3>
        <label style={{ display: "grid", gap: "0.25rem" }}>
          <span>Nickname</span>
          <input value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="nickname" required minLength={2} />
        </label>
        <label style={{ display: "grid", gap: "0.25rem" }}>
          <span>First name</span>
          <input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="optional" />
        </label>
        <label style={{ display: "grid", gap: "0.25rem" }}>
          <span>Last name</span>
          <input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="optional" />
        </label>
        <button type="submit">Save profile</button>
      </form>

      <form onSubmit={onChangePassword} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
        <h3 style={{ margin: 0 }}>Change password</h3>
        <label style={{ display: "grid", gap: "0.25rem" }}>
          <span>Current password</span>
          <input
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <label style={{ display: "grid", gap: "0.25rem" }}>
          <span>New password</span>
          <input
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
          />
        </label>
        <label style={{ display: "grid", gap: "0.25rem" }}>
          <span>Confirm new password</span>
          <input
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
          />
        </label>
        <button type="submit">Update password</button>
      </form>

      {message ? (
        <p
          style={{
            marginTop: "1rem",
            color: message === "Profile saved." || message === "Password updated." ? "#0a0" : "crimson",
          }}
        >
          {message}
        </p>
      ) : null}
      <p style={{ marginTop: "1.5rem" }}>
        <Link to="/">Back</Link>
      </p>
    </main>
  );
}

function MyScenariosPage() {
  const [items, setItems] = useState<
    Array<{ id: string; slug: string; title: string; state: string; first_published_at?: string | null }>
  >([]);
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token) {
      return;
    }
    try {
      const rows = await listMyScenarios(token);
      setItems(rows);
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, []);

  return (
    <main style={layoutStyle}>
      <h2>My scenarios</h2>
      <p>Author or collaborator (owner/editor). Draft and published scenarios are opened by id.</p>
      <p>
        <Link to="/my-profile">My profile</Link>
      </p>
      <button type="button" onClick={() => load().catch((e: Error) => setMessage(e.message))}>
        Refresh
      </button>
      <ul style={{ marginTop: "1rem", paddingLeft: "1.25rem" }}>
        {items.map((s) => (
          <li key={s.id} style={{ marginBottom: "0.5rem" }}>
            <strong>{s.title}</strong> — {s.state}{" "}
            <Link to={`/scenarios/${s.id}/edit`}>Edit / workflow</Link>
            {(s.state === "published" || s.state === "in_review") && s.first_published_at ? (
              <>
                {" "}
                <Link to={`/public/${s.slug}`}>View public</Link>
              </>
            ) : null}
          </li>
        ))}
      </ul>
      {!items.length && <p>No scenarios are associated with your account.</p>}
      {message ? <p style={{ color: "crimson" }}>{message}</p> : null}
      <Link to="/">Back</Link>
    </main>
  );
}

function NewScenarioPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token) {
      return;
    }
    const trimmedTitle = title.trim();
    if (trimmedTitle.length < 3) {
      setMessage("Title must have at least 3 characters.");
      return;
    }
    if (!body.trim()) {
      setMessage("Body cannot be empty.");
      return;
    }
    try {
      const scenario = await createScenario(token, { title: trimmedTitle, body_markdown: body });
      setMessage(`Draft created: ${scenario.id}`);
      navigate(`/scenarios/${scenario.id}/edit`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>New Draft</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem" }}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="title" />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={8} />
        <button type="submit">Create draft</button>
      </form>
      <p>{message}</p>
      <Link to="/">Back</Link>
    </main>
  );
}

function EditScenarioPage() {
  const params = useParams();
  const scenarioId = params.id ?? "";
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [state, setState] = useState("");
  const [livePublicTitle, setLivePublicTitle] = useState<string | null>(null);
  const [livePublicBody, setLivePublicBody] = useState<string | null>(null);
  const [coverAsset, setCoverAsset] = useState<{ asset_id: string; alt_text?: string | null } | null>(null);
  const [inlineAssets, setInlineAssets] = useState<Array<{ asset_id: string; order: number; alt_text?: string | null }>>([]);
  const [assetPreviewUrls, setAssetPreviewUrls] = useState<Record<string, string>>({});
  const [assetPreviewCache, setAssetPreviewCache] = useState<Record<string, { url: string; expiresAtMs: number }>>({});
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [inlineFile, setInlineFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    const scenario = await getScenario(token, scenarioId);
    setTitle(scenario.title);
    setBody(scenario.body_markdown);
    setState(scenario.state);
    setLivePublicTitle(scenario.live_public_title ?? null);
    setLivePublicBody(scenario.live_public_body_markdown ?? null);
    setCoverAsset(scenario.cover_image ? { asset_id: scenario.cover_image.asset_id, alt_text: scenario.cover_image.alt_text } : null);
    setInlineAssets(
      (scenario.inline_assets ?? [])
        .slice()
        .sort((a, b) => a.order - b.order)
        .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text })),
    );
    await loadAssetPreviews(
      scenario.cover_image?.asset_id ?? null,
      (scenario.inline_assets ?? []).map((a) => a.asset_id),
    );
  };

  const loadAssetPreviews = async (coverAssetId: string | null, inlineAssetIds: string[]) => {
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    const ids = [...(coverAssetId ? [coverAssetId] : []), ...inlineAssetIds];
    if (!ids.length) {
      setAssetPreviewUrls({});
      return;
    }
    const now = Date.now();
    const nextCache = { ...assetPreviewCache };
    const previewMap: Record<string, string> = {};
    const toFetch: string[] = [];

    for (const assetId of ids) {
      const hit = nextCache[assetId];
      if (hit && hit.expiresAtMs > now + 5000) {
        previewMap[assetId] = hit.url;
      } else {
        toFetch.push(assetId);
      }
    }

    if (toFetch.length) {
      const fetched = await Promise.all(
        toFetch.map(async (assetId) => {
          const res = await getScenarioAssetReadUrl(token, scenarioId, assetId);
          return { assetId, signedUrl: res.signed_url, expiresInSeconds: res.expires_in_seconds };
        }),
      );
      for (const row of fetched) {
        const expiresAtMs = Date.now() + Math.max(1, row.expiresInSeconds - 10) * 1000;
        nextCache[row.assetId] = { url: row.signedUrl, expiresAtMs };
        previewMap[row.assetId] = row.signedUrl;
      }
      setAssetPreviewCache(nextCache);
    }

    setAssetPreviewUrls(previewMap);
  };

  useEffect(() => {
    load().catch((error: Error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId]);

  const onSave = async (event: FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    try {
      const updated = await patchScenario(token, scenarioId, { title, body_markdown: body });
      setState(updated.state);
      setMessage(`Saved. Revision #${updated.current_revision_number}`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onSubmitReview = async () => {
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    try {
      const updated = await submitReview(token, scenarioId);
      setState(updated.state);
      setMessage("Submitted for review.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onUploadCover = async () => {
    const token = getToken();
    if (!token || !scenarioId || !coverFile) return;
    try {
      const updated = await uploadScenarioCover(token, scenarioId, coverFile);
      setCoverAsset(updated.cover_image ? { asset_id: updated.cover_image.asset_id, alt_text: updated.cover_image.alt_text } : null);
      setMessage("Cover image uploaded.");
      setCoverFile(null);
      setAssetPreviewCache({});
      await loadAssetPreviews(updated.cover_image?.asset_id ?? null, (updated.inline_assets ?? []).map((x) => x.asset_id));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onUploadInline = async () => {
    const token = getToken();
    if (!token || !scenarioId || !inlineFile) return;
    try {
      const updated = await uploadScenarioInline(token, scenarioId, inlineFile, inlineAssets.length);
      setInlineAssets(
        (updated.inline_assets ?? [])
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text })),
      );
      setMessage("Inline image uploaded.");
      setInlineFile(null);
      setAssetPreviewCache({});
      await loadAssetPreviews(updated.cover_image?.asset_id ?? null, (updated.inline_assets ?? []).map((x) => x.asset_id));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onDeleteInline = async (assetId: string) => {
    const token = getToken();
    if (!token || !scenarioId) return;
    try {
      const updated = await deleteScenarioInlineAsset(token, scenarioId, assetId);
      setInlineAssets(
        (updated.inline_assets ?? [])
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text })),
      );
      setMessage("Inline image removed.");
      setAssetPreviewCache({});
      await loadAssetPreviews(updated.cover_image?.asset_id ?? null, (updated.inline_assets ?? []).map((x) => x.asset_id));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const moveInline = async (assetId: string, direction: -1 | 1) => {
    const token = getToken();
    if (!token || !scenarioId) return;
    const idx = inlineAssets.findIndex((x) => x.asset_id === assetId);
    const to = idx + direction;
    if (idx < 0 || to < 0 || to >= inlineAssets.length) return;
    const next = inlineAssets.slice();
    const tmp = next[idx];
    next[idx] = next[to];
    next[to] = tmp;
    try {
      const updated = await reorderScenarioInlineAssets(
        token,
        scenarioId,
        next.map((x) => x.asset_id),
      );
      setInlineAssets(
        (updated.inline_assets ?? [])
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text })),
      );
      setMessage("Image order updated.");
      setAssetPreviewCache({});
      await loadAssetPreviews(updated.cover_image?.asset_id ?? null, (updated.inline_assets ?? []).map((x) => x.asset_id));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onDeleteCover = async () => {
    const token = getToken();
    if (!token || !scenarioId) return;
    try {
      const updated = await deleteScenarioCoverAsset(token, scenarioId);
      setCoverAsset(null);
      setMessage("Cover image removed.");
      setAssetPreviewCache({});
      await loadAssetPreviews(null, (updated.inline_assets ?? []).map((x) => x.asset_id));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const locked = state === "in_review" || state === "approved";
  const canSubmitReview = state === "draft" || state === "published";

  return (
    <main style={layoutStyle}>
      <h2>Draft Editor</h2>
      <p>State: {state}</p>
      {state === "published" ? (
        <p style={{ color: "#444", fontSize: "0.95rem" }}>
          You can keep editing this as draft content. The public page keeps showing the latest approved version until
          you submit for review and a reviewer republishes.
        </p>
      ) : null}
      {locked ? (
        <p style={{ color: "#666" }}>In review or approved: content cannot be edited until the next cycle.</p>
      ) : null}
      {livePublicTitle != null && livePublicTitle !== "" ? (
        <section style={{ marginBottom: "1rem", padding: "0.75rem", background: "#f5f5f5", borderRadius: "6px" }}>
          <strong>Current live public version (reference)</strong>
          <p style={{ margin: "0.35rem 0 0" }}>{livePublicTitle}</p>
          {livePublicBody != null ? (
            <pre style={{ whiteSpace: "pre-wrap", marginTop: "0.5rem", fontSize: "0.9rem" }}>{livePublicBody}</pre>
          ) : null}
        </section>
      ) : null}
      <form onSubmit={onSave} style={{ display: "grid", gap: "0.75rem" }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="title"
          disabled={locked}
        />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={12} disabled={locked} />
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={locked}>
            Save draft
          </button>
          {canSubmitReview ? (
            <button type="button" onClick={() => onSubmitReview()} disabled={locked}>
              Submit for review
            </button>
          ) : null}
        </div>
      </form>
      <section style={{ marginTop: "1rem", padding: "0.75rem", border: "1px solid #ddd", borderRadius: "6px" }}>
        <h3>Assets (MinIO)</h3>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          <input type="file" accept="image/*" onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)} disabled={locked} />
          <button type="button" onClick={() => onUploadCover()} disabled={locked || !coverFile}>
            Upload cover image
          </button>
          {coverAsset ? (
            <button type="button" onClick={() => onDeleteCover()} disabled={locked}>
              Remove cover image
            </button>
          ) : null}
        </div>
        {coverAsset && assetPreviewUrls[coverAsset.asset_id] ? (
          <div style={{ marginTop: "0.6rem" }}>
            <img
              src={assetPreviewUrls[coverAsset.asset_id]}
              alt={coverAsset.alt_text ?? "cover"}
              style={{ maxWidth: "240px", maxHeight: "140px", border: "1px solid #ddd", borderRadius: "4px" }}
            />
          </div>
        ) : null}
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap", marginTop: "0.6rem" }}>
          <input type="file" accept="image/*" onChange={(e) => setInlineFile(e.target.files?.[0] ?? null)} disabled={locked} />
          <button type="button" onClick={() => onUploadInline()} disabled={locked || !inlineFile}>
            Upload inline image
          </button>
        </div>
        <ul style={{ paddingLeft: "1.25rem", marginTop: "0.75rem" }}>
          {inlineAssets.map((asset, index) => (
            <li key={asset.asset_id} style={{ marginBottom: "0.35rem" }}>
              #{index + 1} {asset.alt_text ?? "no alt text"}{" "}
              <button type="button" onClick={() => moveInline(asset.asset_id, -1)} disabled={index === 0 || locked}>
                ↑
              </button>{" "}
              <button
                type="button"
                onClick={() => moveInline(asset.asset_id, 1)}
                disabled={index === inlineAssets.length - 1 || locked}
              >
                ↓
              </button>{" "}
              <button type="button" onClick={() => onDeleteInline(asset.asset_id)} disabled={locked}>
                Remove
              </button>
              {assetPreviewUrls[asset.asset_id] ? (
                <div style={{ marginTop: "0.35rem" }}>
                  <img
                    src={assetPreviewUrls[asset.asset_id]}
                    alt={asset.alt_text ?? `inline-${index + 1}`}
                    style={{ maxWidth: "240px", maxHeight: "140px", border: "1px solid #ddd", borderRadius: "4px" }}
                  />
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
      <p>{message}</p>
      <Link to="/">Back</Link>
    </main>
  );
}

function ReviewPage() {
  const [items, setItems] = useState<
    Array<{
      scenario_id: string;
      slug: string;
      title: string;
      state: string;
      has_prior_approval: boolean;
      live_public_slug?: string | null;
      live_public_title?: string | null;
      live_public_body_markdown?: string | null;
    }>
  >([]);
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token) {
      return;
    }
    const queue = await reviewQueue(token);
    setItems(queue.items);
  };

  useEffect(() => {
    load().catch((error: Error) => setMessage(error.message));
  }, []);

  const onApprovePublish = async (scenarioId: string) => {
    const token = getToken();
    if (!token) {
      return;
    }
    try {
      await approveScenario(token, scenarioId);
      await publishScenario(token, scenarioId);
      setMessage("Scenario approved and published.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Review Queue</h2>
      <p>Current role: {getRole() ?? "no role"}</p>
      {items.map((item) => (
        <div key={item.scenario_id} style={{ border: "1px solid #ccc", padding: "0.75rem", marginBottom: "0.75rem" }}>
          <strong>Draft candidate:</strong> {item.title} ({item.state})<br />
          {item.has_prior_approval && item.live_public_title ? (
            <div style={{ marginTop: "0.5rem", padding: "0.5rem", background: "#f9f9f9", borderRadius: "4px" }}>
              <strong>Current live public version:</strong> {item.live_public_title}
              {item.live_public_body_markdown ? (
                <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem", marginTop: "0.35rem" }}>
                  {item.live_public_body_markdown}
                </pre>
              ) : null}
            </div>
          ) : null}
          <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <Link to={`/scenarios/${item.scenario_id}/edit`}>Open scenario (draft)</Link>
            <button onClick={() => onApprovePublish(item.scenario_id)}>Approve + Publish</button>
            {item.has_prior_approval && item.live_public_slug ? (
              <Link to={`/public/${item.live_public_slug}`}>View public (live)</Link>
            ) : null}
          </div>
        </div>
      ))}
      {!items.length && <p>No pending items.</p>}
      <p>{message}</p>
      <Link to="/">Back</Link>
    </main>
  );
}

function PublicScenarioPage() {
  const { slug } = useParams();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [publishedAt, setPublishedAt] = useState("");
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [coverAlt, setCoverAlt] = useState<string>("cover image");
  const [inlineImages, setInlineImages] = useState<Array<{ url: string; alt: string }>>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!slug) {
      return;
    }
    publicScenario(slug)
      .then((data) => {
        setTitle(data.title);
        setBody(data.body_markdown);
        setPublishedAt(data.published_at);
        setCoverUrl(data.cover_image?.signed_url ?? null);
        setCoverAlt(data.cover_image?.alt_text ?? "cover image");
        setInlineImages(
          (data.inline_assets ?? [])
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((x) => ({ url: x.signed_url, alt: x.alt_text ?? "scenario image" })),
        );
      })
      .catch((error: Error) => setMessage(error.message));
  }, [slug]);

  return (
    <main style={layoutStyle}>
      <h2>Public View</h2>
      {publishedAt ? <p style={{ color: "#666" }}>Published: {new Date(publishedAt).toLocaleString()}</p> : null}
      {coverUrl ? (
        <div style={{ margin: "0.75rem 0 1rem" }}>
          <img
            src={coverUrl}
            alt={coverAlt}
            style={{
              width: "100%",
              maxHeight: "300px",
              objectFit: "cover",
              borderRadius: "8px",
              border: "1px solid #ddd",
            }}
          />
        </div>
      ) : null}
      <h3>{title}</h3>
      <pre style={{ whiteSpace: "pre-wrap", marginBottom: inlineImages.length ? "1rem" : 0 }}>{body}</pre>
      {inlineImages.length ? (
        <section style={{ display: "grid", gap: "0.75rem" }}>
          {inlineImages.map((img) => (
            <img
              key={img.url}
              src={img.url}
              alt={img.alt}
              style={{ width: "100%", borderRadius: "8px", border: "1px solid #ddd" }}
            />
          ))}
        </section>
      ) : null}
      {message ? <p style={{ marginTop: "1rem", color: "crimson" }}>{message}</p> : null}
      <Link to="/">Back</Link>
    </main>
  );
}

function LogoutButton() {
  return (
    <button
      onClick={() => {
        clearSession();
        window.location.href = "/";
      }}
      style={{ position: "fixed", top: 12, right: 12 }}
    >
      Logout
    </button>
  );
}

export function App() {
  return (
    <>
      <LogoutButton />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/my-scenarios"
          element={
            <RequireAuth>
              <MyScenariosPage />
            </RequireAuth>
          }
        />
        <Route
          path="/my-profile"
          element={
            <RequireAuth>
              <MyProfilePage />
            </RequireAuth>
          }
        />
        <Route
          path="/scenarios/new"
          element={
            <RequireAuth>
              <NewScenarioPage />
            </RequireAuth>
          }
        />
        <Route
          path="/scenarios/:id/edit"
          element={
            <RequireAuth>
              <EditScenarioPage />
            </RequireAuth>
          }
        />
        <Route
          path="/review"
          element={
            <RequireAuth>
              <ReviewPage />
            </RequireAuth>
          }
        />
        <Route path="/public/:slug" element={<PublicScenarioPage />} />
      </Routes>
    </>
  );
}

