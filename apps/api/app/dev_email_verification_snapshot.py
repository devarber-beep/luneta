"""In-memory snapshot of the last issued email verification token (dev-only)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

_snapshot: _Snapshot | None = None


@dataclass(frozen=True)
class _Snapshot:
    email: str
    token: str
    issued_at: datetime


def record_last(*, email: str, token: str) -> None:
    global _snapshot
    _snapshot = _Snapshot(email=email, token=token, issued_at=datetime.now(UTC))


def get_last() -> _Snapshot | None:
    return _snapshot


def clear_last() -> None:
    global _snapshot
    _snapshot = None
