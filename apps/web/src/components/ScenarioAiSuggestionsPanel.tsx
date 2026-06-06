import { useState } from "react";
import {
  ContentPolicyError,
  discardAiSuggestion,
  generateAiSuggestions,
  recordAiSuggestionApplied,
  recordAiSuggestionApplyFailed,
  type AiSuggestionItem,
} from "../api";
import { applyAiSuggestionToDraft } from "./applyAiSuggestion";
import {
  aiApplySuccessMessage,
  aiDiscardSuccessMessage,
  aiGenerateEmptyMessage,
  aiGenerateSuccessMessage,
  aiRegenerateConfirmMessage,
} from "./aiSuggestionMessages";
import type { AiGenerateEmptyReason } from "../api";

const panelStyle = {
  marginBottom: "1.25rem",
  padding: "1rem",
  background: "#f3f6fc",
  border: "1px solid #c5d4f7",
  borderRadius: "8px",
} as const;

const itemStyle = {
  marginTop: "0.75rem",
  padding: "0.75rem",
  background: "#fff",
  border: "1px solid #dde3f0",
  borderRadius: "6px",
} as const;

type Props = {
  token: string;
  scenarioId: string;
  disabled?: boolean;
  title: string;
  description: string;
  onApplyToForm: (next: { title?: string; description?: string }) => void;
  onStatusMessage: (message: string) => void;
  onSensitiveBlocked?: (error: ContentPolicyError) => void;
};

function scopeLabel(item: AiSuggestionItem): string {
  if (item.scope === "title") return "Title";
  if (item.scope === "description_full") return "Description (full)";
  return `Description (paragraph ${(item.paragraph_index ?? 0) + 1})`;
}

export function ScenarioAiSuggestionsPanel({
  token,
  scenarioId,
  disabled,
  title,
  description,
  onApplyToForm,
  onStatusMessage,
  onSensitiveBlocked,
}: Props) {
  const [requestId, setRequestId] = useState<string | null>(null);
  const [items, setItems] = useState<AiSuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [pendingSaveHint, setPendingSaveHint] = useState(false);

  const onGenerate = async () => {
    if (items.length > 0) {
      const ok = window.confirm(aiRegenerateConfirmMessage());
      if (!ok) return;
    }
    setLoading(true);
    try {
      const res = await generateAiSuggestions(token, scenarioId, {
        title,
        description,
      });
      setRequestId(res.request_id);
      setItems(res.items);
      if (res.items.length === 0) {
        onStatusMessage(
          aiGenerateEmptyMessage(
            res.empty_reason ?? (res.raw_items_received ? "filtered" : "model_empty"),
            res.raw_items_received ?? 0,
            res.items_filtered_out ?? 0,
          ),
        );
      } else {
        onStatusMessage(aiGenerateSuccessMessage(res.items.length));
      }
    } catch (error) {
      if (error instanceof ContentPolicyError) {
        onSensitiveBlocked?.(error);
      } else {
        onStatusMessage((error as Error).message);
      }
    } finally {
      setLoading(false);
    }
  };

  const onApply = async (item: AiSuggestionItem) => {
    if (!requestId) return;
    const result = applyAiSuggestionToDraft(item, { title, description });
    onApplyToForm({ title: result.title, description: result.description });
    setPendingSaveHint(true);
    const actionPayload = {
      request_id: requestId,
      scope: item.scope,
      kind: item.kind,
      paragraph_index: item.paragraph_index,
      current_excerpt: item.current_excerpt,
      proposed_text: item.proposed_text,
      rationale: item.rationale,
    };
    try {
      if (result.excerptFound) {
        await recordAiSuggestionApplied(token, scenarioId, item.id, actionPayload);
      } else {
        await recordAiSuggestionApplyFailed(token, scenarioId, item.id, actionPayload);
      }
      setItems((prev) => prev.filter((row) => row.id !== item.id));
      onStatusMessage(aiApplySuccessMessage(result.excerptFound));
    } catch (error) {
      onStatusMessage(
        `Could not record this action on the server: ${(error as Error).message}. ` +
          "Your form may still have been updated — save the draft if you want to keep it.",
      );
    }
  };

  const onDiscard = async (item: AiSuggestionItem) => {
    if (!requestId) return;
    try {
      await discardAiSuggestion(token, scenarioId, item.id, {
        request_id: requestId,
        scope: item.scope,
        kind: item.kind,
        paragraph_index: item.paragraph_index,
        current_excerpt: item.current_excerpt,
        proposed_text: item.proposed_text,
        rationale: item.rationale,
      });
      setItems((prev) => prev.filter((row) => row.id !== item.id));
      onStatusMessage(aiDiscardSuccessMessage());
    } catch (error) {
      onStatusMessage(`Could not discard this suggestion: ${(error as Error).message}`);
    }
  };

  return (
    <section style={panelStyle} aria-labelledby="ai-suggestions-heading">
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
        <h3 id="ai-suggestions-heading" style={{ margin: 0, flex: "1 1 auto" }}>
          AI suggestions
        </h3>
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            padding: "0.15rem 0.45rem",
            borderRadius: "4px",
            background: "#1a73e8",
            color: "#fff",
          }}
        >
          AI
        </span>
        <button type="button" disabled={disabled || loading} onClick={() => onGenerate()}>
          {loading ? "Generating…" : "Suggest improvements"}
        </button>
      </div>
      <p style={{ margin: "0.5rem 0 0", fontSize: "0.88rem", color: "#444", lineHeight: 1.45 }}>
        Optional AI help for the scenario owner (not reviewer suggestions). Up to 5 suggestions per
        batch; up to 5 generations per hour. Apply copies text into the form only — use Save draft
        to persist.
      </p>
      {pendingSaveHint ? (
        <p style={{ margin: "0.5rem 0 0", fontSize: "0.88rem", color: "#b06000", fontWeight: 600 }}>
          You have applied AI changes in the form that are not saved yet — click Save draft to
          persist them.
        </p>
      ) : null}
      {items.length === 0 ? (
        <p style={{ margin: "0.65rem 0 0", fontSize: "0.85rem", color: "#666" }}>
          No pending AI suggestions. Click Suggest improvements to request a batch.
        </p>
      ) : (
        <ul style={{ listStyle: "none", margin: "0.5rem 0 0", padding: 0 }}>
          {items.map((item) => (
            <li key={item.id} style={itemStyle}>
              <div style={{ fontSize: "0.8rem", color: "#555", marginBottom: "0.35rem" }}>
                {scopeLabel(item)} · {item.kind}
              </div>
              <p style={{ margin: "0 0 0.35rem", fontSize: "0.88rem" }}>
                <strong>Why:</strong> {item.rationale}
              </p>
              <p style={{ margin: "0 0 0.35rem", fontSize: "0.85rem", color: "#333" }}>
                <strong>Current excerpt:</strong>{" "}
                <span style={{ fontFamily: "monospace", whiteSpace: "pre-wrap" }}>{item.current_excerpt}</span>
              </p>
              <p style={{ margin: "0 0 0.5rem", fontSize: "0.85rem", color: "#333" }}>
                <strong>Proposed:</strong>{" "}
                <span style={{ fontFamily: "monospace", whiteSpace: "pre-wrap" }}>{item.proposed_text}</span>
              </p>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <button type="button" disabled={disabled} onClick={() => onApply(item)}>
                  Apply to form
                </button>
                <button type="button" disabled={disabled} onClick={() => onDiscard(item)}>
                  Discard
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
