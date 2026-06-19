import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { deleteScenario, listMyScenarios, type ScenarioSummary } from "../api";
import { ConfirmModal } from "../components/ConfirmModal";
import { PageLayout } from "../components/PageLayout";
import { ScenarioCard } from "../components/ScenarioCard";
import { ScenarioSearchField } from "../components/ScenarioSearchField";
import { StatusMessage } from "../components/StatusMessage";
import { useMustChangePassword, useToken } from "../useSession";

type MyScenariosTab = "all" | "changes_required" | "applying_changes" | "published" | "pending_suggestions";

export function MyScenariosPage() {
  const token = useToken();
  const mustChangePassword = useMustChangePassword();
  const [searchParams, setSearchParams] = useSearchParams();
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
