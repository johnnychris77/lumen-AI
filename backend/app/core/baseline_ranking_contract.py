"""Baseline-aware ranking contract helpers."""

from __future__ import annotations

import re
from typing import Any

BASELINE_RANKING_INPUT_FIELDS = (
    "instrument_match_status",
    "baseline_status",
    "baseline_confidence",
)

BASELINE_RANKING_AUDIT_IDENTITY_FIELDS = (
    "capture_method",
    "barcode_value",
    "instrument_name",
    "model_number",
    "instrument_category",
)


def _coerce_optional_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _coerce_optional_text(value).strip().lower()).strip("_")


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


def apply_baseline_ranking_to_inspection_payload(payload: dict[str, Any]) -> dict[str, Any]:
    contract = resolve_baseline_ranking_contract(
        instrument_match_status=payload.get("instrument_match_status"),
        baseline_status=payload.get("baseline_status"),
        baseline_confidence=payload.get("baseline_confidence"),
    )

    enriched_payload = dict(payload)
    enriched_payload.update(
        {
            "ranking_mode": contract["ranking_mode"],
            "baseline_review_required": contract["baseline_review_required"],
            "final_ranking_allowed": contract["final_ranking_allowed"],
            "baseline_review_reason": contract["review_reason"],
        }
    )
    return enriched_payload


def apply_baseline_ranking_to_inspection_payload_if_present(payload: dict[str, Any]) -> dict[str, Any]:
    if any(payload.get(field) not in (None, "") for field in BASELINE_RANKING_INPUT_FIELDS):
        return apply_baseline_ranking_to_inspection_payload(payload)
    return dict(payload)
