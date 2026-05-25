import { type CSSProperties, type FormEvent, type ReactElement, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  changeMyPassword,
  deleteScenario,
  getScenario,
  listMyScenarios,
  listPublicScenarios,
  login,
  me,
  patchMyProfile,
  listScenarioSuggestions,
  publicScenario,
  signup,
  type SuggestionItem,
  verifyEmail,
} from "./api";
import { clearSession, getRole, getToken, setRole, setToken } from "./session";
import { DescriptionWithSuggestions } from "./components/DescriptionWithSuggestions";
import { ScenarioEvaluationPanel } from "./components/ScenarioEvaluationPanel";
import { ScenarioEvaluationInsights } from "./components/ScenarioEvaluationInsights";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { ScenarioEditorPage } from "./pages/ScenarioEditorPage";
import { AdminCatalogPage } from "./pages/AdminCatalogPage";
import { AdminAssignmentsPage } from "./pages/AdminAssignmentsPage";
import { AdminEvaluationsPage } from "./pages/AdminEvaluationsPage";

const layoutStyle: CSSProperties = {
  maxWidth: "860px",
  margin: "0 auto",
  padding: "2rem",
  fontFamily: "system-ui, sans-serif",
};

function HomePage() {
  const token = getToken();
  const [published, setPublished] = useState<Array<{ id: string; title: string; published_at: string; public_path: string }>>([]);
  const [catalogError, setCatalogError] = useState("");

  useEffect(() => {
    listPublicScenarios()
      .then(setPublished)
      .catch((e: Error) => setCatalogError(e.message));
  }, []);

  return (
    <main style={layoutStyle}>
      <h1>Luneta</h1>
      <nav style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginTop: "1rem" }}>
        {!token ? <Link to="/signup">Signup</Link> : null}
        <Link to="/verify-email">Verify email</Link>
        {!token ? <Link to="/login">Login</Link> : null}
        {token ? <Link to="/my-scenarios">My scenarios</Link> : null}
        {token ? <Link to="/my-profile">My profile</Link> : null}
        {token ? <Link to="/scenarios/new">New scenario</Link> : null}
        {getRole() === "reviewer" || getRole() === "admin" ? <Link to="/review">Review queue</Link> : null}
        {getRole() === "admin" ? <Link to="/admin/catalogs">Admin catalogs</Link> : null}
        {getRole() === "admin" ? <Link to="/admin/assignments">Assignments</Link> : null}
        {getRole() === "admin" ? <Link to="/admin/evaluations">Moderate evaluations</Link> : null}

      </nav>
      {token ? <p style={{ marginTop: "1rem" }}>Active session.</p> : <p style={{ marginTop: "1rem" }}>No session.</p>}
      <section style={{ marginTop: "2rem" }}>
        <h2>Published</h2>
        {catalogError ? <p style={{ color: "crimson" }}>{catalogError}</p> : null}
        {!published.length && !catalogError ? <p>No published scenarios yet.</p> : null}
        <ul style={{ paddingLeft: "1.25rem" }}>
          {published.map((s) => (
            <li key={s.id}>
              <Link to={s.public_path}>{s.title}</Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
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
        <button type="submit">Create account</button>
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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const auth = await login(email, password);
      setToken(auth.access_token);
      const profile = await me(auth.access_token);
      setRole(profile.role);
      setMessage(`Signed in as ${profile.role}`);
      if (profile.role === "reviewer" || profile.role === "admin") {
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

function RequireAdmin({ children }: { children: ReactElement }) {
  if (getRole() !== "admin") {
    return <Navigate to="/" replace />;
  }
  return children;
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
    setReadOnlyEmail(profile.email_normalized);
    setReadOnlyRole(profile.role);
    setVerified(profile.email_verified_at != null);
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
    Array<{
      id: string;
      title: string;
      state: string;
      first_published_at?: string | null;
      public_path?: string | null;
      my_participation_role: "owner" | "collaborator";
    }>
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

  const onDeleteDraft = async (id: string, title: string) => {
    const token = getToken();
    if (!token) {
      return;
    }
    if (!window.confirm(`Delete draft “${title}”? This cannot be undone.`)) {
      return;
    }
    try {
      await deleteScenario(token, id);
      setMessage("Draft deleted.");
      await load();
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
            <span style={{ color: "#666", fontSize: "0.9rem" }}>
              ({s.my_participation_role === "owner" ? "Owner" : "Collaborator"})
            </span>{" "}
            {s.my_participation_role === "owner" ? (
              <Link to={`/scenarios/${s.id}/edit`}>Edit / workflow</Link>
            ) : (
              <Link to={`/scenarios/${s.id}/view`}>View</Link>
            )}
            {s.my_participation_role === "owner" && s.state === "draft" ? (
              <>
                {" "}
                <button type="button" onClick={() => onDeleteDraft(s.id, s.title)}>
                  Delete draft
                </button>
              </>
            ) : null}
            {s.public_path ? (
              <>
                {" "}
                <Link to={s.public_path}>View public</Link>
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

function PublicScenarioPage() {
  const { slug } = useParams();
  const [scenarioId, setScenarioId] = useState("");
  const [authorUserId, setAuthorUserId] = useState("");
  const [authorNickname, setAuthorNickname] = useState("");
  const [collaborators, setCollaborators] = useState<Array<{ user_id: string; nickname: string }>>([]);
  const [myUserId, setMyUserId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [summary, setSummary] = useState<string | null>(null);
  const [categories, setCategories] = useState<Array<{ id: string; label: string }>>([]);
  const [ethicalRisks, setEthicalRisks] = useState<Array<{ id: string; label: string }>>([]);
  const [publicCanSuggest, setPublicCanSuggest] = useState(false);
  const [publishedAt, setPublishedAt] = useState("");
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [coverAlt, setCoverAlt] = useState<string>("cover image");
  const [inlineImages, setInlineImages] = useState<Array<{ url: string; alt: string }>>([]);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [canViewSuggestions, setCanViewSuggestions] = useState(false);
  const [message, setMessage] = useState("");

  const loadSuggestions = async (sid: string) => {
    const token = getToken();
    if (!token) return;
    try {
      const list = await listScenarioSuggestions(token, sid);
      setSuggestions(list.items);
      setCanViewSuggestions(true);
    } catch {
      setSuggestions([]);
      setCanViewSuggestions(false);
    }
  };

  useEffect(() => {
    const token = getToken();
    if (token) {
      me(token)
        .then((profile) => setMyUserId(profile.user_id))
        .catch(() => setMyUserId(null));
    }
  }, []);

  useEffect(() => {
    if (!slug) {
      return;
    }
    publicScenario(slug)
      .then(async (data) => {
        setScenarioId(data.id);
        setAuthorUserId(data.author_user_id);
        setAuthorNickname(data.author_nickname);
        setCollaborators(data.collaborators ?? []);
        setTitle(data.title);
        setDescription(data.description);
        setSummary(data.summary ?? null);
        setCategories(data.categories ?? []);
        setEthicalRisks(data.ethical_risks ?? []);
        setPublishedAt(data.published_at);
        setCoverUrl(data.cover_image?.signed_url ?? null);
        setCoverAlt(data.cover_image?.alt_text ?? "cover image");
        setInlineImages(
          (data.inline_assets ?? [])
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((x) => ({ url: x.signed_url, alt: x.alt_text ?? "scenario image" })),
        );
        const token = getToken();
        if (token && data.id) {
          try {
            const detail = await getScenario(token, data.id);
            setPublicCanSuggest(Boolean(detail.can_create_suggestion));
          } catch {
            setPublicCanSuggest(false);
          }
          await loadSuggestions(data.id);
        }
      })
      .catch((error: Error) => setMessage(error.message));
  }, [slug]);

  return (
    <main style={layoutStyle}>
      <h2>Public View</h2>
      {publishedAt ? <p style={{ color: "#666" }}>Published: {new Date(publishedAt).toLocaleString()}</p> : null}
      <section style={{ marginBottom: "1rem", fontSize: "0.95rem", color: "#444" }}>
        <p style={{ margin: "0.25rem 0" }}>
          <strong>Owner:</strong> {authorNickname || authorUserId}
        </p>
        {collaborators.length > 0 ? (
          <div style={{ marginTop: "0.35rem" }}>
            <strong>Collaborators:</strong>
            <ul style={{ margin: "0.25rem 0 0", paddingLeft: "1.25rem" }}>
              {collaborators.map((c) => (
                <li key={c.user_id}>{c.nickname}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {summary ? (
          <p style={{ margin: "0.75rem 0 0" }}>
            <strong>Summary:</strong> {summary}
          </p>
        ) : null}
        {categories.length > 0 ? (
          <p style={{ margin: "0.5rem 0 0" }}>
            <strong>Categories:</strong> {categories.map((c) => c.label).join(", ")}
          </p>
        ) : null}
        {ethicalRisks.length > 0 ? (
          <p style={{ margin: "0.5rem 0 0" }}>
            <strong>Ethical risks:</strong> {ethicalRisks.map((r) => r.label).join(", ")}
          </p>
        ) : null}
      </section>
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
      <div style={{ marginBottom: inlineImages.length ? "1rem" : 0 }}>
        {scenarioId &&
        getToken() &&
        myUserId &&
        authorUserId &&
        myUserId !== authorUserId &&
        (publicCanSuggest || canViewSuggestions) ? (
          <DescriptionWithSuggestions
            scenarioId={scenarioId}
            description={description}
            suggestions={suggestions}
            canSuggest={publicCanSuggest}
            canViewSuggestions={canViewSuggestions}
            canResolve={false}
            onSuggestionSubmitted={async () => {
              setMessage("Suggestion submitted.");
              await loadSuggestions(scenarioId);
            }}
          />
        ) : (
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{description}</pre>
        )}
      </div>
      {inlineImages.length ? (
        <section style={{ display: "grid", gap: "0.75rem", marginBottom: "1rem" }}>
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
      {scenarioId && getToken() ? (
        <>
          <ScenarioEvaluationInsights
            scenarioId={scenarioId}
            token={getToken() ?? ""}
            showSummary
            ownerView={Boolean(myUserId && authorUserId && myUserId === authorUserId) && getRole() !== "admin"}
            showDetail={getRole() === "admin"}
            showModeration={getRole() === "admin"}
          />
          <ScenarioEvaluationPanel
            scenarioId={scenarioId}
            token={getToken() ?? ""}
            authorUserId={authorUserId}
            myUserId={myUserId}
          />
        </>
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
              <ScenarioEditorPage isCreate />
            </RequireAuth>
          }
        />
        <Route
          path="/scenarios/:id/edit"
          element={
            <RequireAuth>
              <ScenarioEditorPage />
            </RequireAuth>
          }
        />
        <Route
          path="/scenarios/:id/view"
          element={
            <RequireAuth>
              <ScenarioEditorPage viewOnly />
            </RequireAuth>
          }
        />
        <Route
          path="/review"
          element={
            <RequireAuth>
              <ReviewQueuePage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/catalogs"
          element={
            <RequireAuth>
              <RequireAdmin>
                <AdminCatalogPage />
              </RequireAdmin>
            </RequireAuth>
          }
        />
        <Route
          path="/admin/assignments"
          element={
            <RequireAuth>
              <RequireAdmin>
                <AdminAssignmentsPage />
              </RequireAdmin>
            </RequireAuth>
          }
        />
        <Route
          path="/admin/evaluations"
          element={
            <RequireAuth>
              <RequireAdmin>
                <AdminEvaluationsPage />
              </RequireAdmin>
            </RequireAuth>
          }
        />
        <Route path="/public/:slug" element={<PublicScenarioPage />} />
      </Routes>
    </>
  );
}

