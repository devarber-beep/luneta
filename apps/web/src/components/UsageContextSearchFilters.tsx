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



const labelStyle = { display: "grid", gap: "0.25rem", fontSize: "0.9rem" } as const;



export function UsageContextSearchFilters({ value, onChange }: Props) {

  const set = <K extends keyof UsageContextSearchFilterState>(key: K, v: UsageContextSearchFilterState[K]) => {

    onChange({ ...value, [key]: v });

  };



  const activeCount = countActiveUsageContextFilters(value);

  const summaryLabel =

    activeCount === 0 ? "Any usage context" : `Usage context (${activeCount})`;



  return (

    <details

      style={{

        minWidth: "200px",

        border: "1px solid #dadce0",

        borderRadius: "6px",

        background: "#fff",

      }}

    >

      <summary

        style={{

          display: "grid",

          gridTemplateColumns: "1fr auto",

          gridTemplateRows: "auto auto",

          columnGap: "0.5rem",

          alignItems: "center",

          padding: "0.45rem 0.65rem",

          cursor: "pointer",

          listStyle: "none",

        }}

      >

        <span style={{ fontSize: "0.8rem", color: "#555" }}>Usage context</span>

        <span aria-hidden style={{ gridColumn: "2 / 3", gridRow: "1 / 3", color: "#666" }}>

          ▾

        </span>

        <span style={{ fontWeight: 500 }}>{summaryLabel}</span>

      </summary>

      <div

        style={{

          display: "grid",

          gap: "0.75rem",

          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",

          padding: "0.65rem 0.75rem 0.85rem",

          borderTop: "1px solid #eee",

          background: "#fafafa",

        }}

      >

        <label style={labelStyle}>

          <span>Children age from</span>

          <input

            type="number"

            min={0}

            max={17}

            value={value.children_age_min}

            onChange={(e) => set("children_age_min", e.target.value)}

          />

        </label>

        <label style={labelStyle}>

          <span>Children age to</span>

          <input

            type="number"

            min={0}

            max={17}

            value={value.children_age_max}

            onChange={(e) => set("children_age_max", e.target.value)}

          />

        </label>

        <label style={labelStyle}>

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

        {(

          [

            ["physically_present", "Physically present"],

            ["online_present", "Online present"],

            ["execution_place_affects_scenario", "Place affects scenario"],

            ["special_circumstances", "Special circumstances"],

            ["consent_in_place", "Consent in place"],

          ] as const

        ).map(([key, label]) => (

          <label key={key} style={labelStyle}>

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

        {activeCount ? (

          <div style={{ gridColumn: "1 / -1" }}>

            <button

              type="button"

              onClick={() => onChange(emptyUsageContextSearchFilters())}

              style={{

                border: "none",

                background: "none",

                color: "#1a73e8",

                fontSize: "0.78rem",

                cursor: "pointer",

                padding: 0,

              }}

            >

              Clear usage context filters

            </button>

          </div>

        ) : null}

      </div>

    </details>

  );

}

