import { type ChangeEvent, type FormEvent, type ReactElement, useEffect, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  changeMyPassword,
  deleteMyAvatar,
  deleteScenario,
  getScenario,
  listMyScenarios,
  login,
  me,
  patchMyProfile,
  uploadMyAvatar,
  listScenarioSuggestions,
  publicScenario,
  signup,
  type SuggestionItem,
  verifyEmail,
} from "./api";
import { clearSession, setMustChangePassword, setRole, setToken } from "./session";
import { useMustChangePassword, useRole, useToken } from "./useSession";
import { DescriptionWithSuggestions } from "./components/DescriptionWithSuggestions";
import { ScenarioDescriptionContent } from "./components/ScenarioDescriptionContent";
import { ScenarioEvaluationPanel } from "./components/ScenarioEvaluationPanel";
import { ScenarioEvaluationInsights } from "./components/ScenarioEvaluationInsights";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { ScenarioEditorPage } from "./pages/ScenarioEditorPage";
import { AdminCatalogPage } from "./pages/AdminCatalogPage";
import { AdminAssignmentsPage } from "./pages/AdminAssignmentsPage";
import { AdminEvaluationsPage } from "./pages/AdminEvaluationsPage";
import { AdminAuditPage } from "./pages/AdminAuditPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { PublishedScenariosSection } from "./components/PublishedScenariosSection";
import { ScenarioSearchField } from "./components/ScenarioSearchField";
import { SiteNavbar } from "./components/SiteNavbar";
import { SiteFooter } from "./components/SiteFooter";
import { ScenarioCard } from "./components/ScenarioCard";
import { PageLayout } from "./components/PageLayout";
import { FormField } from "./components/FormField";
import { StatusMessage } from "./components/StatusMessage";
import { ConfirmModal } from "./components/ConfirmModal";
import { AdminDeleteScenarioButton } from "./components/AdminDeleteScenarioButton";
import { describeUsageContext } from "./components/usageContextLabels";
import type { ScenarioSummary, ScenarioUsageContext } from "./api";

function HomePage() {
  return (
    <PageLayout documentTitle="Home" heading="Published scenarios" headingLevel={2}>
      <PublishedScenariosSection
        sectionHeading=""
        searchPlaceholder="Search by title, description, author or university"
      />
    </PageLayout>
  );
}

function AboutPage() {
  return (
    <PageLayout documentTitle="About" heading="About">
      <div className="card prose-block">
        <p>
          This platform supports the collection, review, and publication of smart-glasses usage scenarios in
          childhood contexts, as part of the{" "}
          <a href="https://jphourcade.com/projects/xrforyouthethics/index.html" rel="noreferrer" target="_blank">
            XR for Youth Ethics Consortium
          </a>
          .
        </p>
      </div>
    </PageLayout>
  );
}

function ContactPage() {
  return (
    <PageLayout documentTitle="Contact" heading="Contact">
      <div className="card prose-block">
        <p>
          For questions about the consortium or this platform, contact Juan Pablo Hourcade at{" "}
          <a href="mailto:juanpablo-hourcade@uiowa.edu">juanpablo-hourcade@uiowa.edu</a>.
        </p>
        <p>
          More information is available on the{" "}
          <a href="https://jphourcade.com/projects/xrforyouthethics/index.html" rel="noreferrer" target="_blank">
            consortium website
          </a>
          .
        </p>
      </div>
    </PageLayout>
  );
}

function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const fn = firstName.trim();
    const ln = lastName.trim();
    if (!fn || !ln) {
      setMessage("First and last name are required.");
      return;
    }
    try {
      const response = await signup({
        email,
        password,
        first_name: fn,
        last_name: ln,
      });
      setMessage(`User created: ${response.user_id}. Check logs for the verification token.`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <PageLayout documentTitle="Signup" heading="Signup" className="page-layout--auth">
      <div className="auth-card card">
        <form onSubmit={onSubmit} className="form-stack">
        <FormField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <FormField
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <FormField
          label="First name"
          autoComplete="given-name"
          required
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
        />
        <FormField
          label="Last name"
          autoComplete="family-name"
          required
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
        />
        <button type="submit" className="btn btn--primary">
          Create account
        </button>
        </form>
        <StatusMessage message={message} onDismiss={() => setMessage("")} />
        <p className="auth-card__footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </PageLayout>
  );
}

function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get("token")?.trim() ?? "";
  const [message, setMessage] = useState("");
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    if (!tokenFromUrl) {
      return;
    }
    setVerifying(true);
    verifyEmail(tokenFromUrl)
      .then((response) => {
        setMessage(response.verified ? "Email verified. You can sign in now." : "Could not verify this link.");
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setVerifying(false));
  }, [tokenFromUrl]);

  if (!tokenFromUrl) {
    return <Navigate to="/" replace />;
  }

  return (
    <PageLayout documentTitle="Verify email" heading="Verify email">
      {verifying ? <p className="text-muted">Verifying your email…</p> : null}
      <StatusMessage message={message} onDismiss={() => setMessage("")} />
      <p>
        <Link to="/login">Go to login</Link>
      </p>
    </PageLayout>
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
      setMustChangePassword(auth.must_change_password);
      const profile = await me(auth.access_token);
      setRole(profile.role);
      setMustChangePassword(profile.must_change_password);
      setMessage(`Signed in as ${profile.role}`);
      if (profile.must_change_password) {
        navigate("/my-profile");
      } else if (profile.role === "reviewer" || profile.role === "admin") {
        navigate("/review");
      } else {
        navigate("/my-scenarios");
      }
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <PageLayout documentTitle="Login" heading="Login" className="page-layout--auth">
      <div className="auth-card card">
        <form onSubmit={onSubmit} className="form-stack">
        <FormField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <FormField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" className="btn btn--primary">
          Sign in
        </button>
        </form>
        <StatusMessage message={message} onDismiss={() => setMessage("")} />
        <p className="auth-card__footer">
          Need an account? <Link to="/signup">Sign up</Link>
        </p>
      </div>
    </PageLayout>
  );
}

function RequireAdmin({ children }: { children: ReactElement }) {
  const role = useRole();
  if (role !== "admin") {
    return <Navigate to="/" replace />;
  }
  return children;
}

function RequireAuth({ children }: { children: ReactElement }) {
  const token = useToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function RequireActiveSession({ children }: { children: ReactElement }) {
  const mustChange = useMustChangePassword();
  const location = useLocation();
  if (!mustChange) {
    return children;
  }
  const path = location.pathname;
  if (path === "/my-profile" || path === "/my-scenarios") {
    return children;
  }
  if (/^\/scenarios\/[^/]+\/view$/.test(path)) {
    return children;
  }
  return <Navigate to="/my-profile" replace />;
}

function profileStatusFeedback(message: string) {
  if (message === "Profile saved." || message === "Photo updated." || message === "Photo removed.") {
    return { variant: "success" as const, presentation: "modal" as const, title: "Done" };
  }
  if (message.startsWith("Password updated.")) {
    return { variant: "success" as const, presentation: "modal" as const, title: "Password updated" };
  }
  return { variant: undefined, presentation: "auto" as const, title: undefined };
}

function MyProfilePage() {
  const token = useToken();
  const mustChangePassword = useMustChangePassword();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [university, setUniversity] = useState("");
  const [biography, setBiography] = useState("");
  const [readOnlyEmail, setReadOnlyEmail] = useState("");
  const [readOnlyRole, setReadOnlyRole] = useState("");
  const [verified, setVerified] = useState(false);
  const [verifiedAt, setVerifiedAt] = useState<string | null>(null);
  const [lastLoginAt, setLastLoginAt] = useState<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    if (!token) return;
    const profile = await me(token);
    setFirstName(profile.first_name);
    setLastName(profile.last_name);
    setDisplayName(profile.display_name);
    setUniversity(profile.university ?? "");
    setBiography(profile.biography ?? "");
    setReadOnlyEmail(profile.email_normalized);
    setMustChangePassword(profile.must_change_password);
    setReadOnlyRole(profile.role);
    setVerified(profile.email_verified_at != null);
    setVerifiedAt(profile.email_verified_at);
    setLastLoginAt(profile.last_login_at);
    setAvatarUrl(profile.avatar_url);
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, [token]);

  const onSaveProfile = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) return;
    const fn = firstName.trim();
    const ln = lastName.trim();
    if (!fn || !ln) {
      setMessage("First and last name are required.");
      return;
    }
    try {
      await patchMyProfile(token, {
        first_name: fn,
        last_name: ln,
        university: university.trim() || null,
        biography: biography.trim() || null,
      });
      setMessage("Profile saved.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onAvatarSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    if (!token) return;
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await uploadMyAvatar(token, file);
      setMessage("Photo updated.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      event.target.value = "";
    }
  };

  const onRemoveAvatar = async () => {
    if (!token) return;
    try {
      await deleteMyAvatar(token);
      setMessage("Photo removed.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onChangePassword = async (event: FormEvent) => {
    event.preventDefault();
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
      setMustChangePassword(false);
      setMessage("Password updated. You can now create and edit scenarios.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <PageLayout documentTitle="My profile" heading="My profile" headingLevel={1} className="page-layout--profile">
      <div className="profile-page">
        {mustChangePassword ? (
          <section className="card profile-page__callout card--warning" aria-labelledby="password-required-heading">
            <h3 id="password-required-heading">Password change required</h3>
            <p>
              Your account uses a temporary password. Change it below before creating or editing scenarios. You can
              still browse your scenarios in read-only mode from <Link to="/my-scenarios">My scenarios</Link>.
            </p>
          </section>
        ) : null}

        <section className="card profile-page__hero" aria-label="Profile overview">
          <div className="profile-page__avatar-block">
            {avatarUrl ? (
              <img src={avatarUrl} alt="" className="profile-avatar profile-avatar--large" />
            ) : (
              <div className="profile-avatar profile-avatar--large profile-avatar--placeholder" aria-hidden>
                No photo
              </div>
            )}
            {!mustChangePassword ? (
              <div className="profile-page__avatar-actions">
                <label className="btn btn--primary">
                  Upload photo
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={onAvatarSelected}
                    className="sr-only"
                  />
                </label>
                {avatarUrl ? (
                  <button type="button" className="btn btn--ghost" onClick={onRemoveAvatar}>
                    Remove photo
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
          <div className="profile-page__identity">
            <h2 className="profile-page__display-name">{displayName || readOnlyEmail || "—"}</h2>
            {readOnlyRole ? (
              <span className="profile-page__role-badge">{readOnlyRole.replaceAll("_", " ")}</span>
            ) : null}
            {readOnlyEmail ? <p className="profile-page__email text-muted">{readOnlyEmail}</p> : null}
          </div>
        </section>

        <section className="card editor-section" aria-labelledby="account-heading">
          <h3 id="account-heading" className="editor-section__title">
            Account
          </h3>
          <dl className="profile-page__meta-list">
            <dt>Email verified</dt>
            <dd>
              <span className={verified ? "profile-page__verified--yes" : "profile-page__verified--no"}>
                {verified ? "Yes" : "No"}
              </span>
              {verifiedAt ? ` · ${new Date(verifiedAt).toLocaleString()}` : ""}
            </dd>
            <dt>Last login</dt>
            <dd>{lastLoginAt ? new Date(lastLoginAt).toLocaleString() : "—"}</dd>
            <dt>Display name</dt>
            <dd>{displayName || "—"}</dd>
          </dl>
        </section>

        {!mustChangePassword ? (
          <section className="card editor-section" aria-labelledby="profile-details-heading">
            <h3 id="profile-details-heading" className="editor-section__title">
              Profile details
            </h3>
            <form onSubmit={onSaveProfile} className="profile-page__form">
              <FormField label="First name" required value={firstName} onChange={(e) => setFirstName(e.target.value)} />
              <FormField label="Last name" required value={lastName} onChange={(e) => setLastName(e.target.value)} />
              <FormField
                label="University"
                hint="Optional"
                value={university}
                onChange={(e) => setUniversity(e.target.value)}
              />
              <FormField
                label="Biography"
                hint="Optional"
                multiline
                rows={4}
                value={biography}
                onChange={(e) => setBiography(e.target.value)}
              />
              <div className="profile-page__form-actions">
                <button type="submit" className="btn btn--primary">
                  Save profile
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className="card editor-section" aria-labelledby="password-heading">
          <h3 id="password-heading" className="editor-section__title">
            Change password
          </h3>
          <form onSubmit={onChangePassword} className="profile-page__form">
            <FormField
              label="Current password"
              type="password"
              autoComplete="current-password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <FormField
              label="New password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <FormField
              label="Confirm new password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            <div className="profile-page__form-actions">
              <button type="submit" className="btn btn--primary">
                Update password
              </button>
            </div>
          </form>
        </section>
      </div>

      <StatusMessage
        message={message}
        {...profileStatusFeedback(message)}
        onDismiss={() => setMessage("")}
      />
    </PageLayout>
  );
}

function MyScenariosPage() {
  const token = useToken();
  const mustChangePassword = useMustChangePassword();
  const [searchParams, setSearchParams] = useSearchParams();
  type MyScenariosTab = "all" | "changes_required" | "applying_changes" | "published" | "pending_suggestions";
  const tabParam = searchParams.get("state");
  const activeTab: MyScenariosTab =
    tabParam === "changes_required" ||
    tabParam === "applying_changes" ||
    tabParam === "published" ||
    tabParam === "pending_suggestions"
      ? tabParam
      : "all";
  const [items, setItems] = useState<ScenarioSummary[]>([]);
  const [pendingTabCount, setPendingTabCount] = useState(0);
  const [searchQ, setSearchQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: string; title: string; state: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const pageSize = 6;

  const load = async () => {
    if (!token) {
      return;
    }
    setLoading(true);
    try {
      const rows = await listMyScenarios(token, {
        q: submittedQ || undefined,
        state:
          activeTab === "changes_required" ||
          activeTab === "applying_changes" ||
          activeTab === "published"
            ? activeTab
            : undefined,
        pending_suggestions: activeTab === "pending_suggestions",
      });
      setItems(rows);
      setMessage("");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const onDeleteScenario = (id: string, title: string, state: string) => {
    setDeleteConfirm({ id, title, state });
  };

  const executeDeleteScenario = async () => {
    if (!token || !deleteConfirm) {
      return;
    }
    const isDraft = deleteConfirm.state === "draft";
    setDeleting(true);
    try {
      await deleteScenario(token, deleteConfirm.id);
      setDeleteConfirm(null);
      setMessage(isDraft ? "Draft deleted." : "Scenario deleted.");
      await load();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    if (!token) {
      return;
    }
    listMyScenarios(token, { pending_suggestions: true })
      .then((rows) => setPendingTabCount(rows.length))
      .catch(() => setPendingTabCount(0));
  }, [token]);

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, [token, submittedQ, activeTab]);

  useEffect(() => {
    setPage(1);
  }, [submittedQ, activeTab]);

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const paginatedItems = items.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const setTab = (tab: MyScenariosTab) => {
    if (tab === "all") {
      setSearchParams({});
    } else {
      setSearchParams({ state: tab });
    }
  };

  const emptyMessage =
    submittedQ
      ? "No scenarios match your search."
      : activeTab === "changes_required"
        ? "No scenarios require changes."
        : activeTab === "applying_changes"
          ? "No scenarios are being updated."
          : activeTab === "published"
            ? "No published scenarios."
            : activeTab === "pending_suggestions"
              ? "No scenarios with pending suggestions."
              : "No scenarios are associated with your account.";

  return (
    <PageLayout documentTitle="My scenarios" heading="My scenarios">
      <div className="btn-group btn-group--tabs" role="tablist" aria-label="Scenario filters">
        <button type="button" className="btn" onClick={() => setTab("all")} disabled={activeTab === "all"}>
          All scenarios
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => setTab("changes_required")}
          disabled={activeTab === "changes_required"}
        >
          Changes required
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => setTab("applying_changes")}
          disabled={activeTab === "applying_changes"}
        >
          Applying changes
        </button>
        <button type="button" className="btn" onClick={() => setTab("published")} disabled={activeTab === "published"}>
          Published
        </button>
        <button
          type="button"
          className="btn btn--with-badge"
          onClick={() => setTab("pending_suggestions")}
          disabled={activeTab === "pending_suggestions"}
          aria-label={
            pendingTabCount > 0
              ? `Pending suggestions (${pendingTabCount})`
              : "Pending suggestions"
          }
        >
          Pending suggestions
          {pendingTabCount > 0 ? (
            <span className="tab-badge" aria-hidden>
              {pendingTabCount}
            </span>
          ) : null}
        </button>
      </div>
      <ScenarioSearchField value={searchQ} onChange={setSearchQ} onSubmit={() => setSubmittedQ(searchQ.trim())} />
      <button type="button" className="btn" onClick={() => load().catch((e: Error) => setMessage(e.message))}>
        Refresh
      </button>
      {loading ? (
        <p className="text-muted" role="status" aria-live="polite">
          Loading…
        </p>
      ) : null}
      <div className="scenario-card-grid">
        {paginatedItems.map((s) => (
          <ScenarioCard
            key={s.id}
            scenario={{
              id: s.id,
              title: s.title,
              href:
                s.my_participation_role === "owner" && !mustChangePassword
                  ? `/scenarios/${s.id}/edit`
                  : `/scenarios/${s.id}/view`,
              coverUrl: s.cover_url,
              coverAlt: s.cover_alt,
              descriptionPreview: s.description_preview,
              evaluationCount: s.evaluation_count,
              averageRiskScore: s.average_risk_score,
              averageBenefitScore: s.average_benefit_score,
              badges: [
                { label: s.state.replaceAll("_", " "), tone: "muted" },
                {
                  label: s.my_participation_role === "owner" ? "Owner" : "Collaborator",
                  tone: "default",
                },
                ...(s.pending_suggestion_count
                  ? [{ label: `${s.pending_suggestion_count} pending`, tone: "warning" as const }]
                  : []),
              ],
              meta: [`Updated ${new Date(s.updated_at).toLocaleDateString()}`],
              footer: (
                <div className="btn-group">
                  {s.my_participation_role === "owner" ? (
                    mustChangePassword ? (
                      <Link to={`/scenarios/${s.id}/view`} className="btn">
                        View
                      </Link>
                    ) : (
                      <Link to={`/scenarios/${s.id}/edit`} className="btn btn--primary">
                        Edit
                      </Link>
                    )
                  ) : (
                    <Link to={`/scenarios/${s.id}/view`} className="btn">
                      View
                    </Link>
                  )}
                  {s.public_path ? (
                    <Link to={s.public_path} className="btn">
                      Public page
                    </Link>
                  ) : null}
                  {s.my_participation_role === "owner" &&
                  (s.state === "draft" || s.state === "published") &&
                  !mustChangePassword ? (
                    <button
                      type="button"
                      className="btn btn--danger"
                      onClick={() => onDeleteScenario(s.id, s.title, s.state)}
                    >
                      {s.state === "draft" ? "Delete draft" : "Delete scenario"}
                    </button>
                  ) : null}
                </div>
              ),
            }}
          />
        ))}
      </div>
      {items.length > pageSize ? (
        <nav className="pagination" aria-label="My scenarios pagination">
          <button type="button" className="btn" disabled={currentPage <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="text-muted" style={{ fontSize: "0.9rem" }}>
            Page {currentPage} of {totalPages} ({items.length} results)
          </span>
          <button
            type="button"
            className="btn"
            disabled={currentPage >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
      {!loading && !items.length ? <p>{emptyMessage}</p> : null}
      {deleteConfirm ? (
        <ConfirmModal
          title={deleteConfirm.state === "draft" ? "Delete draft?" : "Delete published scenario?"}
          message={
            deleteConfirm.state === "draft"
              ? `“${deleteConfirm.title}” will be removed permanently. Stored images will also be deleted.`
              : `“${deleteConfirm.title}” will disappear from the public catalog. Stored images will be removed. This cannot be undone.`
          }
          variant="warning"
          confirmLabel={deleteConfirm.state === "draft" ? "Delete draft" : "Delete scenario"}
          confirmTone="danger"
          busy={deleting}
          onConfirm={() => executeDeleteScenario()}
          onCancel={() => {
            if (!deleting) {
              setDeleteConfirm(null);
            }
          }}
        />
      ) : null}
      <StatusMessage message={message} onDismiss={() => setMessage("")} />
    </PageLayout>
  );
}

function PublicScenarioPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const token = useToken();
  const role = useRole();
  const [scenarioId, setScenarioId] = useState("");
  const [authorUserId, setAuthorUserId] = useState("");
  const [authorDisplayName, setAuthorDisplayName] = useState("");
  const [authorUniversity, setAuthorUniversity] = useState<string | null>(null);
  const [collaborators, setCollaborators] = useState<Array<{ user_id: string; display_name: string }>>([]);
  const [myUserId, setMyUserId] = useState<string | null>(null);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [categories, setCategories] = useState<Array<{ id: string; label: string }>>([]);
  const [ethicalRisks, setEthicalRisks] = useState<Array<{ id: string; label: string }>>([]);
  const [usageContextLines, setUsageContextLines] = useState<string[]>([]);
  const [publicCanSuggest, setPublicCanSuggest] = useState(false);
  const [publishedAt, setPublishedAt] = useState("");
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [coverAlt, setCoverAlt] = useState<string>("cover image");
  const [inlineImages, setInlineImages] = useState<Array<{ url: string; alt: string }>>([]);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [canViewSuggestions, setCanViewSuggestions] = useState(false);
  const [message, setMessage] = useState("");

  const loadSuggestions = async (sid: string) => {
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
    if (token) {
      me(token)
        .then((profile) => setMyUserId(profile.user_id))
        .catch(() => setMyUserId(null));
    } else {
      setMyUserId(null);
    }
  }, [token]);

  useEffect(() => {
    if (!slug) {
      return;
    }
    publicScenario(slug)
      .then(async (data) => {
        setScenarioId(data.id);
        setAuthorUserId(data.author_user_id);
        setAuthorDisplayName(data.author_display_name);
        setAuthorUniversity(data.author_university ?? null);
        setCollaborators(data.collaborators ?? []);
        setTitle(data.title);
        setDescription(data.description);
        setCategories(data.categories ?? []);
        setEthicalRisks(data.ethical_risks ?? []);
        setUsageContextLines(describeUsageContext(data.usage_context as ScenarioUsageContext | null));
        setPublishedAt(data.published_at);
        setCoverUrl(data.cover_image?.signed_url ?? null);
        setCoverAlt(data.cover_image?.alt_text ?? "cover image");
        setInlineImages(
          (data.inline_assets ?? [])
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((x) => ({ url: x.signed_url, alt: x.alt_text ?? "scenario image" })),
        );
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
  }, [slug, token]);

  const hasSidebarMeta =
    categories.length > 0 || ethicalRisks.length > 0 || usageContextLines.length > 0;
  const showAside = Boolean(coverUrl) || hasSidebarMeta;

  return (
    <PageLayout
      documentTitle={title || "Public scenario"}
      heading={title || "Public scenario"}
      headingLevel={1}
      className="page-layout--public-scenario"
      headerAside={
        role === "admin" && scenarioId && token ? (
          <AdminDeleteScenarioButton
            scenarioId={scenarioId}
            title={title}
            token={token}
            onDeleted={() => navigate("/")}
            onError={(message) => setMessage(message)}
          />
        ) : null
      }
    >
      {publishedAt ? (
        <p className="public-scenario__published text-muted">
          Published {new Date(publishedAt).toLocaleDateString(undefined, { dateStyle: "long" })}
        </p>
      ) : null}

      <article className="public-scenario">
        <div className={`public-scenario__layout${showAside ? " public-scenario__layout--split" : ""}`}>
          {showAside ? (
            <aside className="public-scenario__aside" aria-label="Illustration and classification">
              {coverUrl ? (
                <figure className="public-scenario__cover-figure">
                  <img src={coverUrl} alt={coverAlt} className="public-scenario__cover" />
                </figure>
              ) : null}

              {categories.length > 0 ? (
                <section className="public-scenario__sidebar-section" aria-labelledby="public-scenario-categories">
                  <h3 id="public-scenario-categories" className="public-scenario__sidebar-title">
                    Categories
                  </h3>
                  <ul className="public-scenario__tag-list">
                    {categories.map((c) => (
                      <li key={c.id} className="public-scenario__tag">
                        {c.label}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {ethicalRisks.length > 0 ? (
                <section className="public-scenario__sidebar-section" aria-labelledby="public-scenario-risks">
                  <h3 id="public-scenario-risks" className="public-scenario__sidebar-title">
                    Ethical risks
                  </h3>
                  <ul className="public-scenario__tag-list public-scenario__tag-list--risks">
                    {ethicalRisks.map((r) => (
                      <li key={r.id} className="public-scenario__tag public-scenario__tag--risk">
                        {r.label}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {usageContextLines.length > 0 ? (
                <section className="public-scenario__sidebar-section" aria-labelledby="public-scenario-context">
                  <h3 id="public-scenario-context" className="public-scenario__sidebar-title">
                    Usage context
                  </h3>
                  <ul className="public-scenario__context-list">
                    {usageContextLines.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </aside>
          ) : null}

          <div className="public-scenario__main">
            <header className="public-scenario__byline">
              <p className="public-scenario__author-line">
                <span className="public-scenario__byline-label">Author</span>
                <span className="public-scenario__author-name">{authorDisplayName || authorUserId}</span>
                {authorUniversity ? (
                  <span className="public-scenario__affiliation">{authorUniversity}</span>
                ) : null}
              </p>
              {collaborators.length > 0 ? (
                <div className="public-scenario__collaborators">
                  <span className="public-scenario__byline-label">Collaborators</span>
                  <ul className="public-scenario__collaborator-list">
                    {collaborators.map((c) => (
                      <li key={c.user_id}>{c.display_name}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </header>

            <div className="scenario-read-section public-scenario__description">
              {scenarioId && token && (publicCanSuggest || canViewSuggestions) ? (
                <DescriptionWithSuggestions
                  scenarioId={scenarioId}
                  description={description}
                  suggestions={suggestions}
                  canSuggest={publicCanSuggest}
                  canViewSuggestions={canViewSuggestions}
                  canResolve={false}
                  publishedParagraphAltTextOnly
                  onSuggestionSubmitted={async () => {
                    await loadSuggestions(scenarioId);
                  }}
                />
              ) : (
                <ScenarioDescriptionContent description={description} />
              )}
            </div>

            {inlineImages.length ? (
              <section className="public-scenario__gallery" aria-label="Scenario images">
                {inlineImages.map((img) => (
                  <figure key={img.url} className="public-scenario__gallery-item">
                    <img src={img.url} alt={img.alt} className="public-scenario__gallery-image" />
                  </figure>
                ))}
              </section>
            ) : null}

            {scenarioId && token ? (
              <div className="public-scenario__evaluations">
                <ScenarioEvaluationInsights
                  scenarioId={scenarioId}
                  token={token}
                  showSummary
                  ownerView={Boolean(myUserId && authorUserId && myUserId === authorUserId) && role !== "admin"}
                  showDetail={role === "admin"}
                  showModeration={role === "admin"}
                />
                <ScenarioEvaluationPanel
                  scenarioId={scenarioId}
                  token={token}
                  authorUserId={authorUserId}
                  myUserId={myUserId}
                />
              </div>
            ) : null}
          </div>
        </div>
      </article>

      <StatusMessage message={message} onDismiss={() => setMessage("")} />
      <p className="public-scenario__back">
        <Link to="/">Back to catalog</Link>
      </p>
    </PageLayout>
  );
}

export function App() {
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <SiteNavbar />
      <div className="app-shell__body">
        <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
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
              <RequireActiveSession>
                <ScenarioEditorPage isCreate />
              </RequireActiveSession>
            </RequireAuth>
          }
        />
        <Route
          path="/scenarios/:id/edit"
          element={
            <RequireAuth>
              <RequireActiveSession>
                <ScenarioEditorPage />
              </RequireActiveSession>
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
              <RequireActiveSession>
                <ReviewQueuePage />
              </RequireActiveSession>
            </RequireAuth>
          }
        />
        <Route
          path="/admin/users"
          element={
            <RequireAuth>
              <RequireAdmin>
                <AdminUsersPage />
              </RequireAdmin>
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
        <Route
          path="/admin/audit"
          element={
            <RequireAuth>
              <RequireAdmin>
                <AdminAuditPage />
              </RequireAdmin>
            </RequireAuth>
          }
        />
        <Route path="/public/:slug" element={<PublicScenarioPage />} />
        </Routes>
      </div>
      <SiteFooter />
    </div>
  );
}

