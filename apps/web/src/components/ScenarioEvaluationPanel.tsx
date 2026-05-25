import { type FormEvent, useEffect, useState } from "react";
import {
  fetchActiveEthicalRisks,
  getMyScenarioEvaluation,
  submitScenarioEvaluation,
  type EvaluationAspects,
  type EvaluationItem,
} from "../api";

const CHILDREN_AGE_OPTIONS: Array<{ value: EvaluationAspects["children_age"]; label: string }> = [
  { value: "0-4", label: "0–4" },
  { value: "5-9", label: "5–9" },
  { value: "10-14", label: "10–14" },
  { value: "15_or_more", label: "15 or more" },
];

const DURATION_OPTIONS: Array<{ value: EvaluationAspects["duration_frequency"]; label: string }> = [
  { value: "daily", label: "Daily" },
  { value: "once_a_week", label: "Once a week" },
  { value: "several_times_a_day", label: "Several times a day" },
  { value: "several_times_a_week", label: "Several times a week" },
  { value: "once_a_month", label: "Once a month" },
];

const YES_NO_OPTIONS: Array<{ value: EvaluationAspects["consent"]; label: string }> = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

const emptyAspects = (): EvaluationAspects => ({
  children_age: "",
  duration_frequency: "",
  execution_place: "",
  special_circumstances: "",
  consent: "",
});

function formatScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

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
    <label style={{ display: "grid", gap: "0.35rem" }}>
      <span>
        {label}: <strong>{formatScore(value)}</strong> / 10
      </span>
      <input
        type="range"
        min={1}
        max={10}
        step={0.5}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%" }}
      />
    </label>
  );
}

function YesNoField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: "" | "yes" | "no";
  onChange: (next: "yes" | "no") => void;
}) {
  return (
    <fieldset style={{ border: "none", margin: 0, padding: 0 }}>
      <legend style={{ marginBottom: "0.35rem", fontWeight: 500 }}>{label}</legend>
      <div style={{ display: "flex", gap: "1rem" }}>
        {YES_NO_OPTIONS.map((opt) => (
          <label key={opt.value} style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
            <input
              type="radio"
              name={label}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              required={value === ""}
            />
            {opt.label}
          </label>
        ))}
      </div>
    </fieldset>
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
  const [aspects, setAspects] = useState<EvaluationAspects>(emptyAspects);
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

  const aspectsComplete =
    aspects.children_age !== "" &&
    aspects.duration_frequency !== "" &&
    aspects.execution_place !== "" &&
    aspects.special_circumstances !== "" &&
    aspects.consent !== "";

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (selectedRisks.length === 0) {
      setMessage("Select at least one ethical risk from the catalog.");
      return;
    }
    if (!aspectsComplete) {
      setMessage("Complete all required fields in the evaluation form.");
      return;
    }
    try {
      await submitScenarioEvaluation(token, scenarioId, {
        risk_score: riskScore,
        benefit_score: benefitScore,
        detected_ethical_risk_ids: selectedRisks,
        comment,
        aspects: aspects as EvaluationAspects,
      });
      setMessage("Evaluation submitted. Thank you.");
      await reload();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const toggleRisk = (id: string) => {
    setSelectedRisks((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  if (!token || isOwner) {
    return null;
  }

  if (loading) {
    return <p style={{ marginTop: "1.5rem", color: "#666" }}>Loading evaluation…</p>;
  }

  if (existing) {
    return (
      <details style={{ marginTop: "2rem" }} open>
        <summary style={{ cursor: "pointer", fontWeight: 600, fontSize: "1.05rem" }}>
          Your ethical evaluation
        </summary>
        <section style={{ marginTop: "0.75rem", padding: "1rem", background: "#f4f8f4", borderRadius: "8px" }}>
          <p>
            <strong>Ethical risk:</strong> {formatScore(existing.risk_score)}/10 · <strong>Benefit:</strong>{" "}
            {formatScore(existing.benefit_score)}/10
          </p>
          {existing.detected_ethical_risk_labels.length ? (
            <p>
              <strong>Risks detected:</strong> {existing.detected_ethical_risk_labels.join(", ")}
            </p>
          ) : null}
          {existing.comment ? <p>{existing.comment}</p> : null}
          <p style={{ fontSize: "0.9rem", color: "#666" }}>
            Submitted {new Date(existing.submitted_at).toLocaleString()}. Evaluations cannot be edited after
            submission.
          </p>
        </section>
      </details>
    );
  }

  if (!canSubmit) {
    return null;
  }

  return (
    <details style={{ marginTop: "2rem" }}>
      <summary style={{ cursor: "pointer", fontWeight: 600, fontSize: "1.05rem" }}>
        Ethical evaluation
      </summary>
      <section style={{ marginTop: "0.75rem", padding: "1rem", border: "1px solid #ddd", borderRadius: "8px" }}>
        <p style={{ color: "#555", fontSize: "0.95rem", marginTop: 0 }}>
          Share your assessment of this published scenario. You may submit one evaluation per scenario.
        </p>
        <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.85rem" }}>
          <HalfPointSlider label="Ethical risk score" value={riskScore} onChange={setRiskScore} />
          <HalfPointSlider label="Benefit score" value={benefitScore} onChange={setBenefitScore} />

          <fieldset style={{ border: "1px solid #eee", padding: "0.75rem", margin: 0 }}>
            <legend>Ethical risks detected (select at least one)</legend>
            <div style={{ display: "grid", gap: "0.35rem", maxHeight: "200px", overflowY: "auto" }}>
              {risks.map((r) => (
                <label key={r.id} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
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

          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>Free comment (optional)</span>
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} />
          </label>

          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>Children age range</span>
            <select
              required
              value={aspects.children_age}
              onChange={(e) =>
                setAspects((prev) => ({
                  ...prev,
                  children_age: e.target.value as EvaluationAspects["children_age"],
                }))
              }
            >
              <option value="" disabled>
                Select a range
              </option>
              {CHILDREN_AGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>Duration and frequency</span>
            <select
              required
              value={aspects.duration_frequency}
              onChange={(e) =>
                setAspects((prev) => ({
                  ...prev,
                  duration_frequency: e.target.value as EvaluationAspects["duration_frequency"],
                }))
              }
            >
              <option value="" disabled>
                Select an option
              </option>
              {DURATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <YesNoField
            label="Does the execution place affect the scenario?"
            value={aspects.execution_place}
            onChange={(next) => setAspects((prev) => ({ ...prev, execution_place: next }))}
          />
          <YesNoField
            label="Are there special circumstances for the child?"
            value={aspects.special_circumstances}
            onChange={(next) => setAspects((prev) => ({ ...prev, special_circumstances: next }))}
          />
          <YesNoField
            label="Is consent in place for this scenario?"
            value={aspects.consent}
            onChange={(next) => setAspects((prev) => ({ ...prev, consent: next }))}
          />

          <button type="submit">Submit evaluation</button>
        </form>
        {message ? <p style={{ color: message.includes("Thank") ? "#060" : "crimson" }}>{message}</p> : null}
      </section>
    </details>
  );
}
