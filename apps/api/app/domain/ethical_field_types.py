"""Shared enums for scenario usage context fields."""
from __future__ import annotations

from typing import Literal

DurationFrequencyOption = Literal[
    "daily",
    "once_a_week",
    "several_times_a_day",
    "several_times_a_week",
    "once_a_month",
]
YesNoAnswer = Literal["yes", "no"]
