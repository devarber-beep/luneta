import type { ScenarioUsageContext } from "../api";
import {
  USAGE_CONTEXT_DURATION_OPTIONS,
  USAGE_CONTEXT_YES_NO_OPTIONS,
} from "./usageContextLabels";

export type UsageContextFormState = {
  children_age_start: number | "";
  children_age_end: number | "";
  children_count: number | "";
  children_count_undefined: boolean;
  duration_frequency: ScenarioUsageContext["duration_frequency"] | "";
  physically_present: ScenarioUsageContext["physically_present"] | "";
  online_present: ScenarioUsageContext["online_present"] | "";
  execution_place_affects_scenario: ScenarioUsageContext["execution_place_affects_scenario"] | "";
  special_circumstances: ScenarioUsageContext["special_circumstances"] | "";
  consent_in_place: ScenarioUsageContext["consent_in_place"] | "";
};

export function emptyUsageContextForm(): UsageContextFormState {
  return {
    children_age_start: "",
    children_age_end: "",
    children_count: "",
    children_count_undefined: false,
    duration_frequency: "",
    physically_present: "",
    online_present: "",
    execution_place_affects_scenario: "",
    special_circumstances: "",
    consent_in_place: "",
  };
}

export function usageContextFromScenario(ctx: ScenarioUsageContext | null | undefined): UsageContextFormState {
  if (!ctx) {
    return emptyUsageContextForm();
  }
  return {
    children_age_start: ctx.children_age_start ?? "",
    children_age_end: ctx.children_age_end ?? "",
    children_count: ctx.children_count ?? "",
    children_count_undefined: ctx.children_count == null,
    duration_frequency: ctx.duration_frequency ?? "",
    physically_present: ctx.physically_present ?? "",
    online_present: ctx.online_present ?? "",
    execution_place_affects_scenario: ctx.execution_place_affects_scenario ?? "",
    special_circumstances: ctx.special_circumstances ?? "",
    consent_in_place: ctx.consent_in_place ?? "",
  };
}

export function usageContextFormIsComplete(form: UsageContextFormState): boolean {
  return (
    form.children_age_start !== "" &&
    form.children_age_end !== "" &&
    form.children_age_end >= form.children_age_start &&
    (form.children_count_undefined || form.children_count !== "") &&
    form.duration_frequency !== "" &&
    form.physically_present !== "" &&
    form.online_present !== "" &&
    form.execution_place_affects_scenario !== "" &&
    form.special_circumstances !== "" &&
    form.consent_in_place !== ""
  );
}

export function usageContextToPatch(form: UsageContextFormState): ScenarioUsageContext {
  return {
    children_age_start: form.children_age_start === "" ? null : form.children_age_start,
    children_age_end: form.children_age_end === "" ? null : form.children_age_end,
    children_count: form.children_count_undefined || form.children_count === "" ? null : form.children_count,
    duration_frequency: form.duration_frequency || null,
    physically_present: form.physically_present || null,
    online_present: form.online_present || null,
    execution_place_affects_scenario: form.execution_place_affects_scenario || null,
    special_circumstances: form.special_circumstances || null,
    consent_in_place: form.consent_in_place || null,
  };
}

function YesNoField({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: "" | "yes" | "no";
  onChange: (next: "yes" | "no") => void;
  disabled?: boolean;
}) {
  return (
    <fieldset className="usage-context-form__fieldset" disabled={disabled}>
      <legend className="usage-context-form__legend">{label}</legend>
      <div className="usage-context-form__radios">
        {USAGE_CONTEXT_YES_NO_OPTIONS.map((opt) => (
          <label key={opt.value} className="usage-context-form__radio">
            <input
              type="radio"
              name={label}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              required={value === ""}
              disabled={disabled}
            />
            {opt.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

type Props = {
  value: UsageContextFormState;
  onChange: (next: UsageContextFormState) => void;
  disabled?: boolean;
};

export function ScenarioUsageContextFields({ value, onChange, disabled }: Props) {
  return (
    <div className="usage-context-form usage-context-form--columns">
      <div className="usage-context-form__col">
        <div className="usage-context-form__row--split">
          <label className="form-field">
            <span className="form-field__label">Children age range start</span>
            <input
              type="number"
              min={0}
              max={17}
              step={1}
              required
              disabled={disabled}
              value={value.children_age_start}
              onChange={(e) =>
                onChange({ ...value, children_age_start: e.target.value === "" ? "" : Number(e.target.value) })
              }
              inputMode="numeric"
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Children age range end</span>
            <input
              type="number"
              min={0}
              max={17}
              step={1}
              required
              disabled={disabled}
              value={value.children_age_end}
              onChange={(e) =>
                onChange({ ...value, children_age_end: e.target.value === "" ? "" : Number(e.target.value) })
              }
              inputMode="numeric"
            />
          </label>
        </div>
        <label className="form-field">
          <span className="form-field__label">Number of children</span>
          <input
            type="number"
            min={1}
            max={500}
            required={!value.children_count_undefined}
            disabled={disabled || value.children_count_undefined}
            value={value.children_count}
            onChange={(e) => onChange({ ...value, children_count: e.target.value === "" ? "" : Number(e.target.value) })}
            inputMode="numeric"
          />
          <label className="usage-context-form__checkbox-label">
            <input
              type="checkbox"
              disabled={disabled}
              checked={value.children_count_undefined}
              onChange={(e) =>
                onChange({
                  ...value,
                  children_count_undefined: e.target.checked,
                  children_count: e.target.checked ? "" : value.children_count,
                })
              }
            />
            Undefined
          </label>
        </label>

        <label className="form-field">
          <span className="form-field__label">Duration and frequency</span>
          <select
            required
            disabled={disabled}
            value={value.duration_frequency}
            onChange={(e) =>
              onChange({
                ...value,
                duration_frequency: e.target.value as UsageContextFormState["duration_frequency"],
              })
            }
          >
            <option value="" disabled>
              Select an option
            </option>
            {USAGE_CONTEXT_DURATION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="usage-context-form__col">
        <YesNoField
          label="Is anyone physically present during the session?"
          value={value.physically_present}
          onChange={(next) => onChange({ ...value, physically_present: next })}
          disabled={disabled}
        />
        <YesNoField
          label="Is anyone present online during the session?"
          value={value.online_present}
          onChange={(next) => onChange({ ...value, online_present: next })}
          disabled={disabled}
        />
        <YesNoField
          label="Does the execution place affect the scenario?"
          value={value.execution_place_affects_scenario}
          onChange={(next) => onChange({ ...value, execution_place_affects_scenario: next })}
          disabled={disabled}
        />
        <YesNoField
          label="Are there special circumstances for the child?"
          value={value.special_circumstances}
          onChange={(next) => onChange({ ...value, special_circumstances: next })}
          disabled={disabled}
        />
        <YesNoField
          label="Is consent in place for this scenario?"
          value={value.consent_in_place}
          onChange={(next) => onChange({ ...value, consent_in_place: next })}
          disabled={disabled}
        />
      </div>
    </div>
  );
}
