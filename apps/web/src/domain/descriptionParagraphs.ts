/**
 * Paragraph splitting for scenario descriptions.
 * Contract: packages/contracts/fixtures/description_paragraphs.json
 * Python mirror: apps/api/app/core/description_paragraphs.py
 */
export const PARAGRAPH_SEPARATOR = "\n\n";

export function splitDescriptionParagraphs(description: string): string[] {
  const text = (description || "").trim();
  if (!text) return [];
  if (text.includes(PARAGRAPH_SEPARATOR)) {
    return text.split(PARAGRAPH_SEPARATOR).filter((p) => p.trim());
  }
  return [text];
}

export function joinDescriptionParagraphs(parts: string[]): string {
  return parts.join(PARAGRAPH_SEPARATOR);
}

export function replaceDescriptionParagraph(
  description: string,
  paragraphIndex: number,
  newText: string,
): string {
  const parts = splitDescriptionParagraphs(description);
  if (paragraphIndex < 0 || paragraphIndex >= parts.length) {
    throw new Error(
      `paragraph_index ${paragraphIndex} out of range (0..${parts.length - 1})`,
    );
  }
  parts[paragraphIndex] = newText;
  return joinDescriptionParagraphs(parts);
}
