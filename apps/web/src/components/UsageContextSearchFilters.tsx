import { useEffect, useId, useRef, useState } from "react";
import type { SearchPublicScenariosParams } from "../api";
import { USAGE_CONTEXT_DURATION_OPTIONS, USAGE_CONTEXT_YES_NO_OPTIONS } from "./usageContextLabels";

export type UsageContextSearchFilterState = {
  children_age_min: string;
  children_age_max: string;
  physically_present: "" | "yes" | "no";
  online_present: "" | "yes" | "no";
  execution_place_affects_scenario: "" | "yes" | "no";
  special_circumstances: "" | "yes" | "no";
  consent_in_place: "" | "yes" | "no";
  duration_frequency: SearchPublicScenariosParams["duration_frequency"] | "";
};

export function emptyUsageContextSearchFilters(): UsageContextSearchFilterState {
  return {
    children_age_min: "",
    children_age_max: "",
    physically_present: "",
    online_present: "",
    execution_place_affects_scenario: "",
    special_circumstances: "",
    consent_in_place: "",
    duration_frequency: "",
  };
}

export function usageContextSearchParams(
  filters: UsageContextSearchFilterState,
): Pick<
  SearchPublicScenariosParams,
  | "children_age_min"
  | "children_age_max"
  | "physically_present"
  | "online_present"
  | "execution_place_affects_scenario"
  | "special_circumstances"
  | "consent_in_place"
  | "duration_frequency"
> {
  const parseAge = (raw: string) => {
    const n = Number(raw);
    return raw.trim() === "" || Number.isNaN(n) ? undefined : n;
  };
  return {
    children_age_min: parseAge(filters.children_age_min),
    children_age_max: parseAge(filters.children_age_max),
    physically_present: filters.physically_present || undefined,
    online_present: filters.online_present || undefined,
    execution_place_affects_scenario: filters.execution_place_affects_scenario || undefined,
    special_circumstances: filters.special_circumstances || undefined,
    consent_in_place: filters.consent_in_place || undefined,
    duration_frequency: filters.duration_frequency || undefined,
  };
}

export function countActiveUsageContextFilters(filters: UsageContextSearchFilterState): number {
  let count = 0;
  if (filters.children_age_min.trim()) count += 1;
  if (filters.children_age_max.trim()) count += 1;
  if (filters.physically_present) count += 1;
  if (filters.online_present) count += 1;
  if (filters.execution_place_affects_scenario) count += 1;
  if (filters.special_circumstances) count += 1;
  if (filters.consent_in_place) count += 1;
  if (filters.duration_frequency) count += 1;
  return count;
}

type Props = {
  value: UsageContextSearchFilterState;
  onChange: (next: UsageContextSearchFilterState) => void;
};

const YES_NO_FIELDS = [
  ["physically_present", "Physically present"],
  ["online_present", "Online present"],
  ["execution_place_affects_scenario", "Place affects scenario"],
  ["special_circumstances", "Special circumstances"],
  ["consent_in_place", "Consent in place"],
] as const;

export function UsageContextSearchFilters({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    const onDocClick = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const set = <K extends keyof UsageContextSearchFilterState>(key: K, v: UsageContextSearchFilterState[K]) => {
    onChange({ ...value, [key]: v });
  };

  const activeCount = countActiveUsageContextFilters(value);
  const triggerText = activeCount === 0 ? "Any usage context" : `Usage context (${activeCount})`;

  return (
    <div className="filter-dropdown" ref={rootRef}>
      <button
        type="button"
        className="filter-dropdown__trigger"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="filter-dropdown__label">Usage context</span>
        <span className="filter-dropdown__chevron" aria-hidden>
          ▾
        </span>
        <span className="filter-dropdown__value">{triggerText}</span>
      </button>
      {open ? (
        <div id={panelId} className="filter-dropdown__panel filter-dropdown__panel--wide" role="dialog" aria-label="Usage context filters">
          <div className="filter-dropdown__panel-head">
            <span className="filter-dropdown__panel-title">Usage context</span>
            {activeCount > 0 ? (
              <button type="button" className="filter-dropdown__clear" onClick={() => onChange(emptyUsageContextSearchFilters())}>
                Clear
              </button>
            ) : null}
          </div>
          <div className="usage-context-filters__grid">
            <label className="usage-context-filters__field">
              <span>Children age from</span>
              <input
                type="number"
                min={0}
                max={17}
                value={value.children_age_min}
                onChange={(e) => set("children_age_min", e.target.value)}
              />
            </label>
            <label className="usage-context-filters__field">
              <span>Children age to</span>
              <input
                type="number"
                min={0}
                max={17}
                value={value.children_age_max}
                onChange={(e) => set("children_age_max", e.target.value)}
              />
            </label>
            <label className="usage-context-filters__field">
              <span>Duration / frequency</span>
              <select
                value={value.duration_frequency}
                onChange={(e) =>
                  set("duration_frequency", e.target.value as UsageContextSearchFilterState["duration_frequency"])
                }
              >
                <option value="">Any</option>
                {USAGE_CONTEXT_DURATION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            {YES_NO_FIELDS.map(([key, label]) => (
              <label key={key} className="usage-context-filters__field">
                <span>{label}</span>
                <select
                  value={value[key]}
                  onChange={(e) => set(key, e.target.value as UsageContextSearchFilterState[typeof key])}
                >
                  <option value="">Any</option>
                  {USAGE_CONTEXT_YES_NO_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
