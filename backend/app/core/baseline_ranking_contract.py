"""Baseline-aware ranking contract helpers."""

from __future__ import annotations

import re
from typing import Any


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def resolve_baseline_ranking_contract(
    instrument_match_status: str | None,
    baseline_status: str | None,
    baseline_confidence: str | None = None,
) -> dict[str, Any]:
    normalized_instrument_match = _normalize(instrument_match_status)
    normalized_baseline_status = _normalize(baseline_status)

    if (
        normalized_baseline_status == "approved_baseline_found"
        and normalized_instrument_match == "matched"
    ):
        return {
            "instrument_match_status": instrument_match_status or "",
            "baseline_status": baseline_status or "",
            "baseline_confidence": baseline_confidence or "",
            "ranking_mode": "Baseline-confirmed ranking",
            "baseline_review_required": False,
            "final_ranking_allowed": True,
            "review_reason": "Approved baseline matched.",
        }

    if normalized_baseline_status == "pending_baseline_review":
        return {
            "instrument_match_status": instrument_match_status or "",
            "baseline_status": baseline_status or "",
            "baseline_confidence": baseline_confidence or "",
            "ranking_mode": "Provisional ranking",
            "baseline_review_required": True,
            "final_ranking_allowed": False,
            "review_reason": "Baseline pending approval; ranking remains provisional.",
        }

    if normalized_baseline_status in {"no_approved_baseline", "baseline_not_available"}:
        return {
            "instrument_match_status": instrument_match_status or "",
            "baseline_status": baseline_status or "",
            "baseline_confidence": baseline_confidence or "",
            "ranking_mode": "Manual review required",
            "baseline_review_required": True,
            "final_ranking_allowed": False,
            "review_reason": "No approved baseline available for final ranking.",
        }

    return {
        "instrument_match_status": instrument_match_status or "",
        "baseline_status": baseline_status or "",
        "baseline_confidence": baseline_confidence or "",
        "ranking_mode": "Pending baseline check",
        "baseline_review_required": True,
        "final_ranking_allowed": False,
        "review_reason": "Baseline status has not been confirmed.",
    }
