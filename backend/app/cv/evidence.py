"""Evidence classification for CV results (P4.7.1 SCI-17, hardened in P4.7.2).

One place decides what a CV result or a stored ``CVInferenceRecord`` IS, so
KPIs, history, the review queue, ranking and every downstream analytics
service agree — and none of them can count an invented, simulated or
unverifiable result as a detection.

Classes
-------
``model_inference``    a completed run with TRUSTED server-issued provenance
                       (``app.cv.provenance``): sealed by this server for this
                       tenant, with an approved, integrity-verified artifact,
                       and the record still matches what was sealed.
``simulated``          produced by the dev/test simulation (mock provider).
                       Never a detection.
``ai_unavailable``     no approved model could run; nothing was evaluated.
``failed``             a model was configured but loading/execution failed.
``legacy_unverified``  everything else: a record with no independently
                       verifiable provenance — written before provenance
                       existed, written by anything other than the pipeline,
                       or whose provenance is missing, revoked or invalid.

P4.7.2: what a record says about itself is never evidence
---------------------------------------------------------
Until P4.7.2 a record was promoted to ``model_inference`` when its own
``result_json`` contained an ``evidence_class`` marker and a
``model_integrity.verified`` flag. Anything able to write a row could forge
both. Those claims are no longer read for promotion at all. A stored claim can
only ever DEMOTE a record (``simulated: true`` still marks it simulated).
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from sqlalchemy import and_, exists
from sqlalchemy.orm import Session, object_session

EVIDENCE_MODEL_INFERENCE = "model_inference"
EVIDENCE_SIMULATED = "simulated"
EVIDENCE_AI_UNAVAILABLE = "ai_unavailable"
EVIDENCE_FAILED = "failed"
EVIDENCE_LEGACY_UNVERIFIED = "legacy_unverified"

# Providers whose output is never model inference.
SIMULATED_PROVIDERS = frozenset({"mock"})
UNAVAILABLE_PROVIDERS = frozenset({"unavailable"})
_COMPLETED = ("success", "partial")


def _payload(record: Any) -> dict[str, Any]:
    raw = getattr(record, "result_json", "") or ""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def classify(*, provider: str, status: str, simulated: Any, provenance_trusted: bool) -> str:
    """The single classification rule.

    ``provenance_trusted`` must come from ``app.cv.provenance`` verification —
    never from a field of the record or result being classified."""
    provider = (provider or "").strip().lower()
    status = (status or "").strip().lower()
    if provider in SIMULATED_PROVIDERS or simulated is True:
        return EVIDENCE_SIMULATED
    if provider in UNAVAILABLE_PROVIDERS or status == EVIDENCE_AI_UNAVAILABLE:
        return EVIDENCE_AI_UNAVAILABLE
    if status == EVIDENCE_FAILED:
        return EVIDENCE_FAILED
    if status in _COMPLETED and provenance_trusted is True:
        return EVIDENCE_MODEL_INFERENCE
    return EVIDENCE_LEGACY_UNVERIFIED


def classify_result(result: Any, *, provenance_trusted: bool = False) -> str:
    """Evidence class of an in-memory ``CVInferenceResult``.

    Without ``provenance_trusted=True`` — which only the pipeline may pass, and
    only after it has sealed the run — a completed result is NOT model inference."""
    return classify(
        provider=getattr(result, "provider", ""),
        status=getattr(result, "status", ""),
        simulated=getattr(result, "simulated", False),
        provenance_trusted=provenance_trusted,
    )


def is_inference_candidate(result: Any) -> bool:
    """Could this in-memory result become model inference IF it can be sealed?"""
    return classify_result(result, provenance_trusted=True) == EVIDENCE_MODEL_INFERENCE


def _class_from_check(record: Any, trusted: bool) -> str:
    return classify(
        provider=getattr(record, "provider", ""),
        status=getattr(record, "status", ""),
        simulated=_payload(record).get("simulated"),
        provenance_trusted=trusted,
    )


def classify_record(record: Any, db: Session | None = None) -> str:
    """Evidence class of a stored ``CVInferenceRecord``.

    Provenance is looked up through ``db`` or the record's own session. With no
    session to verify against, a completed record is ``legacy_unverified``."""
    from app.cv.provenance import verify_record  # noqa: PLC0415 - avoids an import cycle

    session = db if db is not None else object_session(record)
    return _class_from_check(record, verify_record(session, record).trusted)


def classify_records(db: Session | None, records: Iterable[Any]) -> dict[int, str]:
    """Evidence class per record id, verifying provenance in ONE query."""
    from app.cv.provenance import verify_records  # noqa: PLC0415

    records = list(records)
    checks = verify_records(db, records)
    return {
        r.id: _class_from_check(r, checks[r.id].trusted)
        for r in records
        if r.id is not None
    }


def is_operational_evidence(evidence_class: str) -> bool:
    """Only verified model inference may feed defect KPIs, ranking or metrics."""
    return evidence_class == EVIDENCE_MODEL_INFERENCE


def operational_sql_criteria(model: Any) -> tuple:
    """Relational SQL criteria for operational evidence.

    A record qualifies only if a ``cv_inference_provenance`` row in the
    ``trusted`` state refers to it and agrees with it on inference id, tenant,
    provider and execution status. Nothing in ``result_json`` is consulted.

    This narrows a query; it cannot check the provenance seal or detect a record
    altered after sealing (those need the server key). Every reader MUST pass
    the rows it loads through ``integrity_verified`` before using them, e.g.::

        rows = db.query(CVInferenceRecord).filter(
            CVInferenceRecord.tenant_id == tenant_id,
            *operational_sql_criteria(CVInferenceRecord),
        ).all()
        rows = integrity_verified(db, rows)
    """
    from app.cv.provenance import STATE_TRUSTED  # noqa: PLC0415
    from app.models.cv_inference import CVInferenceProvenance  # noqa: PLC0415

    provenance = CVInferenceProvenance
    return (
        model.provider.notin_(tuple(sorted(SIMULATED_PROVIDERS | UNAVAILABLE_PROVIDERS))),
        model.status.in_(_COMPLETED),
        exists().where(and_(
            provenance.record_id == model.id,
            provenance.inference_id == model.inference_id,
            provenance.tenant_id == model.tenant_id,
            provenance.provider == model.provider,
            provenance.execution_status == model.status,
            provenance.state == STATE_TRUSTED,
            provenance.revoked_at == "",
        )),
    )


def integrity_verified(db: Session | None, records: Iterable[Any]) -> list:
    """Keep only the records whose provenance seal and content verify.

    The explicit integrity check that completes ``operational_sql_criteria``."""
    records = list(records)
    classes = classify_records(db, records)
    return [r for r in records if classes.get(r.id) == EVIDENCE_MODEL_INFERENCE]
