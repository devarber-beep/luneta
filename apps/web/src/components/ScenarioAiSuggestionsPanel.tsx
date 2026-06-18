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
    <section className="ai-suggestions-panel" aria-labelledby="ai-suggestions-heading">
      <div className="ai-suggestions-panel__header">
        <h3 id="ai-suggestions-heading" className="ai-suggestions-panel__title">
          AI suggestions
        </h3>
        <span className="badge-ai" aria-hidden>
          AI
        </span>
        <button type="button" className="btn" disabled={disabled || loading} onClick={() => onGenerate()}>
          {loading ? "Generating…" : "Suggest improvements"}
        </button>
      </div>
      {items.length === 0 ? (
        <p className="ai-suggestions-panel__hint">No pending AI suggestions. Click Suggest improvements to request a batch.</p>
      ) : (
        <ul className="ai-suggestions-panel__list">
          {items.map((item) => (
            <li key={item.id} className="ai-suggestions-panel__item">
              <div className="ai-suggestions-panel__item-meta">
                {scopeLabel(item)} · {item.kind}
              </div>
              <p className="ai-suggestions-panel__item-text">
                <strong>Why:</strong> {item.rationale}
              </p>
              <p className="ai-suggestions-panel__item-text">
                <strong>Current excerpt:</strong>{" "}
                <span className="ai-suggestions-panel__excerpt">{item.current_excerpt}</span>
              </p>
              <p className="ai-suggestions-panel__item-text">
                <strong>Proposed:</strong>{" "}
                <span className="ai-suggestions-panel__excerpt">{item.proposed_text}</span>
              </p>
              <div className="btn-group">
                <button type="button" className="btn btn--primary" disabled={disabled} onClick={() => onApply(item)}>
                  Apply to form
                </button>
                <button type="button" className="btn btn--ghost" disabled={disabled} onClick={() => onDiscard(item)}>
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
