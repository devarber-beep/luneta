import { type ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatEvaluationScore } from "./evaluationLabels";

export type ScenarioCardData = {
  id: string;
  title: string;
  href: string;
  coverUrl?: string | null;
  coverAlt?: string | null;
  descriptionPreview?: string | null;
  evaluationCount?: number;
  averageRiskScore?: number | null;
  averageBenefitScore?: number | null;
  meta?: string[];
  badges?: Array<{ label: string; tone?: "default" | "warning" | "muted" }>;
  footer?: ReactNode;
};

type Props = {
  scenario: ScenarioCardData;
};

export function ScenarioCard({ scenario }: Props) {
  const {
    title,
    href,
    coverUrl,
    coverAlt,
    descriptionPreview,
    evaluationCount = 0,
    averageRiskScore,
    averageBenefitScore,
    meta = [],
    badges = [],
    footer,
  } = scenario;

  return (
    <article className="scenario-card">
      <Link to={href} className="scenario-card__cover-link" tabIndex={-1} aria-hidden={!coverUrl}>
        {coverUrl ? (
          <img src={coverUrl} alt={coverAlt || ""} className="scenario-card__cover" loading="lazy" />
        ) : (
          <div className="scenario-card__cover scenario-card__cover--placeholder" aria-hidden>
            No cover
          </div>
        )}
      </Link>
      <div className="scenario-card__body">
        <div className="scenario-card__head">
          <h3 className="scenario-card__title">
            <Link to={href}>{title}</Link>
          </h3>
          {badges.length ? (
            <div className="scenario-card__badges">
              {badges.map((badge) => (
                <span
                  key={badge.label}
                  className={`scenario-card__badge scenario-card__badge--${badge.tone ?? "default"}`}
                >
                  {badge.label}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        {descriptionPreview ? <p className="scenario-card__preview">{descriptionPreview}</p> : null}
        {evaluationCount > 0 ? (
          <p className="scenario-card__eval">
            <span className="scenario-card__eval-label">Community ethics</span>
            {" · "}
            risk{" "}
            <strong>
              {averageRiskScore != null ? formatEvaluationScore(averageRiskScore) : "—"}
            </strong>
            /10 · benefit{" "}
            <strong>
              {averageBenefitScore != null ? formatEvaluationScore(averageBenefitScore) : "—"}
            </strong>
            /10
            <span className="text-muted"> ({evaluationCount})</span>
          </p>
        ) : (
          <p className="scenario-card__eval text-muted">No community evaluations yet</p>
        )}
        {meta.length ? (
          <ul className="scenario-card__meta">
            {meta.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : null}
        {footer ? <div className="scenario-card__footer">{footer}</div> : null}
      </div>
    </article>
  );
}
