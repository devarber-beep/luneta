import { useEffect, useState } from "react";
import {
  getScenarioEvaluationSummary,
  listScenarioEvaluations,
  moderateScenarioEvaluation,
  type EvaluationItem,
  type EvaluationSummary,
} from "../api";
import { formatEvaluationScore } from "./evaluationLabels";
import { StatusMessage } from "./StatusMessage";
import { getRole } from "../session";

function OwnerCommentsBody({ comments }: { comments: string[] }) {
  return (
    <ul className="evaluation-summary__comment-list">
      {comments.map((text, index) => (
        <li key={`${index}-${text.slice(0, 24)}`} className="evaluation-summary__comment-item">
          {text}
        </li>
      ))}
    </ul>
  );
}

function SummaryBody({ summary, ownerComments }: { summary: EvaluationSummary; ownerComments?: string[] }) {
  if (summary.evaluation_count === 0) {
    return <p className="evaluation-summary__empty">No community evaluations yet.</p>;
  }

  return (
    <div className="evaluation-summary">
      <p className="evaluation-summary__count">
        <strong>{summary.evaluation_count}</strong> evaluation
        {summary.evaluation_count === 1 ? "" : "s"}
      </p>

      {summary.average_risk_score != null ? (
        <div className="evaluation-summary__scores">
          <div className="evaluation-score evaluation-score--risk">
            <span className="evaluation-score__label">Avg. ethical risk</span>
            <span className="evaluation-score__value">
              {formatEvaluationScore(summary.average_risk_score)}
              <span className="evaluation-score__max">/10</span>
            </span>
          </div>
          <div className="evaluation-score evaluation-score--benefit">
            <span className="evaluation-score__label">Avg. benefit</span>
            <span className="evaluation-score__value">
              {summary.average_benefit_score != null
                ? formatEvaluationScore(summary.average_benefit_score)
                : "—"}
              <span className="evaluation-score__max">/10</span>
            </span>
          </div>
        </div>
      ) : null}

      {summary.detected_ethical_risk_labels.length ? (
        <div className="evaluation-summary__risks">
          <span className="evaluation-summary__risks-label">Risks cited</span>
          <ul className="evaluation-tag-list">
            {summary.detected_ethical_risk_labels.map((label) => (
              <li key={label} className="evaluation-tag evaluation-tag--risk">
                {label}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {ownerComments?.length ? (
        <div className="evaluation-summary__comments">
          <span className="evaluation-summary__comments-label">Comments</span>
          <OwnerCommentsBody comments={ownerComments} />
        </div>
      ) : null}
    </div>
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
        setSummary(await getScenarioEvaluationSummary(token, scenarioId));
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
      <StatusMessage message={message} onDismiss={() => setMessage("")} />
      {!summary && showSummary ? (
        <p className="evaluation-panel__loading">Loading community evaluations…</p>
      ) : null}
      {summary && showSummary ? (
        <SummaryBody summary={summary} ownerComments={ownerView ? summary.comments : undefined} />
      ) : null}
      {showDetail && details.length > 0 ? (
        <div className="evaluation-detail">
          <h4 className="evaluation-detail__title">Evaluation detail</h4>
          <ul className="evaluation-detail__list">
            {details.map((ev) => (
              <li key={ev.id} className="evaluation-detail__item">
                <div className="evaluation-detail__header">
                  <strong className="evaluation-detail__author">
                    {ev.evaluator_display_name ?? ev.evaluator_user_id}
                  </strong>
                  {ev.visibility === "hidden" ? (
                    <span className="evaluation-detail__badge">Hidden</span>
                  ) : null}
                  {showModeration ? (
                    <div className="evaluation-detail__actions">
                      <button type="button" className="btn btn--ghost btn--small" onClick={() => onModerate(ev.id, "hide")}>
                        Hide
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost btn--small evaluation-detail__delete"
                        onClick={() => onModerate(ev.id, "delete")}
                      >
                        Delete
                      </button>
                    </div>
                  ) : null}
                </div>
                <div className="evaluation-detail__scores">
                  <span className="evaluation-detail__score evaluation-detail__score--risk">
                    Risk {formatEvaluationScore(ev.risk_score)}/10
                  </span>
                  <span className="evaluation-detail__score evaluation-detail__score--benefit">
                    Benefit {formatEvaluationScore(ev.benefit_score)}/10
                  </span>
                </div>
                {ev.detected_ethical_risk_labels.length ? (
                  <ul className="evaluation-tag-list evaluation-tag-list--inline">
                    {ev.detected_ethical_risk_labels.map((label) => (
                      <li key={label} className="evaluation-tag evaluation-tag--risk">
                        {label}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {ev.comment ? <p className="evaluation-detail__comment">{ev.comment}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {showDetail && getRole() === "admin" && details.length === 0 && summary?.evaluation_count === 0 ? (
        <p className="evaluation-panel__empty">No evaluations to moderate.</p>
      ) : null}
    </>
  );

  const heading = scenarioTitle ? `${scenarioTitle} — evaluations` : "Community ethical evaluations";
  const headingId = `evaluations-${scenarioId}`;

  return (
    <section className="evaluation-panel" aria-labelledby={headingId}>
      <h3 id={headingId} className="evaluation-panel__title">
        {heading}
      </h3>
      {body}
    </section>
  );
}
