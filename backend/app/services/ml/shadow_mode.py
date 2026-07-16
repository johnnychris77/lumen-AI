"""Phase 17 §9 — Shadow-mode helpers.

Record a silent prediction and later reconcile it against the human final
decision. The invariant enforced here (and asserted by tests): a shadow
prediction is stored WITHOUT any clinical recommendation ever being surfaced.

Shadow (Phase 6 — Prospective Shadow-Mode Clinical Validation) §1 extends
this additively: a shadow prediction now also carries image-quality/
anatomy/instrument/facility context, and reconciliation is gated on the
inspection's own workflow state (`app.services.workflow_state_service`)
having reached a terminal state — the technician's finding and the
supervisor's review must already be *locked* before a shadow prediction is
ever reconciled or revealed, enforcing the mission's "humans decide first"
ordering rather than trusting callers to sequence it correctly.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.shadow_prediction import ShadowPrediction
from app.services import workflow_state_service
from app.services.ml import shadow_error_review_queue
from app.services.ml.shadow_comparison_engine import classify_comparison


def record_shadow_prediction(
    db: Session,
    *,
    tenant_id: str,
    model_id: str,
    model_version: str,
    model_type: str,
    predicted_label: str,
    predicted_confidence: str = "",
    inspection_id: int | None = None,
    payload: dict[str, Any] | None = None,
    image_quality: str = "",
    anatomy_zone: str = "",
    instrument_family: str = "",
    facility_id: str = "",
) -> ShadowPrediction:
    row = ShadowPrediction(
        tenant_id=tenant_id,
        model_id=model_id,
        model_version=model_version,
        model_type=model_type,
        inspection_id=inspection_id,
        predicted_label=predicted_label,
        predicted_confidence=str(predicted_confidence),
        prediction_payload=json.dumps(payload or {}),
        shadow_mode=True,
        image_quality=image_quality,
        anatomy_zone=anatomy_zone,
        instrument_family=instrument_family,
        facility_id=facility_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def public_view(row: ShadowPrediction) -> dict[str, Any]:
    """What a NON-privileged consumer may see: the fact a shadow ran, but never
    the predicted clinical recommendation. This is the API contract that keeps a
    shadow model from influencing care."""
    return {
        "id": row.id,
        "model_id": row.model_id,
        "model_type": row.model_type,
        "shadow_mode": True,
        "clinical_recommendation_shown": False,
        "revealed": row.revealed,
        "note": "A shadow model ran silently; its prediction is not shown as a recommendation.",
    }


def reconcile_with_human(db: Session, row: ShadowPrediction, final_label: str) -> ShadowPrediction:
    """Attach the human final decision and compute agreement (§9 comparison).

    Also classifies the comparison category (Shadow §4) additively — the
    original two fields this function has always set are unchanged."""
    row.supervisor_final_label = final_label
    row.agreed_with_human = (row.predicted_label == final_label)
    row.comparison_category = classify_comparison(
        predicted_label=row.predicted_label,
        human_final_label=final_label,
        confidence=_confidence_as_float(row.predicted_confidence),
    )
    db.commit()
    db.refresh(row)
    return row


def _confidence_as_float(predicted_confidence: str) -> float | None:
    try:
        return float(predicted_confidence)
    except (TypeError, ValueError):
        return None


def reveal_if_finalized(db: Session, row: ShadowPrediction, *, insp, final_label: str) -> ShadowPrediction:
    """Shadow §1 — the enforced reveal gate.

    A shadow prediction is reconciled against the human final decision, and
    only marked ``revealed``, once the inspection's own workflow state has
    reached a terminal state (Completed/Cancelled) — i.e. only after the
    technician's finding and the supervisor's review are already locked.
    Calling this before the workflow reaches a terminal state is a no-op:
    the row is returned unchanged, still hidden.
    """
    if insp is None or workflow_state_service.current_state(db, insp) not in workflow_state_service.TERMINAL_STATES:
        return row
    row = reconcile_with_human(db, row, final_label)
    row.revealed = True
    row.revealed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    # §6 — auto-route any disagreement to the error review queue the
    # moment it's revealed; a no-op for agreements.
    shadow_error_review_queue.route_if_disagreement(db, row)
    return row


def shadow_performance(rows: list[ShadowPrediction]) -> dict[str, Any]:
    """Aggregate agreement over reconciled shadow predictions — real evidence,
    only counting rows that have a human final decision."""
    reconciled = [r for r in rows if r.agreed_with_human is not None]
    agreed = sum(1 for r in reconciled if r.agreed_with_human)
    return {
        "total_shadow_predictions": len(rows),
        "reconciled": len(reconciled),
        "agreed_with_human": agreed,
        "agreement_rate": round(agreed / len(reconciled), 4) if reconciled else None,
        "note": "Agreement measured only on shadow predictions reconciled against a human final decision.",
    }
