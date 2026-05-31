import { type FormEvent } from "react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
};

export function ScenarioSearchField({ value, onChange, onSubmit, placeholder }: Props) {
  const onFormSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form
      onSubmit={onFormSubmit}
      style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}
    >
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? "Search scenarios"}
        style={{ flex: "1", minWidth: "220px" }}
      />
      <button type="submit">Search</button>
    </form>
  );
}
