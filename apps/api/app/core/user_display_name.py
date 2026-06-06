"""Format and normalize person names for display and search."""
from __future__ import annotations

import re

_MAX_LEN = 60


def normalize_name_part(raw: str | None) -> str | None:
    if raw is None:
        return None
    display = re.sub(r"\s+", " ", raw.strip())
    if not display:
        return None
    return display[:_MAX_LEN]


def build_display_name(*, first_name: str | None, last_name: str | None) -> str:
    parts: list[str] = []
    fn = normalize_name_part(first_name)
    ln = normalize_name_part(last_name)
    if fn:
        parts.append(fn)
    if ln:
        parts.append(ln)
    return " ".join(parts)


def build_display_name_normalized(*, first_name: str | None, last_name: str | None) -> str:
    return build_display_name(first_name=first_name, last_name=last_name).lower()


def parse_person_names(
    *,
    first_name: str | None,
    last_name: str | None,
) -> tuple[str, str, str, str]:
    fn = normalize_name_part(first_name)
    ln = normalize_name_part(last_name)
    if not fn:
        raise ValueError("first_name is required")
    if not ln:
        raise ValueError("last_name is required")
    display = build_display_name(first_name=fn, last_name=ln)
    return fn, ln, display, display.lower()
