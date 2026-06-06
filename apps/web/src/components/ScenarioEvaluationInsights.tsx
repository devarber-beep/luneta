import { useEffect, useState } from "react";
import {
  getScenarioEvaluationSummary,
  listScenarioEvaluations,
  moderateScenarioEvaluation,
  type EvaluationItem,
  type EvaluationSummary,
} from "../api";
import { formatEvaluationScore } from "./evaluationLabels";
import { getRole } from "../session";

function OwnerCommentsBody({ comments }: { comments: string[] }) {
  return (
    <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
      {comments.map((text, index) => (
        <li key={`${index}-${text.slice(0, 24)}`} style={{ marginBottom: "0.35rem", whiteSpace: "pre-wrap" }}>
          {text}
        </li>
      ))}
    </ul>
  );
}

function SummaryBody({ summary, ownerComments }: { summary: EvaluationSummary; ownerComments?: string[] }) {
  if (summary.evaluation_count === 0) {
    return <p style={{ color: "#666", margin: 0 }}>No evaluations yet.</p>;
  }
  return (
    <>
      <p style={{ margin: "0 0 0.5rem" }}>
        <strong>{summary.evaluation_count}</strong> evaluation
        {summary.evaluation_count === 1 ? "" : "s"}
        {summary.average_risk_score != null ? (
          <>
            {" "}
            · avg. risk{" "}
            <strong>{formatEvaluationScore(summary.average_risk_score)}</strong>/10 · avg. benefit{" "}
            <strong>
              {summary.average_benefit_score != null
                ? formatEvaluationScore(summary.average_benefit_score)
                : "—"}
            </strong>
            /10
          </>
        ) : null}
      </p>
      {summary.detected_ethical_risk_labels.length ? (
        <p style={{ margin: 0 }}>
          <strong>Risks cited:</strong> {summary.detected_ethical_risk_labels.join(", ")}
        </p>
      ) : null}
      {ownerComments?.length ? (
        <div style={{ marginTop: "0.75rem" }}>
          <strong>Comments</strong>
          <OwnerCommentsBody comments={ownerComments} />
        </div>
      ) : null}
    </>
  );
}

type Props = {
  scenarioId: string;
  token: string;
  scenarioTitle?: string;
  showSummary: boolean;
  /** Scenario owner: aggregates like others, optional anonymous comments, no evaluator identity. */
  ownerView?: boolean;
  showDetail: boolean;
  showModeration: boolean;
};

export function ScenarioEvaluationInsights({
  scenarioId,
  token,
  scenarioTitle,
  showSummary,
  ownerView = false,
  showDetail,
  showModeration,
}: Props) {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [details, setDetails] = useState<EvaluationItem[]>([]);
  const [message, setMessage] = useState("");

  const reload = async () => {
    if (!showSummary && !showDetail) {
      return;
    }
    try {
      if (showSummary) {
        const sum = await getScenarioEvaluationSummary(token, scenarioId);
        setSummary(sum);
      }
      if (showDetail) {
        const list = await listScenarioEvaluations(token, scenarioId);
        setDetails(list.items);
      }
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  useEffect(() => {
    if (!token || !scenarioId) {
      return;
    }
    reload().catch((e: Error) => setMessage(e.message));
  }, [scenarioId, token, showSummary, showDetail]);

  const onModerate = async (evaluationId: string, action: "hide" | "delete") => {
    const label = action === "hide" ? "hide" : "permanently delete";
    if (!window.confirm(`${action === "hide" ? "Hide" : "Delete"} this evaluation?`)) {
      return;
    }
    try {
      await moderateScenarioEvaluation(token, evaluationId, action);
      setMessage(`Evaluation ${label === "hide" ? "hidden" : "deleted"}.`);
      await reload();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  if (!showSummary && !showDetail) {
    return null;
  }

  const body = (
    <>
      {message ? <p style={{ color: "crimson" }}>{message}</p> : null}
      {!summary && showSummary ? <p style={{ color: "#666" }}>Loading community evaluations…</p> : null}
      {summary && showSummary ? (
        <SummaryBody
          summary={summary}
          ownerComments={ownerView ? summary.comments : undefined}
        />
      ) : null}
      {showDetail && details.length > 0 ? (
        <div style={{ marginTop: "1rem" }}>
          <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>Evaluation detail</h4>
          <ul style={{ paddingLeft: "1.25rem", margin: 0 }}>
            {details.map((ev) => (
              <li key={ev.id} style={{ marginBottom: "0.85rem" }}>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
                  <strong>{ev.evaluator_display_name ?? ev.evaluator_user_id}</strong>
                  {ev.visibility === "hidden" ? (
                    <span style={{ fontSize: "0.85rem", color: "#888" }}>(hidden)</span>
                  ) : null}
                  {showModeration ? (
                    <>
                      <button type="button" onClick={() => onModerate(ev.id, "hide")}>
                        Hide
                      </button>
                      <button type="button" onClick={() => onModerate(ev.id, "delete")}>
                        Delete
                      </button>
                    </>
                  ) : null}
                </div>
                <span>
                  {" "}
                  — risk {formatEvaluationScore(ev.risk_score)}/10, benefit {formatEvaluationScore(ev.benefit_score)}
                  /10
                </span>
                {ev.detected_ethical_risk_labels.length ? (
                  <span> ({ev.detected_ethical_risk_labels.join(", ")})</span>
                ) : null}
                {ev.comment ? <p style={{ margin: "0.25rem 0 0" }}>{ev.comment}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {showDetail && getRole() === "admin" && details.length === 0 && summary?.evaluation_count === 0 ? (
        <p style={{ color: "#666", marginTop: "0.75rem" }}>No evaluations to moderate.</p>
      ) : null}
    </>
  );

  const heading = scenarioTitle ? `${scenarioTitle} — evaluations` : "Community ethical evaluations";

  return (
    <section
      style={{
        marginTop: "1.5rem",
        padding: "1rem",
        background: "#f8f6ff",
        borderRadius: "8px",
      }}
    >
      <h3 style={{ marginTop: 0 }}>{heading}</h3>
      {body}
    </section>
  );
}
