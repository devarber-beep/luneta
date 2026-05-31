import { useEffect, useId, useRef, useState, type CSSProperties } from "react";

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
    <div ref={rootRef} style={{ position: "relative", minWidth: "200px" }}>
      <button
        type="button"
        disabled={disabled || !options.length}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
        style={triggerStyle}
      >
        <span style={{ fontSize: "0.8rem", color: "#555", gridColumn: "1 / 2" }}>{label}</span>
        <span aria-hidden style={{ gridColumn: "2 / 3", gridRow: "1 / 3", color: "#666" }}>
          ▾
        </span>
        <span style={{ fontWeight: 500, gridColumn: "1 / 2" }}>{triggerText}</span>
      </button>
      {open ? (
        <div id={listId} role="listbox" aria-multiselectable style={panelStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.35rem" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>{label}</span>
            {selectedIds.length ? (
              <button type="button" onClick={clearAll} style={linkBtnStyle}>
                Clear
              </button>
            ) : null}
          </div>
          <div style={{ maxHeight: "11rem", overflowY: "auto" }}>
            {options.map((opt) => (
              <label key={opt.id} style={optionStyle}>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(opt.id)}
                  onChange={(e) => toggle(opt.id, e.target.checked)}
                />
                <span>{opt.label}</span>
              </label>
            ))}
            {!options.length ? <p style={{ margin: 0, fontSize: "0.85rem", color: "#777" }}>No options.</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

const triggerStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr auto",
  gridTemplateRows: "auto auto",
  columnGap: "0.5rem",
  alignItems: "center",
  width: "100%",
  minWidth: "200px",
  padding: "0.45rem 0.65rem",
  borderRadius: "6px",
  border: "1px solid #dadce0",
  background: "#fff",
  cursor: "pointer",
  textAlign: "left",
};

const panelStyle: CSSProperties = {
  position: "absolute",
  top: "calc(100% + 4px)",
  left: 0,
  zIndex: 20,
  minWidth: "100%",
  maxWidth: "320px",
  padding: "0.5rem 0.65rem",
  background: "#fff",
  border: "1px solid #dadce0",
  borderRadius: "8px",
  boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
};

const optionStyle: CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  gap: "0.4rem",
  fontSize: "0.85rem",
  marginBottom: "0.3rem",
  cursor: "pointer",
};

const linkBtnStyle: CSSProperties = {
  border: "none",
  background: "none",
  color: "#1a73e8",
  fontSize: "0.78rem",
  cursor: "pointer",
  padding: 0,
};
