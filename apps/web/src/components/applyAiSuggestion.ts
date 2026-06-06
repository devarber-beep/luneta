import type { AiSuggestionItem } from "../api";
import {
  joinDescriptionParagraphs,
  splitDescriptionParagraphs,
} from "../domain/descriptionParagraphs";

export function replaceExcerpt(current: string, excerpt: string, proposed: string): string {
  const field = current ?? "";
  const needle = excerpt.trim();
  if (!needle) {
    return proposed;
  }
  const idx = field.indexOf(needle);
  if (idx >= 0) {
    return field.slice(0, idx) + proposed + field.slice(idx + needle.length);
  }
  if (field.trim() === needle) {
    return proposed;
  }
  return proposed;
}

export type ApplyAiSuggestionResult = {
  title?: string;
  description?: string;
  excerptFound: boolean;
};

export function applyAiSuggestionToDraft(
  item: AiSuggestionItem,
  draft: { title: string; description: string },
): ApplyAiSuggestionResult {
  if (item.scope === "title") {
    const next = replaceExcerpt(draft.title, item.current_excerpt, item.proposed_text);
    const excerptFound =
      !item.current_excerpt.trim() ||
      draft.title.includes(item.current_excerpt) ||
      draft.title.trim() === item.current_excerpt.trim();
    return { title: next, excerptFound };
  }

  if (item.scope === "description_full") {
    const next = replaceExcerpt(draft.description, item.current_excerpt, item.proposed_text);
    const excerptFound =
      !item.current_excerpt.trim() ||
      draft.description.includes(item.current_excerpt) ||
      draft.description.trim() === item.current_excerpt.trim();
    return { description: next, excerptFound };
  }

  const parts = splitDescriptionParagraphs(draft.description);
  const idx = item.paragraph_index ?? -1;
  if (idx < 0 || idx >= parts.length) {
    return { excerptFound: false };
  }
  const paragraph = parts[idx];
  const nextParagraph = replaceExcerpt(paragraph, item.current_excerpt, item.proposed_text);
  const excerptFound =
    !item.current_excerpt.trim() ||
    paragraph.includes(item.current_excerpt) ||
    paragraph.trim() === item.current_excerpt.trim();
  parts[idx] = nextParagraph;
  return { description: joinDescriptionParagraphs(parts), excerptFound };
}
