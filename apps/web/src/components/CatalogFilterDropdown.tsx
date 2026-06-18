import { useEffect, useId, useRef, useState } from "react";

export type CatalogFilterOption = {
  id: string;
  label: string;
};

type Props = {
  label: string;
  options: CatalogFilterOption[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  emptyLabel?: string;
  disabled?: boolean;
};

export function CatalogFilterDropdown({
  label,
  options,
  selectedIds,
  onChange,
  emptyLabel = "All",
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

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

  const selectedLabels = options.filter((o) => selectedIds.includes(o.id)).map((o) => o.label);
  const triggerText =
    selectedIds.length === 0
      ? emptyLabel
      : selectedIds.length === 1
        ? selectedLabels[0]
        : `${label} (${selectedIds.length})`;

  const toggle = (id: string, checked: boolean) => {
    onChange(checked ? [...selectedIds, id] : selectedIds.filter((x) => x !== id));
  };

  const clearAll = () => onChange([]);

  return (
    <div className="filter-dropdown" ref={rootRef}>
      <button
        type="button"
        className="filter-dropdown__trigger"
        disabled={disabled || !options.length}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listId}
        aria-label={`${label}: ${triggerText}`}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="filter-dropdown__label">{label}</span>
        <span className="filter-dropdown__chevron" aria-hidden>
          ▾
        </span>
        <span className="filter-dropdown__value">{triggerText}</span>
      </button>
      {open ? (
        <div id={listId} role="listbox" aria-multiselectable className="filter-dropdown__panel">
          <div className="filter-dropdown__panel-head">
            <span className="filter-dropdown__panel-title">{label}</span>
            {selectedIds.length ? (
              <button type="button" className="filter-dropdown__clear" onClick={clearAll}>
                Clear
              </button>
            ) : null}
          </div>
          <div className="filter-dropdown__options">
            {options.map((opt) => (
              <label key={opt.id} className="filter-dropdown__option">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(opt.id)}
                  onChange={(e) => toggle(opt.id, e.target.checked)}
                />
                <span>{opt.label}</span>
              </label>
            ))}
            {!options.length ? <p className="filter-dropdown__empty">No options.</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
