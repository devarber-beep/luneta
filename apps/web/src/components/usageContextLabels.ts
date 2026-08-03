import type { ScenarioUsageContext } from "../api";

const DURATION_LABELS: Record<NonNullable<ScenarioUsageContext["duration_frequency"]>, string> = {
  daily: "Daily",
  once_a_week: "Once a week",
  several_times_a_day: "Several times a day",
  several_times_a_week: "Several times a week",
  once_a_month: "Once a month",
};

function yesNoLabel(value: "yes" | "no"): string {
  return value === "yes" ? "Yes" : "No";
}

export function describeUsageContext(ctx: ScenarioUsageContext | null | undefined): string[] {
  const safe = ctx ?? {};
  const lines: string[] = [];
  const age =
    safe.children_age_start != null && safe.children_age_end != null
      ? `${safe.children_age_start}-${safe.children_age_end}`
      : "—";
  lines.push(`Children age range: ${age}`);
  lines.push(`Number of children: ${safe.children_count == null ? "—" : String(safe.children_count)}`);
  lines.push(`Duration and frequency: ${safe.duration_frequency ? DURATION_LABELS[safe.duration_frequency] : "—"}`);
  lines.push(`Physically present: ${safe.physically_present ? yesNoLabel(safe.physically_present) : "—"}`);
  lines.push(`Online presence: ${safe.online_present ? yesNoLabel(safe.online_present) : "—"}`);
  lines.push(
    `Execution place affects scenario: ${
      safe.execution_place_affects_scenario ? yesNoLabel(safe.execution_place_affects_scenario) : "—"
    }`,
  );
  lines.push(`Special circumstances for the child: ${safe.special_circumstances ? yesNoLabel(safe.special_circumstances) : "—"}`);
  lines.push(`Consent in place: ${safe.consent_in_place ? yesNoLabel(safe.consent_in_place) : "—"}`);
  return lines;
}

export const USAGE_CONTEXT_DURATION_OPTIONS = [
  { value: "daily" as const, label: "Daily" },
  { value: "once_a_week" as const, label: "Once a week" },
  { value: "several_times_a_day" as const, label: "Several times a day" },
  { value: "several_times_a_week" as const, label: "Several times a week" },
  { value: "once_a_month" as const, label: "Once a month" },
];

export const USAGE_CONTEXT_YES_NO_OPTIONS = [
  { value: "yes" as const, label: "Yes" },
  { value: "no" as const, label: "No" },
];
