"""Split scenario descriptions into paragraphs (double newline separated).

Contract: packages/contracts/fixtures/description_paragraphs.json
Web mirror: apps/web/src/domain/descriptionParagraphs.ts
"""
from __future__ import annotations

PARAGRAPH_SEPARATOR = "\n\n"


def split_paragraphs(description: str) -> list[str]:
    text = (description or "").strip()
    if not text:
        return []
    if PARAGRAPH_SEPARATOR in text:
        return [p for p in text.split(PARAGRAPH_SEPARATOR) if p.strip()]
    return [text]


def paragraph_count(description: str) -> int:
    return len(split_paragraphs(description))


def replace_paragraph(*, description: str, paragraph_index: int, new_text: str) -> str:
    parts = split_paragraphs(description)
    if paragraph_index < 0 or paragraph_index >= len(parts):
        msg = f"paragraph_index {paragraph_index} out of range (0..{len(parts) - 1})"
        raise ValueError(msg)
    parts[paragraph_index] = new_text
    return PARAGRAPH_SEPARATOR.join(parts)
