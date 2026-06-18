import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchPublicSearchCategories,
  markNotSuitableScenario,
  publishScenario,
  requestChangesScenario,
  reviewedScenarios,
  reviewQueue,
  reopenScenario,
  startReviewScenario,
  type PublicCatalogEntry,
} from "../api";
import { CatalogFilterDropdown } from "../components/CatalogFilterDropdown";
import { PageLayout } from "../components/PageLayout";
import { ScenarioCard } from "../components/ScenarioCard";
import { ScenarioSearchField } from "../components/ScenarioSearchField";
import { StatusMessage } from "../components/StatusMessage";
import { getRole, getToken } from "../session";

type QueueItem = Awaited<ReturnType<typeof reviewQueue>>["items"][number];
type ReviewedItem = Awaited<ReturnType<typeof reviewedScenarios>>["items"][number];

function authorMetaLine(item: { author_display_name: string; author_university?: string | null }) {
  return `${item.author_display_name}${item.author_university ? ` · ${item.author_university}` : ""}`;
}

export function ReviewQueuePage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<"pending" | "reviewed">("pending");
  const [pending, setPending] = useState<QueueItem[]>([]);
  const [reviewed, setReviewed] = useState<ReviewedItem[]>([]);
  const [message, setMessage] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [categories, setCategories] = useState<PublicCatalogEntry[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [pendingPage, setPendingPage] = useState(1);
  const [reviewedPage, setReviewedPage] = useState(1);
  const pageSize = 6;

  useEffect(() => {
    fetchPublicSearchCategories()
      .then((res) => setCategories(res.items))
      .catch(() => setCategories([]));
  }, []);

  const searchParams = {
    q: submittedQ || undefined,
    category_id: selectedCategoryIds.length ? selectedCategoryIds : undefined,
  };

  const load = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const [queue, done] = await Promise.all([
        reviewQueue(token, searchParams),
        reviewedScenarios(token, searchParams),
      ]);
      setPending(queue.items);
      setReviewed(done.items);
      setMessage("");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, [submittedQ, selectedCategoryIds]);

  useEffect(() => {
    setPendingPage(1);
    setReviewedPage(1);
  }, [submittedQ, selectedCategoryIds]);

  const pendingTotalPages = Math.max(1, Math.ceil(pending.length / pageSize));
  const pendingCurrentPage = Math.min(pendingPage, pendingTotalPages);
  const paginatedPending = pending.slice((pendingCurrentPage - 1) * pageSize, pendingCurrentPage * pageSize);

  const reviewedTotalPages = Math.max(1, Math.ceil(reviewed.length / pageSize));
  const reviewedCurrentPage = Math.min(reviewedPage, reviewedTotalPages);
  const paginatedReviewed = reviewed.slice((reviewedCurrentPage - 1) * pageSize, reviewedCurrentPage * pageSize);

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      setMessage(ok);
      await load();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const token = getToken() ?? "";
  const isAdmin = getRole() === "admin";

  return (
    <PageLayout documentTitle="Review queue" heading="Review queue">
      <ScenarioSearchField value={searchQ} onChange={setSearchQ} onSubmit={() => setSubmittedQ(searchQ.trim())} />
      <div className="filter-row">
        <CatalogFilterDropdown
          label="Categories"
          emptyLabel="All categories"
          options={categories.map((c) => ({ id: c.id, label: c.label }))}
          selectedIds={selectedCategoryIds}
          onChange={setSelectedCategoryIds}
        />
      </div>
      <div className="btn-group" role="tablist" aria-label="Review lists">
        <button type="button" className="btn" onClick={() => setTab("pending")} disabled={tab === "pending"}>
          Pending queue
        </button>
        <button type="button" className="btn" onClick={() => setTab("reviewed")} disabled={tab === "reviewed"}>
          Already reviewed
        </button>
      </div>
      {loading ? (
        <p className="text-muted" role="status" aria-live="polite">
          Loading…
        </p>
      ) : null}
      {tab === "pending" ? (
        <div className="scenario-card-grid">
          {paginatedPending.map((item) => (
            <ScenarioCard
              key={item.scenario_id}
              scenario={{
                id: item.scenario_id,
                title: item.title,
                href: `/scenarios/${item.scenario_id}/edit`,
                coverUrl: item.cover_url,
                coverAlt: item.cover_alt,
                descriptionPreview: item.description_preview,
                badges: [
                  { label: item.state.replaceAll("_", " "), tone: "muted" },
                  ...(item.has_prior_approval ? [{ label: "Republication", tone: "warning" as const }] : []),
                ],
                meta: [
                  authorMetaLine(item),
                  item.submitted_at ? `Submitted ${new Date(item.submitted_at).toLocaleString()}` : "",
                ].filter(Boolean),
                footer: (
                  <div className="btn-group">
                    {item.state === "queued" ? (
                      <button
                        type="button"
                        className="btn btn--primary"
                        onClick={() =>
                          run(async () => {
                            await startReviewScenario(token, item.scenario_id);
                            navigate(`/scenarios/${item.scenario_id}/edit`);
                          }, "Review started.")
                        }
                      >
                        Start review
                      </button>
                    ) : (
                      <Link to={`/scenarios/${item.scenario_id}/edit`} className="btn btn--primary">
                        Open for review
                      </Link>
                    )}
                    {item.state === "in_review" ? (
                      <>
                        <button
                          type="button"
                          className="btn"
                          onClick={() => run(() => publishScenario(token, item.scenario_id), "Published.")}
                        >
                          Publish
                        </button>
                        <button
                          type="button"
                          className="btn"
                          onClick={() => {
                            const note = window.prompt("Required changes (note to author):");
                            if (!note?.trim()) return;
                            run(() => requestChangesScenario(token, item.scenario_id, note.trim()), "Changes requested.");
                          }}
                        >
                          Request changes
                        </button>
                        <button
                          type="button"
                          className="btn"
                          onClick={() => {
                            const reason = window.prompt("Reason (optional):");
                            run(
                              () => markNotSuitableScenario(token, item.scenario_id, reason ?? undefined),
                              "Marked not suitable.",
                            );
                          }}
                        >
                          Mark not suitable
                        </button>
                      </>
                    ) : null}
                    {item.live_public_path ? (
                      <Link to={item.live_public_path} className="btn">
                        View public
                      </Link>
                    ) : null}
                  </div>
                ),
              }}
            />
          ))}
        </div>
      ) : (
        <div className="scenario-card-grid">
          {paginatedReviewed.map((item) => (
            <ScenarioCard
              key={item.scenario_id}
              scenario={{
                id: item.scenario_id,
                title: item.title,
                href: `/scenarios/${item.scenario_id}/edit`,
                coverUrl: item.cover_url,
                coverAlt: item.cover_alt,
                descriptionPreview: item.description_preview,
                badges: [
                  { label: item.state.replaceAll("_", " "), tone: "muted" },
                  { label: item.last_review_outcome ?? "reviewed", tone: "default" },
                ],
                meta: [
                  authorMetaLine(item),
                  `Reviewed ${new Date(item.last_reviewed_at).toLocaleString()}`,
                ],
                footer: (
                  <div className="btn-group">
                    <Link to={`/scenarios/${item.scenario_id}/edit`} className="btn btn--primary">
                      Open
                    </Link>
                    {item.live_public_path ? (
                      <Link to={item.live_public_path} className="btn">
                        View public
                      </Link>
                    ) : null}
                    {isAdmin && item.state === "not_suitable" ? (
                      <button
                        type="button"
                        className="btn"
                        onClick={() => run(() => reopenScenario(token, item.scenario_id), "Reopened to draft.")}
                      >
                        Reopen (admin)
                      </button>
                    ) : null}
                  </div>
                ),
              }}
            />
          ))}
        </div>
      )}
      {tab === "pending" && pending.length > pageSize ? (
        <nav className="pagination" aria-label="Pending review queue pagination">
          <button
            type="button"
            className="btn"
            disabled={pendingCurrentPage <= 1}
            onClick={() => setPendingPage((p) => p - 1)}
          >
            Previous
          </button>
          <span className="text-muted" style={{ fontSize: "0.9rem" }}>
            Page {pendingCurrentPage} of {pendingTotalPages} ({pending.length} results)
          </span>
          <button
            type="button"
            className="btn"
            disabled={pendingCurrentPage >= pendingTotalPages}
            onClick={() => setPendingPage((p) => p + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
      {tab === "reviewed" && reviewed.length > pageSize ? (
        <nav className="pagination" aria-label="Reviewed scenarios pagination">
          <button
            type="button"
            className="btn"
            disabled={reviewedCurrentPage <= 1}
            onClick={() => setReviewedPage((p) => p - 1)}
          >
            Previous
          </button>
          <span className="text-muted" style={{ fontSize: "0.9rem" }}>
            Page {reviewedCurrentPage} of {reviewedTotalPages} ({reviewed.length} results)
          </span>
          <button
            type="button"
            className="btn"
            disabled={reviewedCurrentPage >= reviewedTotalPages}
            onClick={() => setReviewedPage((p) => p + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
      {tab === "pending" && !loading && !pending.length ? <p>No pending items match your filters.</p> : null}
      {tab === "reviewed" && !loading && !reviewed.length ? <p>No reviewed items match your filters.</p> : null}
      <StatusMessage message={message} onDismiss={() => setMessage("")} />
    </PageLayout>
  );
}
