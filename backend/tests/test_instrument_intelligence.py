"""Phase 14.8 — Predictive Instrument Intelligence timeline + prediction."""
from app.db.session import SessionLocal
from app.services.instrument_intelligence import instrument_timeline, _trend
from app.db import models


def _mk(tenant, barcode, risk_score, review=False):
    db = SessionLocal()
    try:
        row = models.Inspection(
            file_name="x.jpg", tenant_id=tenant, tenant_name=tenant,
            instrument_type="scope", instrument_barcode=barcode,
            has_image=True, risk_score=risk_score, score_status="scored",
            risk_level="low", supervisor_review_required=review,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


def test_trend_helper():
    assert _trend([5, 5]) == "stable"
    assert _trend([5, 10, 40, 60]) == "worsening"
    assert _trend([60, 40, 10, 5]) == "improving"
    assert _trend([10]) == "insufficient_data"


def test_timeline_and_prediction():
    tenant = "tl-tenant"
    bc = "BC-TL-1"
    db = SessionLocal()
    try:
        db.query(models.Inspection).filter(
            models.Inspection.instrument_barcode == bc
        ).delete()
        db.commit()
    finally:
        db.close()
    # Rising risk over four inspections → worsening trend + RUL estimate.
    for rs in (5, 20, 45, 60):
        _mk(tenant, bc, rs)

    db = SessionLocal()
    try:
        out = instrument_timeline(db, bc, tenant)
    finally:
        db.close()

    assert out["inspection_count"] == 4
    assert out["prediction"]["risk_trend"] == "worsening"
    assert out["prediction"]["latest_risk_score"] == 60
    assert out["prediction"]["estimated_remaining_life"]  # projected estimate present
    # Timeline entries expose the recorded fields.
    assert out["timeline"][0]["risk_score"] == 5
    assert out["timeline"][-1]["inspection_score"] == 40  # 100 - 60


def test_empty_timeline_for_unknown_instrument():
    db = SessionLocal()
    try:
        out = instrument_timeline(db, "does-not-exist-zzz", "tl-tenant")
    finally:
        db.close()
    assert out["inspection_count"] == 0
    assert out["prediction"]["risk_trend"] == "insufficient_data"
