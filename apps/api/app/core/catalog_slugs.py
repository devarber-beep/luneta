"""Internal slug generation for catalog entries."""
from __future__ import annotations

from app.models.scenario import slugify_title


def slug_from_label(label: str) -> str:
    return slugify_title(label.strip()) or "entry"


async def allocate_unique_catalog_slug(
    *,
    get_by_slug,
    base_slug: str,
    suffix_start: int = 0,
) -> str:
    candidate = base_slug if suffix_start == 0 else f"{base_slug}-{suffix_start}"
    if await get_by_slug(candidate) is None:
        return candidate
    return await allocate_unique_catalog_slug(
        get_by_slug=get_by_slug,
        base_slug=base_slug,
        suffix_start=suffix_start + 1,
    )
