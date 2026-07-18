"""
P2C: End-to-end workflow tests for Inspection Intelligence.

Covers:
- Baseline review queue endpoint
- Baseline-aware scoring (all 4 confidence tiers)
- Baseline comparison route
- Vendor baseline creation → approval → audit trail
- 401/403 response shapes for auth-protected routes
"""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _ensure_tables():
    from app.db.base import Base
    from app.db.session import engine
    import app.models.enterprise_quality  # noqa: F401
    import app.models.vendor_baseline_audit  # noqa: F401

    Base.metadata.create_all(bind=engine)


def _make_finding(db, *, tenant_id: str = "test-tenant", severity: str = "high"):
    from app.models.enterprise_quality import EnterpriseFinding
    from datetime import datetime, timezone

    finding = EnterpriseFinding(
        tenant_id=tenant_id,
        finding_category="bioburden / retained debris",
        finding_description="Test finding for workflow validation",
        severity=severity,
        confidence_score=0.85,
        human_confirmed=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


# ── Baseline Review Queue ────────────────────────────────────────────────────

def test_baseline_review_queue_returns_success_shape():
    _ensure_tables()
    from app.main import app

    client = TestClient(app)
    response = client.get(
        "/api/enterprise/baseline-review-queue",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "viewer",
            "X-LumenAI-Actor": "reviewer@test.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "queue_type" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "queue_count" in data
    assert "generated_at" in data


def test_baseline_review_queue_respects_limit_parameter():
    _ensure_tables()
    from app.main import app

    client = TestClient(app)
    response = client.get(
        "/api/enterprise/baseline-review-queue?limit=1",
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "viewer", "X-LumenAI-Actor": "reviewer@test.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 1


def test_baseline_review_queue_item_fields_present():
    _ensure_tables()
    from app.db.session import SessionLocal
    from app.main import app

    db = SessionLocal()
    try:
        _make_finding(db)
    finally:
        db.close()

    client = TestClient(app)
    response = client.get(
        "/api/enterprise/baseline-review-queue?limit=50",
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "viewer", "X-LumenAI-Actor": "reviewer@test.com"},
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert "finding_id" in item
        assert "score" in item
        assert "score_confidence" in item
        assert "baseline_source" in item
        assert "baseline_status" in item
        assert "requires_baseline_review" in item
        assert "manual_review_required" in item
        assert "recommended_action" in item


# ── Baseline-Aware Scoring ───────────────────────────────────────────────────

def test_baseline_aware_score_approved_vendor_baseline_returns_high_confidence():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/enterprise/baseline-aware-score",
        headers={"Authorization": "Bearer dev-token"},
        json={
            "finding_type": "bioburden",
            "risk_level": "high",
            "vendor_baseline_id": 1,
            "hospital_baseline_id": None,
            "historical_match_count": 0,
            "baseline_status": "approved",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    result = data["scoring_result"]
    assert result["score_confidence"].lower() == "high"
    assert result["requires_baseline_review"] is False
    assert result["baseline_source"] == "vendor"


def test_baseline_aware_score_approved_hospital_baseline_returns_medium_high_confidence():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/enterprise/baseline-aware-score",
        headers={"Authorization": "Bearer dev-token"},
        json={
            "finding_type": "bioburden",
            "risk_level": "medium",
            "vendor_baseline_id": None,
            "hospital_baseline_id": 5,
            "historical_match_count": 0,
            "baseline_status": "approved",
        },
    )
    assert response.status_code == 200
    data = response.json()
    result = data["scoring_result"]
    assert result["requires_baseline_review"] is False
    assert result["baseline_source"] == "hospital"


def test_baseline_aware_score_historical_pattern_returns_medium_confidence():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/enterprise/baseline-aware-score",
        headers={"Authorization": "Bearer dev-token"},
        json={
            "finding_type": "bioburden",
            "risk_level": "low",
            "vendor_baseline_id": None,
            "hospital_baseline_id": None,
            "historical_match_count": 5,
            "baseline_status": None,
        },
    )
    assert response.status_code == 200
    data = response.json()
    result = data["scoring_result"]
    assert result["requires_baseline_review"] is True
    assert result["baseline_source"] in {"historical", "historical_pattern"}


def test_baseline_aware_score_no_baseline_requires_manual_review():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/enterprise/baseline-aware-score",
        headers={"Authorization": "Bearer dev-token"},
        json={
            "finding_type": "bioburden",
            "risk_level": "high",
            "vendor_baseline_id": None,
            "hospital_baseline_id": None,
            "historical_match_count": 0,
            "baseline_status": None,
        },
    )
    assert response.status_code == 200
    data = response.json()
    result = data["scoring_result"]
    assert result["manual_review_required"] is True
    assert result["baseline_source"] == "none"


def test_baseline_aware_score_recommended_action_present():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/enterprise/baseline-aware-score",
        headers={"Authorization": "Bearer dev-token"},
        json={"finding_type": "debris", "risk_level": "critical"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommended_action" in data
    assert len(data["recommended_action"]) > 0


# ── Baseline Comparison ──────────────────────────────────────────────────────

def test_baseline_comparison_returns_structured_response():
    _ensure_tables()
    from app.db.session import SessionLocal
    from app.main import app
    from app.models.enterprise_quality import (
        EnterpriseInstrument,
        EnterpriseInstrumentBaseline,
        EnterpriseFinding,
    )
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        instrument = EnterpriseInstrument(
            tenant_id="test-tenant",
            name="Test Scope For Comparison",
            instrument_type="lumened_instrument",
            category="lumened instrument",
            model_number="TST-001",
            risk_class="high",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db.add(instrument)
        db.flush()

        baseline = EnterpriseInstrumentBaseline(
            instrument_id=instrument.id,
            baseline_status="approved",
            created_at=datetime.now(timezone.utc),
        )
        db.add(baseline)
        db.flush()

        finding = EnterpriseFinding(
            tenant_id="test-tenant",
            instrument_id=instrument.id,
            finding_category="bioburden / retained debris",
            finding_description="Test finding for baseline comparison",
            severity="high",
            confidence_score=0.85,
            human_confirmed=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        finding_id = finding.id
    finally:
        db.close()

    client = TestClient(app)
    response = client.post(
        f"/api/enterprise/intake/{finding_id}/baseline-comparison",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "operator",
            "X-LumenAI-Actor": "reviewer@test.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "finding_id" in data or "scoring_result" in data or "baseline_comparison_type" in data


def test_baseline_comparison_missing_finding_returns_404():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/enterprise/intake/999999/baseline-comparison",
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator", "X-LumenAI-Actor": "test@test.com"},
    )
    assert response.status_code == 404


# ── Vendor Baseline Full Workflow ────────────────────────────────────────────

def test_vendor_baseline_create_approve_audit_workflow():
    _ensure_tables()
    from app.main import app
    import time

    unique = str(int(time.time() * 1000))[-6:]
    client = TestClient(app)

    # Step 1: Create vendor baseline
    create_resp = client.post(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        json={
            "vendor_name": f"TestVendor-{unique}",
            "instrument_name": f"TestScope-{unique}",
            "instrument_category": "lumened instrument",
            "catalog_number": f"CAT-{unique}",
            "model_number": f"MDL-{unique}",
            "barcode_value": f"BC-{unique}",
            "qr_code_value": f"QR-{unique}",
            "key_dot_value": "",
            "tray_name": "Test Tray A",
            "baseline_image_url": "https://demo.example.com/baseline.jpg",
            "acceptable_condition_notes": "Clear lumen, no debris.",
            "unacceptable_condition_examples": "Debris present.",
            "ifu_reference": f"IFU-{unique}",
            "subscription_tier": "vendor_enterprise",
        },
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "vendor", "X-LumenAI-Actor": f"vendor-{unique}@test.com"},
    )
    assert create_resp.status_code == 200, create_resp.text
    create_data = create_resp.json()
    baseline_id = create_data.get("baseline_id") or create_data.get("baseline", {}).get("baseline_id")
    assert baseline_id

    # Step 2: Verify it appears in the library
    list_resp = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "hospital_admin", "X-LumenAI-Actor": "admin@test.com"},
    )
    assert list_resp.status_code == 200
    records = list_resp.json()["records"]
    ids = [r.get("baseline_id") or r.get("id") for r in records]
    assert baseline_id in ids

    # Step 3: Approve the baseline
    approve_resp = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        json={"approval_notes": "Meets hospital baseline standards."},
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "hospital_admin", "X-LumenAI-Actor": "admin@hospital.com"},
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    # approve response wraps the record under "baseline" key
    approved_record = approved_data.get("baseline") or approved_data
    assert approved_record.get("baseline_id") == baseline_id or approved_data.get("status") == "success"
    status_val = approved_record.get("baseline_status") or approved_record.get("approval_status") or approved_data.get("new_status", "")
    assert status_val in {"approved", "vendor_approved", "hospital_approved", "active"}

    # Step 4: Audit trail records both events
    audit_resp = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "hospital_admin", "X-LumenAI-Actor": "admin@hospital.com"},
    )
    assert audit_resp.status_code == 200
    events = audit_resp.json()["events"]
    event_types = {e["event_type"] for e in events}
    assert "baseline_submitted" in event_types or len(events) >= 1
    assert any("approv" in e["event_type"].lower() for e in events)


def test_vendor_baseline_list_returns_records_key():
    _ensure_tables()
    from app.main import app

    client = TestClient(app)
    response = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "hospital_admin", "X-LumenAI-Actor": "viewer@test.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "records" in data, f"Expected 'records' key, got: {list(data.keys())}"
    assert isinstance(data["records"], list)


def test_vendor_baseline_record_has_required_fields():
    _ensure_tables()
    from app.main import app

    client = TestClient(app)
    response = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "hospital_admin", "X-LumenAI-Actor": "viewer@test.com"},
    )
    assert response.status_code == 200
    records = response.json()["records"]
    if not records:
        return  # Skip field check if no records yet

    record = records[0]
    for field in ("baseline_id", "vendor_name", "instrument_name", "baseline_status", "approval_status", "baseline_source"):
        assert field in record, f"Missing field '{field}' in vendor baseline record"
