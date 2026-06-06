"""Unit tests for scenario content language detection."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.ai_suggestion_service import (
    _detect_content_language,
    _detect_content_language_heuristic,
)


def test_heuristic_detects_spanish() -> None:
    lang = _detect_content_language_heuristic(
        title="Estudio en el aula",
        description="Observación de niños en la escuela.",
    )
    assert lang == "es"


def test_heuristic_defaults_english() -> None:
    lang = _detect_content_language_heuristic(
        title="Classroom study",
        description="Observation research with smart glasses.",
    )
    assert lang == "en"


def test_langdetect_prefers_spanish_for_long_text() -> None:
    sample = (
        "Estudio observacional en aulas de primaria sobre el uso de gafas inteligentes "
        "para investigación educativa con niños."
    )
    mock_lang = MagicMock()
    mock_lang.lang = "es"
    mock_lang.prob = 0.99
    with patch("langdetect.detect_langs", return_value=[mock_lang]):
        lang = _detect_content_language(title="Título", description=sample)
    assert lang == "es"


def test_short_text_falls_back_to_heuristic() -> None:
    with patch(
        "app.services.ai_suggestion_service._detect_content_language_heuristic",
        return_value="es",
    ) as heuristic:
        lang = _detect_content_language(title="Hola", description="")
    assert lang == "es"
    heuristic.assert_called_once()
