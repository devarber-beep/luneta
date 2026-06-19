"""Heuristic scan for identifiable or sensitive data in scenario text fields."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.scenario import ScenarioModel

_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{2,3}[\s.-]?\d{2,4}(?!\d)",
)
_IBAN = re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}\b", re.IGNORECASE)
_SPANISH_POSTAL = re.compile(
    r"\b(?:CP|C\.P\.|codigo postal|código postal)\s*-?\s*(?:0[1-9]|[1-4]\d|5[0-2])\d{3}\b",
    re.IGNORECASE,
)
_STREET = re.compile(
    r"\b(?:calle|c\/|avenida|av\.|plaza|paseo|pº|carretera|ctra\.|camino|traves[ií]a|"
    r"urbanizaci[oó]n|pol[ií]gono)\s+"
    r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\s.'-]{2,48}\d*\b",
    re.IGNORECASE,
)
_HONORIFIC_NAME = re.compile(
    r"\b(?:Sr|Sra|Srta|Dr|Dra|D\.|Dña|Don|Doña)\.?\s+"
    r"[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+(?:de\s+|del\s+)?[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){0,3}",
    re.IGNORECASE,
)
_PROPER_NAME = re.compile(
    r"\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+"
    r"(?:\s+(?:(?:de|del|la|los|las)\s+)?[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)+\b",
)
_RESIDENCE_PHRASE = re.compile(
    r"\b(?:vive en|vivir en|reside en|afincad[oa]\s+en|domiciliad[oa]\s+en|domicilio en|"
    r"residencia en|direcci[oó]n habitual|empadronad[oa]\s+en)\s+"
    r"[\w\s.'-]{3,60}",
    re.IGNORECASE,
)
_CREDIT_CARD = re.compile(r"\b(?:\d{4}[-\s]){3}\d{4}\b")

_PATTERN_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", _EMAIL),
    ("phone", _PHONE),
    ("iban", _IBAN),
    ("credit_card", _CREDIT_CARD),
    ("postal_code", _SPANISH_POSTAL),
    ("street_address", _STREET),
    ("residence_phrase", _RESIDENCE_PHRASE),
    ("person_name", _HONORIFIC_NAME),
)

# Common words in scenario titles/descriptions that are not personal names.
_NAME_STOPWORDS: frozenset[str] = frozenset(
    {
        "artificial",
        "intelligence",
        "machine",
        "learning",
        "data",
        "science",
        "study",
        "estudio",
        "research",
        "scenario",
        "escenario",
        "classroom",
        "aula",
        "school",
        "university",
        "universidad",
        "instituto",
        "colegio",
        "colega",
        "students",
        "children",
        "niños",
        "observation",
        "observacion",
        "digital",
        "education",
        "educacion",
        "ethical",
        "review",
        "luneta",
        "smart",
        "glasses",
        "real",
        "world",
        "field",
        "work",
        "trabajo",
        "proyecto",
        "informe",
        "analisis",
        "uso",
        "practica",
        "grupo",
        "clase",
        "sesion",
        "entrevista",
        "cuestionario",
        "north",
        "south",
        "east",
        "west",
        "san",
        "los",
        "las",
        "del",
        "una",
        "unos",
        "unas",
        "el",
        "la",
        "los",
        "las",
        "en",
        "de",
    }
)

_TITLE_FIELDS = frozenset({"title", "public_title"})

FINDING_LABELS: dict[str, str] = {
    "email": "email address",
    "phone": "phone number",
    "iban": "bank account (IBAN)",
    "credit_card": "payment card number",
    "postal_code": "postal code",
    "street_address": "street address",
    "residence_phrase": "home or residence location phrase",
    "person_name": "person name",
}

FIELD_LABELS: dict[str, str] = {
    "title": "Title",
    "description": "Description",
    "public_title": "Public title",
    "public_description": "Public description",
}


@dataclass(frozen=True)
class SensitiveFinding:
    finding_type: str
    field: str
    excerpt: str

    @property
    def label(self) -> str:
        return FINDING_LABELS.get(self.finding_type, self.finding_type)

    @property
    def field_label(self) -> str:
        return FIELD_LABELS.get(self.field, self.field)


@dataclass(frozen=True)
class SensitiveDataCheckResult:
    passed: bool
    finding_types: list[str]
    findings: list[SensitiveFinding]


def _scenario_fields(scenario: ScenarioModel) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for field, value in (
        ("title", scenario.title),
        ("description", scenario.description),
        ("public_title", scenario.public_title),
        ("public_description", scenario.public_description),
    ):
        if isinstance(value, str) and value.strip():
            rows.append((field, value))
    return rows


def _redact_match(text: str, start: int, end: int, *, max_len: int = 72) -> str:
    pad = 18
    snippet_start = max(0, start - pad)
    snippet_end = min(len(text), end + pad)
    prefix = "…" if snippet_start > 0 else ""
    suffix = "…" if snippet_end < len(text) else ""
    body = text[snippet_start:snippet_end]
    rel_start = start - snippet_start
    rel_end = end - snippet_start
    redacted = f"{body[:rel_start]}[…]{body[rel_end:]}"
    excerpt = f"{prefix}{redacted}{suffix}".strip()
    if len(excerpt) > max_len:
        return excerpt[: max_len - 1] + "…"
    return excerpt


def _is_likely_proper_name(match: re.Match[str]) -> bool:
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", match.group(0))
    if len(words) < 2:
        return False
    lowered = [w.lower() for w in words]
    if all(word in _NAME_STOPWORDS for word in lowered):
        return False
    # At least two tokens must look like name parts (not generic scenario vocabulary).
    name_like = [w for w in lowered if w not in _NAME_STOPWORDS and len(w) >= 3]
    return len(name_like) >= 2


def _findings_for_text(*, field: str, text: str) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    seen: set[tuple[str, str]] = set()

    def add(finding_type: str, match: re.Match[str]) -> None:
        excerpt = _redact_match(text, match.start(), match.end())
        key = (finding_type, excerpt)
        if key in seen:
            return
        seen.add(key)
        findings.append(SensitiveFinding(finding_type=finding_type, field=field, excerpt=excerpt))

    for finding_type, pattern in _PATTERN_RULES:
        for match in pattern.finditer(text):
            if finding_type == "person_name" and pattern is _HONORIFIC_NAME:
                add(finding_type, match)
            elif finding_type != "person_name":
                add(finding_type, match)

    if field not in _TITLE_FIELDS:
        for match in _PROPER_NAME.finditer(text):
            if _is_likely_proper_name(match):
                add("person_name", match)

    return findings


def scan_scenario_for_sensitive_data(scenario: ScenarioModel) -> SensitiveDataCheckResult:
    all_findings: list[SensitiveFinding] = []
    for field, text in _scenario_fields(scenario):
        all_findings.extend(_findings_for_text(field=field, text=text))

    finding_types: list[str] = []
    for item in all_findings:
        if item.finding_type not in finding_types:
            finding_types.append(item.finding_type)

    return SensitiveDataCheckResult(
        passed=not all_findings,
        finding_types=finding_types,
        findings=all_findings,
    )


def format_finding_labels(finding_types: list[str]) -> str:
    if not finding_types:
        return "sensitive or identifiable data"
    return ", ".join(FINDING_LABELS.get(code, code) for code in finding_types)


def sensitive_data_blocked_message(*, finding_types: list[str], action: str) -> str:
    labels = format_finding_labels(finding_types)
    verb = "saved" if action == "save" else "submitted for review"
    return (
        "Sensitive or identifiable data detected. Your scenario could not be "
        f"{verb}. Please anonymize or remove: {labels}. "
        "Edit the text in the editor and try again."
    )


def findings_as_dicts(findings: list[SensitiveFinding]) -> list[dict[str, str]]:
    return [
        {
            "finding_type": f.finding_type,
            "field": f.field,
            "field_label": f.field_label,
            "label": f.label,
            "excerpt": f.excerpt,
        }
        for f in findings
    ]
