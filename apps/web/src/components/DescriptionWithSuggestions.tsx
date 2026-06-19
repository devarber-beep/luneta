import { useEffect, useMemo, useState } from "react";
import {
  acceptScenarioSuggestion,
  applyAcceptedSuggestionText,
  createScenarioSuggestion,
  rejectScenarioSuggestion,
  type SuggestionItem,
} from "../api";
import { splitDescriptionParagraphs } from "../domain/descriptionParagraphs";
import { getToken } from "../session";
import { StatusMessage } from "./StatusMessage";

export { splitDescriptionParagraphs } from "../domain/descriptionParagraphs";

function suggestionStatusFeedback(message: string) {
  if (message === "Suggestion submitted.") {
    return { variant: "success" as const, presentation: "modal" as const, title: "Suggestion submitted" };
  }
  if (message === "Suggestion accepted.") {
    return { variant: "success" as const, presentation: "modal" as const, title: "Suggestion accepted" };
  }
  if (message === "Suggestion rejected.") {
    return { variant: "success" as const, presentation: "modal" as const, title: "Suggestion rejected" };
  }
  if (message === "Alternative text applied to the scenario.") {
    return {
      variant: "success" as const,
      presentation: "modal" as const,
      title: "Alternative text applied",
    };
  }
  return { variant: undefined, presentation: "auto" as const, title: undefined };
}

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
  /** Hide accepted and rejected suggestions (e.g. on published public view). */
  hideResolvedSuggestions?: boolean;
  onSuggestionSubmitted?: () => void;
  onScenarioUpdated?: () => void;
  onSuggestionAccepted?: (result: {
    suggestion: SuggestionItem;
    scenario: { state: string; description?: string; can_start_editing_working_copy?: boolean };
  }) => void | Promise<void>;
  onSuggestionApplied?: (result: {
    suggestion: SuggestionItem;
    scenario: { description?: string };
  }) => void | Promise<void>;
  onEnsureReadyToApply?: () => void | Promise<void>;
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
  hideResolvedSuggestions = false,
  onSuggestionSubmitted,
  onScenarioUpdated,
  onSuggestionAccepted,
  onSuggestionApplied,
  onEnsureReadyToApply,
}: Props) {
  const paragraphs = useMemo(() => splitDescriptionParagraphs(description), [description]);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [activeParagraph, setActiveParagraph] = useState<number | "scenario" | null>(null);
  const [draftBody, setDraftBody] = useState("");
  const [draftKind, setDraftKind] = useState<"comment" | "alternative_text">("comment");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const shouldHideResolved = hideResolvedSuggestions || publishedParagraphAltTextOnly;
  const visibleSuggestions = useMemo(
    () => (shouldHideResolved ? suggestions.filter((s) => s.status === "pending") : suggestions),
    [suggestions, shouldHideResolved],
  );

  const scenarioSuggestions = visibleSuggestions.filter((s) => s.scope === "scenario");
  const byParagraph = (index: number) =>
    visibleSuggestions.filter((s) => s.scope === "paragraph" && s.paragraph_index === index);

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
      await onEnsureReadyToApply?.();
      const result = await applyAcceptedSuggestionText(token, scenarioId, suggestionId);
      if (onSuggestionApplied) {
        await onSuggestionApplied(result);
      } else {
        onScenarioUpdated?.();
      }
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
        const result = await acceptScenarioSuggestion(token, scenarioId, suggestionId);
        if (onSuggestionAccepted) {
          await onSuggestionAccepted(result);
        } else {
          onScenarioUpdated?.();
        }
      } else {
        await rejectScenarioSuggestion(token, scenarioId, suggestionId);
        onScenarioUpdated?.();
      }
      setMessage(action === "accept" ? "Suggestion accepted." : "Suggestion rejected.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (notesOnly) {
    if (!canViewSuggestions || !visibleSuggestions.length) {
      return null;
    }
    return (
      <div className="suggestion-notes">
        {visibleSuggestions.map((s) => (
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
        <StatusMessage
          message={message}
          {...suggestionStatusFeedback(message)}
          onDismiss={() => setMessage("")}
        />
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
          style={{ width: "100%", marginBottom: canViewSuggestions && visibleSuggestions.length ? "0.5rem" : 0 }}
        />
        {canViewSuggestions && visibleSuggestions.length > 0 ? (
          <div className="suggestion-notes">
            {visibleSuggestions.map((s) => (
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
        <StatusMessage
          message={message}
          {...suggestionStatusFeedback(message)}
          onDismiss={() => setMessage("")}
        />
      </div>
    );
  }

  return (
    <div>
      {canSuggest ? (
        <div className="description-with-suggestions__toolbar">
          <button
            type="button"
            className="btn btn--suggest-floating"
            onClick={() => {
              setActiveParagraph("scenario");
              setDraftKind("comment");
              setDraftBody("");
            }}
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
        <p className="scenario-description scenario-description--empty">No paragraphs yet. Add text separated by blank lines.</p>
      ) : (
        paragraphs.map((text, index) => (
          <div
            key={index}
            className={`description-with-suggestions__row${canViewSuggestions ? " description-with-suggestions__row--with-notes" : ""}`}
          >
            <div
              className={`description-with-suggestions__paragraph${hoveredIndex === index && canSuggest ? " description-with-suggestions__paragraph--hover" : ""}`}
              onMouseEnter={() => canSuggest && setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <p className="scenario-description__paragraph">{text}</p>
              {canSuggest && hoveredIndex === index ? (
                <button
                  type="button"
                  className="btn btn--suggest-floating"
                  onClick={() => openParagraphSuggestion(index)}
                >
                  Suggest
                </button>
              ) : null}
            </div>
            {canViewSuggestions ? (
              <div className="suggestion-notes suggestion-notes--inline">
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

      <StatusMessage
        message={message}
        {...suggestionStatusFeedback(message)}
        onDismiss={() => setMessage("")}
      />
    </div>
  );
}

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
    (canApplyAcceptedText || canResolve) &&
    s.status === "accepted" &&
    s.kind === "alternative_text" &&
    !s.applied_at;
  const statusClass =
    s.status === "pending" ? "suggestion-note--pending" : s.status === "accepted" ? "suggestion-note--accepted" : "suggestion-note--rejected";
  return (
    <aside className={`suggestion-note ${statusClass}`}>
      <div className="suggestion-note__header">
        {s.kind === "alternative_text" ? "Alt. text" : "Comment"} · {s.status}
      </div>
      <p className="suggestion-note__body">{s.body}</p>
      {canResolve && s.status === "pending" ? (
        <div className="suggestion-note__actions">
          <button type="button" className="btn btn--small" disabled={busy} onClick={onAccept}>
            Accept
          </button>
          <button type="button" className="btn btn--small" disabled={busy} onClick={onReject}>
            Reject
          </button>
        </div>
      ) : null}
      {showApply ? (
        <div className="suggestion-note__actions">
          <button type="button" className="btn btn--small" disabled={busy} onClick={onApply}>
            Apply
          </button>
        </div>
      ) : null}
      {s.applied_at ? <p className="suggestion-note__meta">Applied</p> : null}
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
