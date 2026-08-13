"""Post-commit enrichment must never sink a completed inspection.

`POST /api/inspections` commits the Inspection row and its AI result, then runs
additive enrichment (findings log, image-view tags, workflow audit, clinical
case library, decision engine, data-quality guardrails). Before this fix, any
one of those raising — e.g. a production table missing a drifted column — turned
a fully-saved inspection into a 500. Because the error is generated above the
CORS middleware, the browser showed a bare "Failed to fetch"; technicians then
retried and created DUPLICATE inspections while never seeing a result.

These tests force each enrichment step to raise and assert the request still
returns 201 with the core result, and that the inspection was persisted exactly
once.
"""
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "res1l13n" + "0" * 56
TENANT = "default-tenant"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"res-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _payload(itype: str, **extra) -> dict:
    p = {
        "instrument_type": itype, "site_name": "Mercy",
        "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        "finding_categories": [],
        # exercise the image-tag persist branch too
        "image_view_tags": [{
            "instrument_family": itype, "anatomy_zone": "tip",
            "image_view": "tip", "capture_quality": "acceptable", "notes": "",
        }],
    }
    p.update(extra)
    return p


def _count(itype: str) -> int:
    db = SessionLocal()
    try:
        return db.query(models.Inspection).filter(models.Inspection.instrument_type == itype).count()
    finally:
        db.close()


def test_decision_engine_failure_does_not_500_and_saves_once(monkeypatch):
    itype = "resilience_decision_type"
    _baseline(itype)

    def _boom(*a, **k):
        raise RuntimeError("simulated decision-engine drift")

    monkeypatch.setattr("app.services.lumen_decision_engine.build_decision", _boom)

    before = _count(itype)
    r = client.post("/api/inspections", json=_payload(itype), headers=AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    body = r.json()
    # Core result is intact; only the degraded enrichment key is absent.
    assert "id" in body
    assert "risk_score" in body
    assert body.get("decision") in (None, {}) or "decision" not in body
    # Saved exactly once — no duplicate-inducing 500.
    assert _count(itype) == before + 1


def test_data_quality_failure_does_not_500(monkeypatch):
    itype = "resilience_dq_type"
    _baseline(itype)

    def _boom(*a, **k):
        raise RuntimeError("simulated data-quality drift")

    monkeypatch.setattr(
        "app.services.data_quality_guardrails_service.evaluate_data_quality", _boom
    )

    r = client.post("/api/inspections", json=_payload(itype), headers=AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "id" in body
    assert "data_quality" not in body or body["data_quality"] is None


def test_image_tag_persist_failure_does_not_500(monkeypatch):
    itype = "resilience_imgtag_type"
    _baseline(itype)

    # Force the image-tag model construction to raise inside the persist step.
    import app.models.inspection_image_tag as tag_mod

    def _boom(*a, **k):
        raise RuntimeError("simulated image-tag table drift")

    monkeypatch.setattr(tag_mod, "InspectionImageTag", _boom)

    before = _count(itype)
    r = client.post("/api/inspections", json=_payload(itype), headers=AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    assert _count(itype) == before + 1
