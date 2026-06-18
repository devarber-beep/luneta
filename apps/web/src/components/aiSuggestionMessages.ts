export type AiGenerateEmptyReason = "none" | "model_empty" | "filtered";

export function aiGenerateEmptyMessage(
  emptyReason: AiGenerateEmptyReason,
  rawItemsReceived: number,
  itemsFilteredOut: number,
): string {
  if (emptyReason === "model_empty") {
    return (
      "The AI did not suggest any improvements for this draft. " +
      "It may already read clearly, or there may be too little text to work with. " +
      "Add more detail to the title or description and try again."
    );
  }
  if (emptyReason === "filtered") {
    const count = itemsFilteredOut || rawItemsReceived;
    return (
      `The AI returned ${count} suggestion(s), but none could be shown ` +
      "(unexpected format or missing fields). Try Generate again; if it keeps happening, save the draft and contact support."
    );
  }
  return "No AI suggestions were returned.";
}

export function aiGenerateSuccessMessage(count: number): string {
  return `Generated ${count} AI suggestion${count === 1 ? "" : "s"}. Review each item, then Apply or Discard.`;
}

export function aiApplySuccessMessage(excerptFound: boolean): string {
  if (excerptFound) {
    return "Suggestion applied to the form. Save draft to persist your changes.";
  }
  return (
    "Suggestion applied using a full-field replacement (the quoted excerpt was not found verbatim in your draft). " +
    "Save draft to persist."
  );
}

export function aiDiscardSuccessMessage(): string {
  return "Suggestion discarded. It will not be applied unless you generate a new batch.";
}

export function aiRegenerateConfirmMessage(): string {
  return (
    "Generate a new batch of AI suggestions? " +
    "The current list will be replaced and any items you have not applied or discarded will be lost."
  );
}

export function isAiGenerateSuccessMessage(message: string): boolean {
  return message.startsWith("Generated ") && message.includes("AI suggestion");
}

export function isAiPersistReminderMessage(message: string): boolean {
  const lower = message.toLowerCase();
  return lower.includes("save draft to persist") || lower.includes("save the draft");
}
