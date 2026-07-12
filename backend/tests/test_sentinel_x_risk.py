"""LumenAI AI Specialist — Project Sentinel-X: Clinical Risk Intelligence &
Patient Safety Agent tests.

Covers the 8 named scenarios from the sprint brief's Section 13, plus a
route smoke test. Distinct from the pre-existing, unrelated
`test_sentinel_orchestration.py` ("Project Sentinel" v3.0).
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.inspection_finding import InspectionFinding
from app.models.sentinelx_risk import SentinelXRiskAssessment
from app.services import (
    sentinelx_override_service,
    sentinelx_patient_safety_watch_service,
    sentinelx_risk_scoring_service,
)
from app.services.sentinelx_risk_agent_service import run_risk_assessment

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _mk_inspection(db, tenant_id, *, barcode, instrument_type="kerrison rongeur", created_at=None):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="t.jpg", instrument_type=instrument_type, instrument_barcode=barcode,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mk_finding(db, tenant_id, inspection_id, *, finding_type, zone, severity_index):
    row = InspectionFinding(tenant_id=tenant_id, inspection_id=inspection_id, finding_type=finding_type, zone=zone, severity_index=severity_index)
    db.add(row)
    db.commit()
    return row


def _identity(barcode: str) -> str:
    return f"barcode:{barcode}"


# ── 1. blood in serration produces high risk ──────────────────────────────

def test_blood_in_serration_produces_high_risk():
    result = sentinelx_risk_scoring_service.compute_risk_score(
        finding_type="blood", severity_index=3, anatomy_zone_high_risk=True,
    )
    assert result["risk_level"] in ("high", "critical")


# ── 2. cosmetic discoloration remains low risk ────────────────────────────

def test_cosmetic_discoloration_remains_low_risk():
    blood = sentinelx_risk_scoring_service.compute_risk_score(finding_type="blood", severity_index=3, anatomy_zone_high_risk=True)
    discoloration = sentinelx_risk_scoring_service.compute_risk_score(finding_type="discoloration", severity_index=1, anatomy_zone_high_risk=False)
    assert discoloration["risk_level"] in ("very_low", "low")
    assert discoloration["risk_score"] < blood["risk_score"]


# ── 3. corrosion recurrence increases risk ────────────────────────────────

def test_corrosion_recurrence_increases_risk():
    low_recurrence = sentinelx_risk_scoring_service.compute_risk_score(finding_type="corrosion", severity_index=2, recurrence_count=0)
    high_recurrence = sentinelx_risk_scoring_service.compute_risk_score(finding_type="corrosion", severity_index=2, recurrence_count=4)
    assert high_recurrence["risk_score"] > low_recurrence["risk_score"]
    assert "recurrence" in high_recurrence["score_breakdown"]


# ── 4. Digital Twin decline increases risk ────────────────────────────────

def test_digital_twin_decline_increases_risk():
    stable = sentinelx_risk_scoring_service.compute_risk_score(finding_type="corrosion", severity_index=2, digital_twin_condition_trend="stable")
    declining = sentinelx_risk_scoring_service.compute_risk_score(finding_type="corrosion", severity_index=2, digital_twin_condition_trend="declining")
    assert declining["risk_score"] > stable["risk_score"]


# ── 5. missing evidence reduces confidence ────────────────────────────────

def test_missing_evidence_reduces_confidence():
    missing_evidence = sentinelx_risk_scoring_service.compute_risk_score(finding_type="corrosion", severity_index=2, evidence_readiness_score=None)
    strong_evidence = sentinelx_risk_scoring_service.compute_risk_score(finding_type="corrosion", severity_index=2, evidence_readiness_score=95)
    assert missing_evidence["score_breakdown"]["evidence_readiness_gap"] > strong_evidence["score_breakdown"].get("evidence_readiness_gap", 0)
    assert missing_evidence["risk_score"] > strong_evidence["risk_score"]


# ── 6. repeat anatomy failures escalate priority ──────────────────────────

def test_repeat_anatomy_failures_escalate_priority():
    tenant_id = uid("sentx-t")
    barcode = uid("instr")
    identity = _identity(barcode)
    db = SessionLocal()
    try:
        for _ in range(2):
            row = SentinelXRiskAssessment(
                tenant_id=tenant_id, instrument_identity=identity, anatomy_zone="jaw serration",
                risk_score=65.0, risk_level="high",
            )
            db.add(row)
        db.commit()

        fired = sentinelx_patient_safety_watch_service.scan_for_alerts(db, tenant_id)
        assert any(a.alert_type == "repeat_anatomy_failure" and a.instrument_identity == identity for a in fired)
    finally:
        db.close()


# ── 7. risk explanation includes supporting evidence ──────────────────────

def test_risk_explanation_includes_supporting_evidence():
    tenant_id = uid("sentx-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        base = datetime.now(timezone.utc) - timedelta(days=10)
        for day in (0, 5):
            insp = _mk_inspection(db, tenant_id, barcode=barcode, created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=2)

        row = run_risk_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        assert row.reasoning_narrative
        assert "corrosion" in row.reasoning_narrative.lower()
        assert row.evidence_json and row.evidence_json != "{}"
        assert row.score_breakdown_json and row.score_breakdown_json != "{}"
    finally:
        db.close()


# ── 8. supervisor override remains auditable ──────────────────────────────

def test_supervisor_override_remains_auditable():
    tenant_id = uid("sentx-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        insp = _mk_inspection(db, tenant_id, barcode=barcode)
        _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=2)
        row = run_risk_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        original_level = row.risk_level

        override = sentinelx_override_service.submit_override(
            db, tenant_id, row.id, overridden_risk_level="critical", rationale="Manual clinical review confirmed higher risk.",
            submitted_by="supervisor@local.dev", submitted_role="spd_manager",
        )
        assert override.original_risk_level == original_level
        assert override.overridden_risk_level == "critical"

        db.refresh(row)
        assert row.risk_level == original_level  # never silently mutated

        history = sentinelx_override_service.overrides_for_assessment(db, tenant_id, row.id)
        assert len(history) == 1

        raised = False
        try:
            sentinelx_override_service.submit_override(db, tenant_id, row.id, overridden_risk_level="low", rationale="", submitted_by="supervisor@local.dev")
        except ValueError:
            raised = True
        assert raised
    finally:
        db.close()


# ── Route smoke test ──────────────────────────────────────────────────────

def test_assess_and_dashboard_routes():
    tenant_id = uid("sentx-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        insp = _mk_inspection(db, tenant_id, barcode=barcode)
        _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=2)
    finally:
        db.close()

    r = client.post(
        "/api/sentinelx/assess", json={"instrument_identity": _identity(barcode), "instrument_type": "kerrison rongeur"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["risk_level"]
    assert body["human_review_required"] is True

    r2 = client.get("/api/sentinelx/dashboard", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert "enterprise_risk" in r2.json()

    r3 = client.get("/api/sentinelx/supervisor-workspace", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
