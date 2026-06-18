import { type FormEvent, useId } from "react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  label?: string;
  placeholder?: string;
};

export function ScenarioSearchField({
  value,
  onChange,
  onSubmit,
  label = "Search scenarios",
  placeholder,
}: Props) {
  const inputId = useId();

  const onFormSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form onSubmit={onFormSubmit} className="search-form" role="search">
      <label htmlFor={inputId} className="sr-only">
        {label}
      </label>
      <input
        id={inputId}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
      />
      <button type="submit" className="btn btn--primary">
        Search
      </button>
    </form>
  );
}
