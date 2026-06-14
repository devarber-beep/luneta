import { useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  acceptScenarioSuggestion,
  applyAcceptedSuggestionText,
  createScenarioSuggestion,
  rejectScenarioSuggestion,
  type SuggestionItem,
} from "../api";
import { splitDescriptionParagraphs } from "../domain/descriptionParagraphs";
import { getToken } from "../session";

export { splitDescriptionParagraphs } from "../domain/descriptionParagraphs";

type Props = {
  scenarioId: string;
  description: string;
  suggestions: SuggestionItem[];
  canSuggest: boolean;
  canViewSuggestions: boolean;
  canResolve: boolean;
  canApplyAcceptedText?: boolean;
  /** Editable textarea instead of read-only paragraphs (owner editing working copy). */
  canEditDescription?: boolean;
  descriptionDisabled?: boolean;
  onDescriptionChange?: (value: string) => void;
  /** Only suggestion actions (use below an editable description field). */
  notesOnly?: boolean;
  /** On published scenarios, paragraph suggestions are alternative text only. */
  publishedParagraphAltTextOnly?: boolean;
  onSuggestionSubmitted?: () => void;
  onScenarioUpdated?: () => void;
};

export function DescriptionWithSuggestions({
  scenarioId,
  description,
  suggestions,
  canSuggest,
  canViewSuggestions,
  canResolve,
  canApplyAcceptedText = false,
  canEditDescription = false,
  descriptionDisabled = false,
  onDescriptionChange,
  notesOnly = false,
  publishedParagraphAltTextOnly = false,
  onSuggestionSubmitted,
  onScenarioUpdated,
}: Props) {
  const paragraphs = useMemo(() => splitDescriptionParagraphs(description), [description]);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [activeParagraph, setActiveParagraph] = useState<number | "scenario" | null>(null);
  const [draftBody, setDraftBody] = useState("");
  const [draftKind, setDraftKind] = useState<"comment" | "alternative_text">("comment");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const scenarioSuggestions = suggestions.filter((s) => s.scope === "scenario");
  const byParagraph = (index: number) =>
    suggestions.filter((s) => s.scope === "paragraph" && s.paragraph_index === index);

  const defaultParagraphKind = publishedParagraphAltTextOnly ? "alternative_text" : "comment";

  const paragraphTextForIndex = (index: number) => paragraphs[index] ?? "";

  const initialBodyForParagraphSuggestion = (
    index: number,
    kind: "comment" | "alternative_text",
  ) => (kind === "alternative_text" ? paragraphTextForIndex(index) : "");

  const openParagraphSuggestion = (index: number) => {
    const kind = defaultParagraphKind;
    setActiveParagraph(index);
    setDraftKind(kind);
    setDraftBody(initialBodyForParagraphSuggestion(index, kind));
  };

  const closeComposer = () => {
    setActiveParagraph(null);
    setDraftBody("");
    setDraftKind(defaultParagraphKind);
  };

  useEffect(() => {
    if (!canSuggest) {
      closeComposer();
      setHoveredIndex(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canSuggest]);

  const submitSuggestion = async () => {
    const token = getToken();
    if (!token || !draftBody.trim() || activeParagraph === null) return;
    setBusy(true);
    try {
      const scope = activeParagraph === "scenario" ? "scenario" : "paragraph";
      const kind =
        scope === "scenario"
          ? "comment"
          : publishedParagraphAltTextOnly
            ? "alternative_text"
            : draftKind;
      await createScenarioSuggestion(token, scenarioId, {
        scope,
        kind,
        paragraph_index: scope === "paragraph" ? activeParagraph : null,
        body: draftBody.trim(),
      });
      setMessage("Suggestion submitted.");
      closeComposer();
      onSuggestionSubmitted?.();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const applyText = async (suggestionId: string) => {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    try {
      await applyAcceptedSuggestionText(token, scenarioId, suggestionId);
      onScenarioUpdated?.();
      setMessage("Alternative text applied to the scenario.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const resolve = async (suggestionId: string, action: "accept" | "reject") => {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    try {
      if (action === "accept") {
        await acceptScenarioSuggestion(token, scenarioId, suggestionId);
      } else {
        await rejectScenarioSuggestion(token, scenarioId, suggestionId);
      }
      onScenarioUpdated?.();
      setMessage(action === "accept" ? "Suggestion accepted." : "Suggestion rejected.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (notesOnly) {
    if (!canViewSuggestions || !suggestions.length) {
      return null;
    }
    return (
      <div style={{ marginTop: "0.75rem" }}>
        {suggestions.map((s) => (
          <div key={s.id} style={{ marginBottom: "0.5rem" }}>
            <MarginNote
              suggestion={s}
              canResolve={canResolve}
              onAccept={() => resolve(s.id, "accept")}
              onReject={() => resolve(s.id, "reject")}
              onApply={() => applyText(s.id)}
              canApplyAcceptedText={canApplyAcceptedText}
              busy={busy}
            />
          </div>
        ))}
        {message ? (
          <p role="status" style={{ fontSize: "0.9rem", marginTop: "0.5rem", color: "#1b5e20" }}>
            {message}
          </p>
        ) : null}
      </div>
    );
  }

  if (canEditDescription) {
    return (
      <div>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange?.(e.target.value)}
          rows={8}
          disabled={descriptionDisabled}
          required
          style={{ width: "100%", marginBottom: canViewSuggestions && suggestions.length ? "0.5rem" : 0 }}
        />
        {canViewSuggestions && suggestions.length > 0 ? (
          <div>
            {suggestions.map((s) => (
              <div key={s.id} style={{ marginBottom: "0.5rem" }}>
                <MarginNote
                  suggestion={s}
                  canResolve={canResolve}
                  onAccept={() => resolve(s.id, "accept")}
                  onReject={() => resolve(s.id, "reject")}
                  onApply={() => applyText(s.id)}
                  canApplyAcceptedText={canApplyAcceptedText}
                  busy={busy}
                />
              </div>
            ))}
          </div>
        ) : null}
        {message ? (
          <p role="status" style={{ fontSize: "0.9rem", marginTop: "0.5rem", color: "#1b5e20" }}>
            {message}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div>
      {canSuggest ? (
        <div style={{ marginBottom: "0.75rem" }}>
          <button
            type="button"
            onClick={() => {
              setActiveParagraph("scenario");
              setDraftKind("comment");
              setDraftBody("");
            }}
            style={floatingBtnStyle}
          >
            Suggest on whole scenario
          </button>
        </div>
      ) : null}

      {canViewSuggestions && scenarioSuggestions.length > 0 ? (
        <div style={{ marginBottom: "1rem" }}>
          {scenarioSuggestions.map((s) => (
            <MarginNote
              key={s.id}
              suggestion={s}
              canResolve={canResolve}
              onAccept={() => resolve(s.id, "accept")}
              onReject={() => resolve(s.id, "reject")}
              onApply={() => applyText(s.id)}
              canApplyAcceptedText={canApplyAcceptedText}
              busy={busy}
            />
          ))}
        </div>
      ) : null}

      {paragraphs.length === 0 ? (
        <p style={{ color: "#666", fontStyle: "italic" }}>No paragraphs yet. Add text separated by blank lines.</p>
      ) : (
        paragraphs.map((text, index) => (
          <div
            key={index}
            style={{
              display: "grid",
              gridTemplateColumns: canViewSuggestions ? "1fr minmax(140px, 28%)" : "1fr",
              gap: "0.75rem",
              marginBottom: "1rem",
              alignItems: "start",
            }}
          >
            <div
              style={{
                position: "relative",
                padding: "0.65rem 0.75rem",
                borderRadius: "6px",
                background: hoveredIndex === index && canSuggest ? "rgba(66, 133, 244, 0.08)" : "transparent",
                outline: hoveredIndex === index && canSuggest ? "1px solid rgba(66, 133, 244, 0.35)" : "none",
                transition: "background 0.15s ease, outline 0.15s ease",
              }}
              onMouseEnter={() => canSuggest && setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.55 }}>{text}</p>
              {canSuggest && hoveredIndex === index ? (
                <button
                  type="button"
                  style={{
                    ...floatingBtnStyle,
                    position: "absolute",
                    top: "0.5rem",
                    right: "0.5rem",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
                  }}
                  onClick={() => openParagraphSuggestion(index)}
                >
                  Suggest
                </button>
              ) : null}
            </div>
            {canViewSuggestions ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {byParagraph(index).map((s) => (
                  <MarginNote
                    key={s.id}
                    suggestion={s}
                    canResolve={canResolve}
                    onAccept={() => resolve(s.id, "accept")}
                    onReject={() => resolve(s.id, "reject")}
                    onApply={() => applyText(s.id)}
                    canApplyAcceptedText={canApplyAcceptedText}
                    busy={busy}
                  />
                ))}
              </div>
            ) : null}
          </div>
        ))
      )}

      {activeParagraph !== null ? (
        <Composer
          label={
            activeParagraph === "scenario"
              ? "Suggestion on whole scenario"
              : `Suggestion on paragraph ${activeParagraph + 1}`
          }
          body={draftBody}
          kind={draftKind}
          allowKindChoice={activeParagraph !== "scenario" && !publishedParagraphAltTextOnly}
          busy={busy}
          onBody={setDraftBody}
          onKind={(nextKind) => {
            setDraftKind(nextKind);
            if (typeof activeParagraph === "number") {
              if (nextKind === "alternative_text") {
                setDraftBody(paragraphTextForIndex(activeParagraph));
              } else {
                setDraftBody("");
              }
            }
          }}
          onCancel={closeComposer}
          onSubmit={submitSuggestion}
        />
      ) : null}

      {message ? (
        <p
          role="status"
          style={{
            fontSize: "0.9rem",
            marginTop: "0.75rem",
            padding: "0.5rem 0.65rem",
            borderRadius: "6px",
            background: message.toLowerCase().includes("error") || message.includes("failed")
              ? "#fdecea"
              : "#e8f5e9",
            color: message.toLowerCase().includes("error") || message.includes("failed") ? "#b3261e" : "#1b5e20",
          }}
        >
          {message}
        </p>
      ) : null}
    </div>
  );
}

const floatingBtnStyle: CSSProperties = {
  fontSize: "0.8rem",
  padding: "0.35rem 0.65rem",
  borderRadius: "999px",
  border: "1px solid #1a73e8",
  background: "#fff",
  color: "#1a73e8",
  cursor: "pointer",
};

function MarginNote({
  suggestion: s,
  canResolve,
  canApplyAcceptedText,
  onAccept,
  onReject,
  onApply,
  busy,
}: {
  suggestion: SuggestionItem;
  canResolve: boolean;
  canApplyAcceptedText: boolean;
  onAccept: () => void;
  onReject: () => void;
  onApply: () => void;
  busy: boolean;
}) {
  const showApply =
    canApplyAcceptedText &&
    s.status === "accepted" &&
    s.kind === "alternative_text" &&
    !s.applied_at;
  const statusColor =
    s.status === "pending" ? "#b8860b" : s.status === "accepted" ? "#2e7d32" : "#9e9e9e";
  return (
    <aside
      style={{
        background: "#fffde7",
        border: "1px solid #f0e68c",
        borderLeft: `4px solid ${statusColor}`,
        borderRadius: "4px",
        padding: "0.5rem 0.6rem",
        fontSize: "0.82rem",
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
        {s.kind === "alternative_text" ? "Alt. text" : "Comment"} · {s.status}
      </div>
      <p style={{ margin: "0 0 0.35rem", whiteSpace: "pre-wrap", lineHeight: 1.4 }}>{s.body}</p>
      {canResolve && s.status === "pending" ? (
        <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
          <button type="button" disabled={busy} onClick={onAccept} style={{ fontSize: "0.75rem" }}>
            Accept
          </button>
          <button type="button" disabled={busy} onClick={onReject} style={{ fontSize: "0.75rem" }}>
            Reject
          </button>
        </div>
      ) : null}
      {showApply ? (
        <button type="button" disabled={busy} onClick={onApply} style={{ fontSize: "0.75rem", marginTop: "0.25rem" }}>
          Apply
        </button>
      ) : null}
      {s.applied_at ? (
        <p style={{ margin: "0.25rem 0 0", fontSize: "0.72rem", color: "#666" }}>Applied</p>
      ) : null}
    </aside>
  );
}

function Composer({
  label,
  body,
  kind,
  allowKindChoice,
  busy,
  onBody,
  onKind,
  onCancel,
  onSubmit,
}: {
  label: string;
  body: string;
  kind: "comment" | "alternative_text";
  allowKindChoice: boolean;
  busy: boolean;
  onBody: (v: string) => void;
  onKind: (k: "comment" | "alternative_text") => void;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  return (
    <div
      style={{
        marginTop: "1rem",
        padding: "1rem",
        border: "1px solid #c5d9f7",
        borderRadius: "8px",
        background: "#f8fbff",
      }}
    >
      <strong style={{ display: "block", marginBottom: "0.5rem" }}>{label}</strong>
      {allowKindChoice ? (
        <label style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.9rem" }}>
          Type{" "}
          <select value={kind} onChange={(e) => onKind(e.target.value as "comment" | "alternative_text")}>
            <option value="comment">Comment</option>
            <option value="alternative_text">Alternative text</option>
          </select>
        </label>
      ) : null}
      <textarea
        value={body}
        onChange={(e) => onBody(e.target.value)}
        rows={4}
        placeholder={
          kind === "alternative_text"
            ? "Edit the paragraph text and submit your proposed version…"
            : "Your comment…"
        }
        style={{ width: "100%", marginBottom: "0.5rem" }}
      />
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" disabled={busy || !body.trim()} onClick={onSubmit}>
          {busy ? "Sending…" : "Submit"}
        </button>
        <button type="button" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
