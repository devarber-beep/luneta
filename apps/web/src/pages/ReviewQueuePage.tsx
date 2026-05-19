import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  markNotSuitableScenario,
  publishScenario,
  requestChangesScenario,
  reviewedScenarios,
  reviewQueue,
  reopenScenario,
  startReviewScenario,
} from "../api";
import { getRole, getToken } from "../session";

const layoutStyle = { maxWidth: "900px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };

type QueueItem = {
  scenario_id: string;
  title: string;
  author_user_id: string;
  state: string;
  has_prior_approval: boolean;
  submitted_at?: string | null;
  live_public_title?: string | null;
  live_public_description?: string | null;
  live_public_path?: string | null;
};

export function ReviewQueuePage() {
  const [tab, setTab] = useState<"pending" | "reviewed">("pending");
  const [pending, setPending] = useState<QueueItem[]>([]);
  const [reviewed, setReviewed] = useState<
    Array<{
      scenario_id: string;
      title: string;
      state: string;
      last_reviewed_at: string;
      last_review_outcome?: string | null;
      live_public_path?: string | null;
    }>
  >([]);
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token) return;
    const [queue, done] = await Promise.all([reviewQueue(token), reviewedScenarios(token)]);
    setPending(queue.items);
    setReviewed(done.items);
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, []);

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
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button type="button" onClick={() => setTab("pending")} disabled={tab === "pending"}>
          Pending queue
        </button>
        <button type="button" onClick={() => setTab("reviewed")} disabled={tab === "reviewed"}>
          Already reviewed
        </button>
      </div>
      {tab === "pending" ? (
        <>
          {pending.map((item) => (
            <div
              key={item.scenario_id}
              style={{ border: "1px solid #ccc", padding: "0.75rem", marginBottom: "0.75rem" }}
            >
              <strong>{item.title}</strong> — {item.state}
              <br />
              <span style={{ fontSize: "0.85rem", color: "#555" }}>Owner: {item.author_user_id}</span>
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
                <Link to={`/scenarios/${item.scenario_id}/edit`}>Open</Link>
                {item.state === "queued" ? (
                  <button
                    type="button"
                    onClick={() => run(() => startReviewScenario(token, item.scenario_id), "Review started.")}
                  >
                    Start review
                  </button>
                ) : null}
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
          {!pending.length ? <p>No pending items.</p> : null}
        </>
      ) : (
        <>
          {reviewed.map((item) => (
            <div
              key={item.scenario_id}
              style={{ border: "1px solid #ddd", padding: "0.75rem", marginBottom: "0.75rem" }}
            >
              <strong>{item.title}</strong> — {item.state} ({item.last_review_outcome ?? "—"})
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
          {!reviewed.length ? <p>No reviewed items yet.</p> : null}
        </>
      )}
      {message ? <p>{message}</p> : null}
      <Link to="/">Back</Link>
    </main>
  );
}

