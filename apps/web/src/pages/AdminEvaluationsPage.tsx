import { useEffect, useMemo, useState } from "react";
import {
  listAdminEvaluationModerationTargets,
  type AdminEvaluationModerationTarget,
} from "../adminApi";
import { ScenarioEvaluationInsights } from "../components/ScenarioEvaluationInsights";
import { getToken } from "../session";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";

const PAGE_SIZE = 4;

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
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    listAdminEvaluationModerationTargets(token)
      .then((res) => {
        setTargets(res.items);
        setPage(1);
        if (res.items.length) {
          setSelectedId(res.items[0].scenario_id);
        } else {
          setSelectedId("");
        }
      })
      .catch((e: Error) => setMessage(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  const totalPages = Math.max(1, Math.ceil(targets.length / PAGE_SIZE));
  const paginatedTargets = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return targets.slice(start, start + PAGE_SIZE);
  }, [targets, page]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  useEffect(() => {
    if (!paginatedTargets.length) {
      return;
    }
    if (!paginatedTargets.some((t) => t.scenario_id === selectedId)) {
      setSelectedId(paginatedTargets[0].scenario_id);
    }
  }, [paginatedTargets, selectedId]);

  const selected = targets.find((t) => t.scenario_id === selectedId);

  return (
    <PageLayout documentTitle="Evaluations" heading="">
      <StatusMessage message={message} onDismiss={() => setMessage("")} />
      {loading ? <p className="text-muted">Loading published scenarios…</p> : null}
      {!loading && targets.length === 0 ? (
        <p className="text-muted">No published scenarios yet.</p>
      ) : null}
      {!loading && targets.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 280px) 1fr", gap: "1.5rem" }}>
          <nav aria-label="Published scenarios">
            <h3 style={{ marginTop: 0, fontSize: "1rem" }}>Published scenarios</h3>
            <ul className="list-picker">
              {paginatedTargets.map((row) => {
                const active = row.scenario_id === selectedId;
                return (
                  <li key={row.scenario_id} className="list-picker__item">
                    <button
                      type="button"
                      onClick={() => setSelectedId(row.scenario_id)}
                      className={`list-picker__button${active ? " list-picker__button--active" : ""}`}
                    >
                      <div className="list-picker__title">{row.title}</div>
                      <div className="list-picker__meta">
                        {row.evaluation_count} evaluation{row.evaluation_count === 1 ? "" : "s"} ·{" "}
                        {formatPublishedAt(row.published_at)}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
            {targets.length > PAGE_SIZE ? (
              <nav className="pagination" aria-label="Published scenarios pagination">
                <button type="button" className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </button>
                <span className="text-muted" style={{ fontSize: "0.9rem" }}>
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  className="btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </nav>
            ) : null}
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
              <p className="text-muted">Select a scenario to moderate evaluations.</p>
            )}
          </div>
        </div>
      ) : null}
    </PageLayout>
  );
}
