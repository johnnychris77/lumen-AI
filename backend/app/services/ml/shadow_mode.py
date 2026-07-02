"""Phase 17 §9 — Shadow-mode helpers.

Record a silent prediction and later reconcile it against the human final
decision. The invariant enforced here (and asserted by tests): a shadow
prediction is stored WITHOUT any clinical recommendation ever being surfaced.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.shadow_prediction import ShadowPrediction


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
        "note": "A shadow model ran silently; its prediction is not shown as a recommendation.",
    }


def reconcile_with_human(db: Session, row: ShadowPrediction, final_label: str) -> ShadowPrediction:
    """Attach the human final decision and compute agreement (§9 comparison)."""
    row.supervisor_final_label = final_label
    row.agreed_with_human = (row.predicted_label == final_label)
    db.commit()
    db.refresh(row)
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
