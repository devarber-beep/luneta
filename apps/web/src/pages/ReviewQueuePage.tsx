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
import { ScenarioSearchField } from "../components/ScenarioSearchField";
import { getRole, getToken } from "../session";

const layoutStyle = { maxWidth: "900px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };

type QueueItem = {
  scenario_id: string;
  title: string;
  author_user_id: string;
  author_university?: string | null;
  state: string;
  has_prior_approval: boolean;
  submitted_at?: string | null;
  live_public_title?: string | null;
  live_public_description?: string | null;
  live_public_path?: string | null;
};

export function ReviewQueuePage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<"pending" | "reviewed">("pending");
  const [pending, setPending] = useState<QueueItem[]>([]);
  const [reviewed, setReviewed] = useState<
    Array<{
      scenario_id: string;
      title: string;
      author_university?: string | null;
      state: string;
      last_reviewed_at: string;
      last_review_outcome?: string | null;
      live_public_path?: string | null;
    }>
  >([]);
  const [message, setMessage] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [categories, setCategories] = useState<PublicCatalogEntry[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

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
    <main style={layoutStyle}>
      <h2>Review</h2>
      <p>Role: {getRole() ?? "—"}</p>
      <ScenarioSearchField
        value={searchQ}
        onChange={setSearchQ}
        onSubmit={() => setSubmittedQ(searchQ.trim())}
        placeholder="Search by title, description, author or university"
      />
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <CatalogFilterDropdown
          label="Categories"
          emptyLabel="All categories"
          options={categories.map((c) => ({ id: c.id, label: c.label }))}
          selectedIds={selectedCategoryIds}
          onChange={setSelectedCategoryIds}
        />
      </div>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button type="button" onClick={() => setTab("pending")} disabled={tab === "pending"}>
          Pending queue
        </button>
        <button type="button" onClick={() => setTab("reviewed")} disabled={tab === "reviewed"}>
          Already reviewed
        </button>
      </div>
      {loading ? <p style={{ color: "#666" }}>Loading…</p> : null}
      {tab === "pending" ? (
        <>
          {pending.map((item) => (
            <div
              key={item.scenario_id}
              style={{ border: "1px solid #ccc", padding: "0.75rem", marginBottom: "0.75rem" }}
            >
              <strong>{item.title}</strong> — {item.state}
              <br />
              <span style={{ fontSize: "0.85rem", color: "#555" }}>
                Owner: {item.author_user_id}
                {item.author_university ? ` · ${item.author_university}` : ""}
              </span>
              {item.submitted_at ? (
                <p style={{ fontSize: "0.85rem", margin: "0.35rem 0" }}>
                  Submitted: {new Date(item.submitted_at).toLocaleString()}
                </p>
              ) : null}
              {item.has_prior_approval && item.live_public_title ? (
                <div style={{ marginTop: "0.5rem", padding: "0.5rem", background: "#f9f9f9", borderRadius: "4px" }}>
                  <strong>Live public version:</strong> {item.live_public_title}
                  {item.live_public_description ? (
                    <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem", marginTop: "0.35rem" }}>
                      {item.live_public_description}
                    </pre>
                  ) : null}
                </div>
              ) : null}
              <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {item.state === "queued" ? (
                  <button
                    type="button"
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
                  <Link to={`/scenarios/${item.scenario_id}/edit`}>Open for review</Link>
                )}
                {item.state === "in_review" ? (
                  <>
                    <button
                      type="button"
                      onClick={() => run(() => publishScenario(token, item.scenario_id), "Published.")}
                    >
                      Publish
                    </button>
                    <button
                      type="button"
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
                {item.live_public_path ? <Link to={item.live_public_path}>View public</Link> : null}
              </div>
            </div>
          ))}
          {!loading && !pending.length ? <p>No pending items match your filters.</p> : null}
        </>
      ) : (
        <>
          {reviewed.map((item) => (
            <div
              key={item.scenario_id}
              style={{ border: "1px solid #ddd", padding: "0.75rem", marginBottom: "0.75rem" }}
            >
              <strong>{item.title}</strong> — {item.state} ({item.last_review_outcome ?? "—"})
              {item.author_university ? (
                <p style={{ fontSize: "0.85rem", margin: "0.25rem 0" }}>{item.author_university}</p>
              ) : null}
              <p style={{ fontSize: "0.85rem" }}>Reviewed: {new Date(item.last_reviewed_at).toLocaleString()}</p>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <Link to={`/scenarios/${item.scenario_id}/edit`}>Open</Link>
                {item.live_public_path ? <Link to={item.live_public_path}>View public</Link> : null}
                {isAdmin && item.state === "not_suitable" ? (
                  <button
                    type="button"
                    onClick={() => run(() => reopenScenario(token, item.scenario_id), "Reopened to draft.")}
                  >
                    Reopen (admin)
                  </button>
                ) : null}
              </div>
            </div>
          ))}
          {!loading && !reviewed.length ? <p>No reviewed items match your filters.</p> : null}
        </>
      )}
      {message ? <p>{message}</p> : null}
      <Link to="/">Back</Link>
    </main>
  );
}
