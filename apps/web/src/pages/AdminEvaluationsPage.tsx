import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listAdminEvaluationModerationTargets,
  type AdminEvaluationModerationTarget,
} from "../adminApi";
import { ScenarioEvaluationInsights } from "../components/ScenarioEvaluationInsights";
import { getToken } from "../session";

const layoutStyle = { maxWidth: "960px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };

function formatPublishedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

export function AdminEvaluationsPage() {
  const token = getToken() ?? "";
  const [targets, setTargets] = useState<AdminEvaluationModerationTarget[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [selectedId, setSelectedId] = useState("");

  useEffect(() => {
    setLoading(true);
    listAdminEvaluationModerationTargets(token)
      .then((res) => {
        setTargets(res.items);
        if (res.items.length && !selectedId) {
          setSelectedId(res.items[0].scenario_id);
        }
      })
      .catch((e: Error) => setMessage(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  const selected = targets.find((t) => t.scenario_id === selectedId);

  return (
    <main style={layoutStyle}>
      <h2>Admin — evaluation moderation</h2>
      <p>
        <Link to="/admin/catalogs">Catalogs</Link> · <Link to="/admin/assignments">Assignments</Link> ·{" "}
        <Link to="/admin/audit">Activity log</Link> · <Link to="/">Home</Link>
      </p>
      {message ? <p style={{ color: "crimson" }}>{message}</p> : null}
      {loading ? <p style={{ color: "#666" }}>Loading published scenarios…</p> : null}
      {!loading && targets.length === 0 ? (
        <p style={{ color: "#666" }}>No published scenarios yet.</p>
      ) : null}
      {!loading && targets.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 280px) 1fr", gap: "1.5rem" }}>
          <nav aria-label="Published scenarios">
            <h3 style={{ marginTop: 0, fontSize: "1rem" }}>Published scenarios</h3>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {targets.map((row) => {
                const active = row.scenario_id === selectedId;
                return (
                  <li key={row.scenario_id} style={{ marginBottom: "0.35rem" }}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(row.scenario_id)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "0.5rem 0.65rem",
                        borderRadius: "6px",
                        border: active ? "2px solid #1a73e8" : "1px solid #ddd",
                        background: active ? "#e8f0fe" : "#fff",
                        cursor: "pointer",
                        font: "inherit",
                      }}
                    >
                      <div style={{ fontWeight: 600, lineHeight: 1.3 }}>{row.title}</div>
                      <div style={{ fontSize: "0.8rem", color: "#555", marginTop: "0.2rem" }}>
                        {row.evaluation_count} evaluation{row.evaluation_count === 1 ? "" : "s"} ·{" "}
                        {formatPublishedAt(row.published_at)}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          <div>
            {selected ? (
              <ScenarioEvaluationInsights
                scenarioId={selected.scenario_id}
                scenarioTitle={selected.title}
                token={token}
                showSummary
                showDetail
                showModeration
              />
            ) : (
              <p style={{ color: "#666" }}>Select a scenario to moderate evaluations.</p>
            )}
          </div>
        </div>
      ) : null}
    </main>
  );
}
