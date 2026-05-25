import type { EvaluationAspects } from "../api";

export function formatEvaluationScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

const AGE_LABELS: Record<NonNullable<EvaluationAspects["children_age"]>, string> = {
  "0-4": "0–4",
  "5-9": "5–9",
  "10-14": "10–14",
  "15_or_more": "15 or more",
};

const DURATION_LABELS: Record<NonNullable<EvaluationAspects["duration_frequency"]>, string> = {
  daily: "Daily",
  once_a_week: "Once a week",
  several_times_a_day: "Several times a day",
  several_times_a_week: "Several times a week",
  once_a_month: "Once a month",
};

function yesNoLabel(value: "yes" | "no"): string {
  return value === "yes" ? "Yes" : "No";
}

export function describeEvaluationAspects(aspects: EvaluationAspects): string[] {
  const lines: string[] = [];
  if (aspects.children_age) {
    lines.push(`Children age: ${AGE_LABELS[aspects.children_age]}`);
  }
  if (aspects.duration_frequency) {
    lines.push(`Duration and frequency: ${DURATION_LABELS[aspects.duration_frequency]}`);
  }
  if (aspects.execution_place) {
    lines.push(`Place affects scenario: ${yesNoLabel(aspects.execution_place)}`);
  }
  if (aspects.special_circumstances) {
    lines.push(`Special circumstances: ${yesNoLabel(aspects.special_circumstances)}`);
  }
  if (aspects.consent) {
    lines.push(`Consent in place: ${yesNoLabel(aspects.consent)}`);
  }
  return lines;
}
