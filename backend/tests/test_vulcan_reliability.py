"""LumenAI AI Specialist — Project Vulcan: Instrument Reliability, Failure
Analysis & Repair Intelligence tests.

Covers the 12 named scenarios from the sprint brief's Section 17, plus route
smoke tests for the Instrument Forensics Workspace / watchlists / executive
analytics endpoints.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import REPAIR_RETURNED, RepairRequest
from app.models.vulcan_reliability import (
    DISPOSITION_REMOVE_FROM_SERVICE,
    RELIABILITY_REMOVE_FROM_SERVICE_CANDIDATE,
)
from app.services import (
    vulcan_aegis_integration_service,
    vulcan_anatomy_zone_service,
    vulcan_feedback_service,
    vulcan_probable_cause_service,
    vulcan_progression_service,
    vulcan_reliability_agent_service,
    vulcan_repair_effectiveness_service,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _mk_inspection(db, tenant_id, *, barcode, instrument_type="kerrison rongeur", technician="", facility_name="", created_at=None):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="test.jpg", instrument_type=instrument_type,
        instrument_barcode=barcode, technician=technician, facility_name=facility_name,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mk_finding(db, tenant_id, inspection_id, *, finding_type, zone, severity_index):
    row = InspectionFinding(
        tenant_id=tenant_id, inspection_id=inspection_id, finding_type=finding_type,
        zone=zone, severity_index=severity_index,
    )
    db.add(row)
    db.commit()
    return row


def _identity(barcode: str) -> str:
    return f"barcode:{barcode}"


# ── 1. repeated corrosion creates progression signal ──────────────────────────

def test_repeated_corrosion_creates_progression_signal():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=60)
        for day, severity in [(0, 1), (25, 2), (55, 2)]:
            insp = _mk_inspection(db, tenant_id, barcode=barcode, created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=severity)

        result = vulcan_progression_service.compute_progression(db, tenant_id, _identity(barcode), zone="jaw")
        assert result["recurrence_count"] == 3
        assert result["progression"] != "insufficient_history"
        assert result["days_span"] >= 50
    finally:
        db.close()


# ── 2. stable cosmetic discoloration does not trigger removal ────────────────

def test_stable_cosmetic_discoloration_does_not_trigger_removal():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=30)
        for day in (0, 15, 29):
            insp = _mk_inspection(db, tenant_id, barcode=barcode, created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="discoloration", zone="jaw", severity_index=1)

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        assert row.progression == "stable"
        assert row.recommended_disposition != DISPOSITION_REMOVE_FROM_SERVICE
        assert row.reliability_category != RELIABILITY_REMOVE_FROM_SERVICE_CANDIDATE
    finally:
        db.close()


# ── 3. crack progression triggers remove-from-service review ─────────────────

def test_crack_progression_triggers_remove_from_service_review():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=40)
        for day, severity in [(0, 1), (20, 2), (39, 3)]:
            insp = _mk_inspection(db, tenant_id, barcode=barcode, created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="crack", zone="jaw", severity_index=severity)

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        assert row.recommended_disposition == DISPOSITION_REMOVE_FROM_SERVICE
    finally:
        db.close()


# ── 4. repeat failure after repair affects reliability score ─────────────────

def test_repeat_failure_after_repair_affects_reliability_score():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=60)
        insp1 = _mk_inspection(db, tenant_id, barcode=barcode, created_at=base)
        _mk_finding(db, tenant_id, insp1.id, finding_type="corrosion", zone="jaw", severity_index=2)

        return_date = base + timedelta(days=10)
        repair = RepairRequest(
            tenant_id=tenant_id, inspection_id=insp1.id, instrument_identity=_identity(barcode),
            vendor_name="Acme Repair", repair_type="jaw_resurface", status=REPAIR_RETURNED,
            actual_return_date=return_date,
        )
        db.add(repair)
        db.commit()
        db.refresh(repair)

        insp2 = _mk_inspection(db, tenant_id, barcode=barcode, created_at=return_date + timedelta(days=15))
        _mk_finding(db, tenant_id, insp2.id, finding_type="corrosion", zone="jaw", severity_index=2)

        outcome = vulcan_repair_effectiveness_service.classify_repair_outcome(db, tenant_id, repair)
        assert outcome["repair_outcome"] == "failure_recurred"

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        assert "repair_recurrence" in row.score_breakdown_json
    finally:
        db.close()


# ── 5. insufficient history produces limited-confidence result ───────────────

def test_insufficient_history_produces_limited_confidence_result():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        insp = _mk_inspection(db, tenant_id, barcode=barcode)
        _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=1)

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        assert row.progression == "insufficient_history"
        assert row.confidence == "low"
    finally:
        db.close()


# ── 6. drill-bit flute failure uses correct anatomy language ─────────────────

def test_drill_bit_flute_failure_uses_correct_anatomy_language():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=10)
        for day in (0, 5):
            insp = _mk_inspection(db, tenant_id, barcode=barcode, instrument_type="drill bit", created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="bone", zone="flutes", severity_index=2)

        analysis = vulcan_anatomy_zone_service.zone_reliability_analysis(db, tenant_id, _identity(barcode), "drill bit")
        zones = [z["anatomy_zone"] for z in analysis["zones"]]
        assert "flutes" in zones
        flute_zone = next(z for z in analysis["zones"] if z["anatomy_zone"] == "flutes")
        assert flute_zone["recommended_manual_inspection"]

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="drill bit")
        assert "flutes" in row.reasoning_narrative
    finally:
        db.close()


# ── 7. rigid-scope O-ring failure uses correct anatomy language ──────────────

def test_rigid_scope_o_ring_failure_uses_correct_anatomy_language():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=10)
        for day in (0, 5):
            insp = _mk_inspection(db, tenant_id, barcode=barcode, instrument_type="rigid scope", created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="damaged_o_ring", zone="o-ring area", severity_index=2)

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="rigid scope")
        assert row.anatomy_zone == "o-ring area"
        assert row.failure_category == "damaged_o_ring"
        assert "o-ring area" in row.reasoning_narrative
    finally:
        db.close()


# ── 8. probable cause includes alternative explanation ────────────────────────

def test_probable_cause_includes_alternative_explanation():
    causes = vulcan_probable_cause_service.classify_probable_causes("condition_related", recurrence_count=3)
    assert causes
    for cause in causes:
        assert cause["alternative_explanations"]
        assert cause["recommended_verification"]
        assert cause["confidence"]


# ── 9. supervisor can correct failure classification ──────────────────────────

def test_supervisor_can_correct_failure_classification():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        insp = _mk_inspection(db, tenant_id, barcode=barcode)
        _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=2)
        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")

        feedback = vulcan_feedback_service.submit_feedback(
            db, tenant_id, row.id, submitted_by="supervisor@local.dev", submitted_role="spd_manager",
            failure_classification_correct=False, supervisor_rationale="Actually pitting, not corrosion.",
        )
        assert feedback.failure_classification_correct is False

        stored = vulcan_feedback_service.feedback_for_assessment(db, tenant_id, row.id)
        assert len(stored) == 1
        assert stored[0]["failure_classification_correct"] is False
    finally:
        db.close()


# ── 10. repair-vendor feedback is stored as a learning signal ────────────────

def test_repair_vendor_feedback_is_stored_as_learning_signal():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        insp = _mk_inspection(db, tenant_id, barcode=barcode)
        _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=2)
        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")

        feedback = vulcan_feedback_service.submit_feedback(
            db, tenant_id, row.id, submitted_by="vendor@repaircorp.example",
            repair_vendor_response="Repair vendor confirms jaw resurfacing was performed within spec.",
        )
        assert feedback.repair_vendor_response

        stored = vulcan_feedback_service.feedback_for_assessment(db, tenant_id, row.id)
        assert stored[0]["repair_vendor_response"]
    finally:
        db.close()


# ── 11. Vulcan cannot independently finalize irreversible disposition ────────

def test_vulcan_cannot_independently_finalize_disposition():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=40)
        for day, severity in [(0, 1), (20, 2), (39, 3)]:
            insp = _mk_inspection(db, tenant_id, barcode=barcode, created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="crack", zone="jaw", severity_index=severity)

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        assert row.recommended_disposition == DISPOSITION_REMOVE_FROM_SERVICE
        # Vulcan's own compute step never sets final_disposition, no matter how severe.
        assert row.final_disposition == ""
        assert row.finalized_by == ""
        assert row.finalized_at is None

        vulcan_feedback_service.submit_feedback(
            db, tenant_id, row.id, submitted_by="supervisor@local.dev", submitted_role="spd_manager",
            final_disposition=DISPOSITION_REMOVE_FROM_SERVICE, supervisor_rationale="Confirmed via manual inspection.",
        )
        db.refresh(row)
        assert row.final_disposition == DISPOSITION_REMOVE_FROM_SERVICE
        assert row.finalized_by == "supervisor@local.dev"
        assert row.finalized_at is not None
    finally:
        db.close()


# ── 12. Aegis and Vulcan evidence remain separately traceable ────────────────

def test_aegis_and_vulcan_evidence_remain_separately_traceable():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        base = datetime.now(timezone.utc) - timedelta(days=20)
        for day in (0, 5, 10):
            insp = _mk_inspection(db, tenant_id, barcode=barcode, technician="tech-a@local.dev", created_at=base + timedelta(days=day))
            _mk_finding(db, tenant_id, insp.id, finding_type="damaged_drill_flute", zone="flutes", severity_index=2)

        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="drill bit")

        assert row.aegis_conclusion_json
        aegis = vulcan_aegis_integration_service.compute_process_variation_signal(db, tenant_id, _identity(barcode), zone="flutes")
        assert aegis["process_variation_detected"] is True

        # Vulcan's own narrative is untouched by Aegis's signal.
        assert row.reasoning_narrative
        assert row.reasoning_narrative != row.combined_conclusion
        assert row.reasoning_narrative in row.combined_conclusion
        assert aegis["narrative"] not in row.reasoning_narrative
    finally:
        db.close()


# ── Route smoke tests ─────────────────────────────────────────────────────────

def test_assess_endpoint_and_forensics_workspace_route():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
        _seed_membership(db, tenant_id, role="viewer")
        insp = _mk_inspection(db, tenant_id, barcode=barcode)
        _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=2)
    finally:
        db.close()

    r = client.post(
        "/api/vulcan/assess", json={"instrument_identity": _identity(barcode), "instrument_type": "kerrison rongeur"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["recommended_disposition"]
    assert body["human_review_required"] is True

    r2 = client.get(f"/api/vulcan/forensics/{_identity(barcode)}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["latest_assessment"] is not None

    r3 = client.get("/api/vulcan/taxonomy", headers=_headers(AUTH_VIEWER, tenant_id))
    assert r3.status_code == 200
    assert "cleaning_related" in r3.json()["groups"]

    r4 = client.get("/api/vulcan/watchlists", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200
    assert "recurring_corrosion" in r4.json()

    r5 = client.get("/api/vulcan/executive-summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r5.status_code == 200
    assert "human_review_required" in r5.json()


def test_viewer_cannot_submit_feedback():
    tenant_id = uid("vulcan-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
        _seed_membership(db, tenant_id, role="viewer")
        insp = _mk_inspection(db, tenant_id, barcode=barcode)
        _mk_finding(db, tenant_id, insp.id, finding_type="corrosion", zone="jaw", severity_index=2)
        row = vulcan_reliability_agent_service.run_reliability_assessment(db, tenant_id, _identity(barcode), instrument_type="kerrison rongeur")
        assessment_id = row.id
    finally:
        db.close()

    r = client.post(f"/api/vulcan/feedback/{assessment_id}", json={"final_disposition": "remove_from_service"}, headers=_headers(AUTH_VIEWER, tenant_id))
    assert r.status_code == 403
