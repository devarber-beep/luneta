import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import {
  fetchActiveEthicalRisks,
  getMyScenarioEvaluation,
  submitScenarioEvaluation,
  type EvaluationItem,
} from "../api";
import { formatEvaluationScore } from "./evaluationLabels";
import { StatusMessage } from "./StatusMessage";

const EVALUATION_SUCCESS_MESSAGE = "Thank you for sharing your assessment.";

function HalfPointSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  return (
    <label className="evaluation-slider">
      <span className="evaluation-slider__label">
        {label}: <strong>{formatEvaluationScore(value)}</strong>
        <span className="evaluation-slider__max"> / 10</span>
      </span>
      <input
        type="range"
        className="evaluation-slider__input"
        min={1}
        max={10}
        step={0.5}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

type Props = {
  scenarioId: string;
  token: string;
  authorUserId: string;
  myUserId: string | null;
};

export function ScenarioEvaluationPanel({ scenarioId, token, authorUserId, myUserId }: Props) {
  const [risks, setRisks] = useState<Array<{ id: string; label: string }>>([]);
  const [existing, setExisting] = useState<EvaluationItem | null>(null);
  const [canSubmit, setCanSubmit] = useState(false);
  const [riskScore, setRiskScore] = useState(5);
  const [benefitScore, setBenefitScore] = useState(5);
  const [selectedRisks, setSelectedRisks] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const isOwner = myUserId != null && myUserId === authorUserId;

  const reload = async () => {
    setLoading(true);
    try {
      const [riskCatalog, mine] = await Promise.all([
        fetchActiveEthicalRisks(token),
        getMyScenarioEvaluation(token, scenarioId),
      ]);
      setRisks(riskCatalog.items);
      setExisting(mine.evaluation);
      setCanSubmit(mine.can_submit);
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token || isOwner) {
      setLoading(false);
      return;
    }
    reload().catch((e: Error) => setMessage(e.message));
  }, [scenarioId, token, isOwner]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (selectedRisks.length === 0) {
      setMessage("Select at least one ethical risk from the catalog.");
      return;
    }
    try {
      await submitScenarioEvaluation(token, scenarioId, {
        risk_score: riskScore,
        benefit_score: benefitScore,
        detected_ethical_risk_ids: selectedRisks,
        comment,
      });
      setMessage(EVALUATION_SUCCESS_MESSAGE);
      await reload();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const toggleRisk = (id: string) => {
    setSelectedRisks((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const statusFeedback =
    message === EVALUATION_SUCCESS_MESSAGE
      ? { variant: "success" as const, presentation: "modal" as const, title: "Evaluation submitted" }
      : { variant: undefined, presentation: "auto" as const, title: undefined };

  if (!token || isOwner) {
    return null;
  }

  let content: ReactNode;

  if (loading) {
    content = <p className="evaluation-panel__loading">Loading evaluation…</p>;
  } else if (existing) {
    content = (
      <details className="evaluation-disclosure" open>
        <summary className="evaluation-disclosure__summary">Your ethical evaluation</summary>
        <section className="evaluation-submitted">
          <div className="evaluation-summary__scores">
            <div className="evaluation-score evaluation-score--risk">
              <span className="evaluation-score__label">Ethical risk</span>
              <span className="evaluation-score__value">
                {formatEvaluationScore(existing.risk_score)}
                <span className="evaluation-score__max">/10</span>
              </span>
            </div>
            <div className="evaluation-score evaluation-score--benefit">
              <span className="evaluation-score__label">Benefit</span>
              <span className="evaluation-score__value">
                {formatEvaluationScore(existing.benefit_score)}
                <span className="evaluation-score__max">/10</span>
              </span>
            </div>
          </div>
          {existing.detected_ethical_risk_labels.length ? (
            <div className="evaluation-summary__risks">
              <span className="evaluation-summary__risks-label">Risks detected</span>
              <ul className="evaluation-tag-list">
                {existing.detected_ethical_risk_labels.map((label) => (
                  <li key={label} className="evaluation-tag evaluation-tag--risk">
                    {label}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {existing.comment ? <p className="evaluation-submitted__comment">{existing.comment}</p> : null}
          <p className="evaluation-submitted__meta">
            Submitted {new Date(existing.submitted_at).toLocaleString()}. Evaluations cannot be edited after
            submission.
          </p>
        </section>
      </details>
    );
  } else if (!canSubmit) {
    return null;
  } else {
    content = (
      <details className="evaluation-disclosure">
        <summary className="evaluation-disclosure__summary">Submit your ethical evaluation</summary>
        <section className="evaluation-form">
          <form onSubmit={onSubmit} className="evaluation-form__fields">
            <HalfPointSlider label="Ethical risk score" value={riskScore} onChange={setRiskScore} />
            <HalfPointSlider label="Benefit score" value={benefitScore} onChange={setBenefitScore} />

            <fieldset className="evaluation-form__fieldset">
              <legend className="evaluation-form__legend">Ethical risks detected (select at least one)</legend>
              <div className="catalog-checklist evaluation-form__risks">
                {risks.map((r) => (
                  <label key={r.id} className="catalog-checklist__item">
                    <input
                      type="checkbox"
                      checked={selectedRisks.includes(r.id)}
                      onChange={() => toggleRisk(r.id)}
                    />
                    <span>{r.label}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="evaluation-form__comment">
              <span className="evaluation-form__comment-label">Free comment (optional)</span>
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} />
            </label>

            <div className="evaluation-form__actions">
              <button type="submit" className="btn btn--primary">
                Submit evaluation
              </button>
            </div>
          </form>
        </section>
      </details>
    );
  }

  return (
    <>
      {content}
      {message ? (
        <StatusMessage
          message={message}
          {...statusFeedback}
          onDismiss={() => setMessage("")}
        />
      ) : null}
    </>
  );
}
