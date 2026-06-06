"""Normalize university names for storage and search."""
from __future__ import annotations

import re

_MAX_LEN = 200


def parse_university_field(raw: str | None) -> tuple[str | None, str | None]:
    if raw is None:
        return None, None
    display = re.sub(r"\s+", " ", raw.strip())
    if not display:
        return None, None
    display = display[:_MAX_LEN]
    normalized = display.lower()
    return display, normalized
