"""Baseline-aware ranking contract helpers."""

from __future__ import annotations

import re


BASELINE_RANKING_INPUT_FIELDS = (
    "instrument_match_status",
    "baseline_status",
    "baseline_confidence",
)


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
