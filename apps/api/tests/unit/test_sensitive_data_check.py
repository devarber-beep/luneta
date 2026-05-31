"""Unit tests for sensitive-data heuristics."""
from __future__ import annotations

from datetime import UTC, datetime

from app.models.scenario import ScenarioModel
from app.services.sensitive_data_check import scan_scenario_for_sensitive_data

_NOW = datetime.now(UTC)


def _scenario(**text: str) -> ScenarioModel:
    return ScenarioModel.model_validate(
        {
            "slug": "study",
            "title": text.get("title", "Study"),
            "description": text.get("description", "Generic classroom observation without identifiers."),
            "author_user_id": "a" * 24,
            "state": "draft",
            "category_ids": [],
            "ethical_risk_ids": [],
            "collaborators": [],
            "last_state_changed_at": _NOW,
            "created_at": _NOW,
            "updated_at": _NOW,
        }
    )


def test_clean_text_passes() -> None:
    result = scan_scenario_for_sensitive_data(_scenario())
    assert result.passed is True
    assert result.findings == []


def test_detects_email_with_location() -> None:
    result = scan_scenario_for_sensitive_data(
        _scenario(description="Contact teacher@school.edu for access.")
    )
    assert result.passed is False
    assert any(f.finding_type == "email" and f.field == "description" for f in result.findings)
    assert result.findings[0].excerpt


def test_ignores_participant_without_proper_name() -> None:
    result = scan_scenario_for_sensitive_data(
        _scenario(description="The participant agreed to take part in the study.")
    )
    assert result.passed is True


def test_detects_proper_name() -> None:
    result = scan_scenario_for_sensitive_data(
        _scenario(description="Notes refer to Maria Lopez throughout the session.")
    )
    assert any(f.finding_type == "person_name" for f in result.findings)


def test_title_colega_or_estudio_not_person_name() -> None:
    for title in ("Colega", "Estudio Colega", "Colega del instituto", "Uso de datos en el aula"):
        result = scan_scenario_for_sensitive_data(_scenario(title=title))
        assert result.passed, title


def test_detects_residence_phrase_not_city_alone() -> None:
    result = scan_scenario_for_sensitive_data(
        _scenario(description="Fieldwork took place in Madrid over two weeks.")
    )
    assert result.passed is True
    result2 = scan_scenario_for_sensitive_data(
        _scenario(description="The family is afincado en Madrid since 2010.")
    )
    assert any(f.finding_type == "residence_phrase" for f in result2.findings)


def test_no_longer_detects_ipv4() -> None:
    result = scan_scenario_for_sensitive_data(
        _scenario(description="Server logs came from 192.168.0.44 during the trial.")
    )
    assert result.passed is True
