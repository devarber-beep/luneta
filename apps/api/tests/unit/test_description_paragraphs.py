"""Paragraph split/join contract: Python impl + web mirror (fixtures/description_paragraphs.json)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.core.description_paragraphs import (
    PARAGRAPH_SEPARATOR,
    paragraph_count,
    replace_paragraph,
    split_paragraphs,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURE_PATH = _REPO_ROOT / "fixtures" / "description_paragraphs.json"
_WEB_TS_PATH = _REPO_ROOT / "apps" / "web" / "src" / "domain" / "descriptionParagraphs.ts"


def _load_fixture() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_file_exists() -> None:
    assert _FIXTURE_PATH.is_file()


def test_paragraph_separator_matches_fixture() -> None:
    fixture = _load_fixture()
    assert PARAGRAPH_SEPARATOR == fixture["paragraph_separator"]


@pytest.mark.parametrize(
    "case",
    _load_fixture()["split_cases"],
    ids=lambda case: repr(case["description"][:40]),
)
def test_split_paragraphs(case: dict) -> None:
    assert split_paragraphs(case["description"]) == case["expected"]


@pytest.mark.parametrize(
    "case",
    _load_fixture()["replace_cases"],
    ids=lambda case: f"idx={case['paragraph_index']}",
)
def test_replace_paragraph(case: dict) -> None:
    if case.get("expect_error"):
        with pytest.raises(ValueError, match="out of range"):
            replace_paragraph(
                description=case["description"],
                paragraph_index=case["paragraph_index"],
                new_text=case["new_text"],
            )
        return
    assert (
        replace_paragraph(
            description=case["description"],
            paragraph_index=case["paragraph_index"],
            new_text=case["new_text"],
        )
        == case["expected"]
    )


def test_paragraph_count_uses_split() -> None:
    fixture = _load_fixture()
    sep = fixture["paragraph_separator"]
    assert paragraph_count("solo") == 1
    assert paragraph_count(f"a{sep}b") == 2


def test_web_typescript_mirror_matches_contract() -> None:
    """Static check: web TS module keeps the same separator and split/replace steps."""
    assert _WEB_TS_PATH.is_file(), f"Missing web mirror: {_WEB_TS_PATH}"
    source = _WEB_TS_PATH.read_text(encoding="utf-8")
    fixture = _load_fixture()
    sep = fixture["paragraph_separator"]
    assert sep == PARAGRAPH_SEPARATOR
    assert 'export const PARAGRAPH_SEPARATOR = "\\n\\n";' in source
    assert "export function splitDescriptionParagraphs" in source
    assert "export function joinDescriptionParagraphs" in source
    assert "export function replaceDescriptionParagraph" in source
    assert ".split(PARAGRAPH_SEPARATOR).filter((p) => p.trim())" in source
    assert '(description || "").trim()' in source
    assert re.search(r"paragraph_index \$\{paragraphIndex\} out of range", source)
