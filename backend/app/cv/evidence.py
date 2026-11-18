"""P4.7.1 — evidence classification for CV results (SCI-17).

One function decides what a CV result or a stored ``CVInferenceRecord`` IS, so
KPIs, history, the review queue and ranking all agree and none of them can
count a simulated or unverified result as a detection.

Classes
-------
``model_inference``    produced by a model whose artifacts passed SHA-256 pin
                       verification, and the run succeeded.
``simulated``          produced by the dev/test simulation (mock provider).
                       Never a detection.
``ai_unavailable``     no approved model could run; nothing was evaluated.
``failed``             a model was configured but loading/execution failed.
``legacy_unverified``  written before this classification existed (or without
                       integrity evidence). It is NOT promoted to
                       ``model_inference`` — its provenance cannot be shown.

No schema migration is needed: the class is derived from the already-stored
``provider`` and ``status`` columns plus the stored result payload.
"""
from __future__ import annotations

import json
from typing import Any

EVIDENCE_MODEL_INFERENCE = "model_inference"
EVIDENCE_SIMULATED = "simulated"
EVIDENCE_AI_UNAVAILABLE = "ai_unavailable"
EVIDENCE_FAILED = "failed"
EVIDENCE_LEGACY_UNVERIFIED = "legacy_unverified"

# Providers whose output is never model inference.
SIMULATED_PROVIDERS = frozenset({"mock"})
UNAVAILABLE_PROVIDERS = frozenset({"unavailable"})


def _payload(record: Any) -> dict[str, Any]:
    raw = getattr(record, "result_json", "") or ""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def classify(
    *, provider: str, status: str, simulated: Any, evidence_class: str, model_integrity: Any,
) -> str:
    provider = (provider or "").strip().lower()
    status = (status or "").strip().lower()
    if provider in SIMULATED_PROVIDERS or simulated is True:
        return EVIDENCE_SIMULATED
    if provider in UNAVAILABLE_PROVIDERS or status == EVIDENCE_AI_UNAVAILABLE:
        return EVIDENCE_AI_UNAVAILABLE
    if status == EVIDENCE_FAILED:
        return EVIDENCE_FAILED
    verified = isinstance(model_integrity, dict) and model_integrity.get("verified") is True
    if status in ("success", "partial") and verified and evidence_class == EVIDENCE_MODEL_INFERENCE:
        return EVIDENCE_MODEL_INFERENCE
    return EVIDENCE_LEGACY_UNVERIFIED


def classify_result(result: Any) -> str:
    """Evidence class of an in-memory ``CVInferenceResult``."""
    return classify(
        provider=getattr(result, "provider", ""),
        status=getattr(result, "status", ""),
        simulated=getattr(result, "simulated", False),
        evidence_class=getattr(result, "evidence_class", ""),
        model_integrity=getattr(result, "model_integrity", {}),
    )


def classify_record(record: Any) -> str:
    """Evidence class of a stored ``CVInferenceRecord`` (new or legacy)."""
    payload = _payload(record)
    return classify(
        provider=getattr(record, "provider", ""),
        status=getattr(record, "status", ""),
        simulated=payload.get("simulated"),
        evidence_class=str(payload.get("evidence_class") or ""),
        model_integrity=payload.get("model_integrity"),
    )


def is_operational_evidence(evidence_class: str) -> bool:
    """Only verified model inference may feed defect KPIs, ranking or metrics."""
    return evidence_class == EVIDENCE_MODEL_INFERENCE


def operational_sql_criteria(model: Any) -> tuple:
    """SQL criteria restricting a ``CVInferenceRecord`` query to operational
    evidence: verified model inference only.

    Every reader of ``cv_inference_records`` outside ``app.routes.cv`` MUST
    apply this, e.g. ``query.filter(*operational_sql_criteria(CVInferenceRecord))``.
    It excludes simulated (mock) rows, not-evaluated rows (whose NOT NULL score
    columns hold placeholders, never measurements), failed rows and legacy rows
    without integrity evidence.

    The ``evidence_class`` marker is written into ``result_json`` only by
    ``app.cv.pipeline.run_analysis`` after ``classify_result`` — which requires
    a passed SHA-256 integrity check — so it cannot be present on a simulated
    or legacy row. (Pydantic serialises compactly: no space after the colon.)
    """
    return (
        model.provider.notin_(tuple(sorted(SIMULATED_PROVIDERS | UNAVAILABLE_PROVIDERS))),
        model.status.in_(("success", "partial")),
        model.result_json.contains(
            f'"evidence_class":"{EVIDENCE_MODEL_INFERENCE}"', autoescape=True,
        ),
    )
