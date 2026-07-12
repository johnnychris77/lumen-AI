"""LumenAI AI Specialist — Project Veritas: Baseline Governance, Evidence
Integrity & Clinical Data Quality tests.

Covers the 16 named scenarios from the sprint brief's Section 22, plus route
permission smoke tests.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.retained_image import ImageLabel, RetainedImage
from app.services import (
    veritas_baseline_governance_service,
    veritas_baseline_matching_service,
    veritas_baseline_resolution_service,
    veritas_conflict_detection_service,
    veritas_feedback_service,
    veritas_image_quality_service,
    veritas_readiness_score_service,
    veritas_specialist_collaboration_service,
    veritas_training_dataset_service,
)
from app.services.veritas_evidence_agent_service import run_evidence_assessment, to_dict as assessment_to_dict
from app.services.vulcan_aegis_integration_service import compute_process_variation_signal
from app.services.vulcan_reliability_agent_service import run_reliability_assessment
from app.models.inspection_finding import InspectionFinding

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
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


def _mk_inspection(db, tenant_id, *, instrument_type="kerrison rongeur", barcode=None, coverage_pct=None,
                    ai_confidence=None, has_image=True, inspected_zones=None):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="t.jpg", instrument_type=instrument_type, instrument_barcode=barcode,
        coverage_pct=coverage_pct, ai_confidence=ai_confidence, has_image=has_image,
        inspected_zones_json="null" if inspected_zones is None else __import__("json").dumps(inspected_zones),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mk_baseline(db, *, instrument_category, manufacturer="Acme", model="X1", baseline_type="manufacturer", approval_status="approved", baseline_version="1.0"):
    row = BaselineLibraryEntry(
        instrument_category=instrument_category, manufacturer_name=manufacturer, model_name=model,
        baseline_type=baseline_type, approval_status=approval_status, baseline_version=baseline_version,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── 1. approved manufacturer baseline has highest priority ──────────────────

def test_approved_manufacturer_baseline_has_highest_priority():
    category = uid("instr-cat")
    db = SessionLocal()
    try:
        tenant_id = uid("veritas-t")
        _mk_baseline(db, instrument_category=category, baseline_type="vendor", baseline_version="2.0")
        _mk_baseline(db, instrument_category=category, baseline_type="manufacturer", baseline_version="3.0")

        resolution = veritas_baseline_resolution_service.resolve_governed_baseline(db, tenant_id, category)
        assert resolution.baseline_tier == "manufacturer"
        assert resolution.baseline_version == "3.0"
    finally:
        db.close()


# ── 2. unapproved baseline cannot drive final scoring ────────────────────────

def test_unapproved_baseline_cannot_drive_final_scoring():
    category = uid("instr-cat")
    db = SessionLocal()
    try:
        tenant_id = uid("veritas-t")
        _mk_baseline(db, instrument_category=category, approval_status="pending")

        resolution = veritas_baseline_resolution_service.resolve_governed_baseline(db, tenant_id, category)
        assert resolution.resolution_status == "SUPERVISOR_REVIEW_REQUIRED"
        assert "No approved baseline" in resolution.message
        assert veritas_baseline_governance_service.is_usable_for_scoring("pending_review") is False
    finally:
        db.close()


# ── 3. rigid-scope baseline does not match flexible endoscope ───────────────

def test_rigid_scope_baseline_does_not_match_flexible_endoscope():
    result = veritas_baseline_matching_service.classify_match(
        instrument_type="rigid scope", baseline_instrument_category="flexible endoscope",
    )
    assert result["match_classification"] == "mismatch"


# ── 4. anatomy-zone mismatch creates evidence conflict ───────────────────────

def test_anatomy_zone_mismatch_creates_evidence_conflict():
    conflicts = veritas_conflict_detection_service.detect_conflicts(match_classification="mismatch")
    assert any(c["conflict_type"] == "instrument_family_differs_from_baseline" for c in conflicts)

    tag_conflicts = veritas_conflict_detection_service.detect_conflicts(ai_zone="jaw", tagged_zone="o-ring area")
    assert any(c["conflict_type"] == "image_tag_differs_from_predicted_zone" for c in tag_conflicts)


# ── 5. poor image quality requires recapture guidance ────────────────────────

def test_poor_image_quality_requires_recapture_guidance():
    result = veritas_image_quality_service.assess_image_quality(has_image=True, ai_confidence=0.15)
    assert result["quality_status"] == "insufficient"
    assert result["recommended_recapture_steps"]


# ── 6. missing critical zone lowers evidence readiness ──────────────────────

def test_missing_critical_zone_lowers_evidence_readiness():
    complete = veritas_readiness_score_service.compute_evidence_readiness_score(
        match_classification="exact", baseline_governance_status="approved", image_quality_status="excellent",
        coverage_status="complete", instrument_identity_confidence="high", provenance_complete=True,
        supervisor_validated=True, model_compatible=True, has_conflicts=False,
    )
    insufficient_coverage = veritas_readiness_score_service.compute_evidence_readiness_score(
        match_classification="exact", baseline_governance_status="approved", image_quality_status="excellent",
        coverage_status="insufficient", instrument_identity_confidence="high", provenance_complete=True,
        supervisor_validated=True, model_compatible=True, has_conflicts=False,
    )
    assert insufficient_coverage["readiness_score"] < complete["readiness_score"]


# ── 7. complete approved evidence produces strong readiness ─────────────────

def test_complete_approved_evidence_produces_strong_readiness():
    result = veritas_readiness_score_service.compute_evidence_readiness_score(
        match_classification="exact", baseline_governance_status="approved", image_quality_status="excellent",
        coverage_status="complete", instrument_identity_confidence="high", provenance_complete=True,
        supervisor_validated=True, model_compatible=True, has_conflicts=False,
    )
    assert result["readiness_category"] == "strong_evidence"
    assert result["readiness_score"] >= 90


# ── 8. duplicate images are detected ──────────────────────────────────────────

def test_duplicate_images_are_detected():
    tenant_id = uid("veritas-t")
    db = SessionLocal()
    try:
        sha = "a" * 64
        img1 = RetainedImage(tenant_id=tenant_id, sha256=sha, consent_recorded=True, uploaded_by="tech@local.dev", exif_stripped=True)
        img2 = RetainedImage(tenant_id=tenant_id, sha256=sha, consent_recorded=True, uploaded_by="tech@local.dev", exif_stripped=True)
        db.add_all([img1, img2])
        db.commit()
        db.refresh(img1)
        db.refresh(img2)
        db.add(ImageLabel(tenant_id=tenant_id, image_id=img2.id, finding_type="corrosion", severity="moderate", is_gold=True))
        db.commit()

        entry = veritas_training_dataset_service.evaluate_for_training(db, tenant_id, img2.id, usage_rights="internal", image_quality_threshold_met=True)
        assert entry.is_duplicate is True
        assert entry.dataset_status == "quarantined"
    finally:
        db.close()


# ── 9. superseded baseline is not selected ───────────────────────────────────

def test_superseded_baseline_is_not_selected():
    category = uid("instr-cat")
    db = SessionLocal()
    try:
        tenant_id = uid("veritas-t")
        baseline = _mk_baseline(db, instrument_category=category)
        resolution = veritas_baseline_resolution_service.resolve_governed_baseline(db, tenant_id, category)
        assert resolution.baseline_source_id == baseline.id

        veritas_baseline_governance_service.record_governance_action(
            db, tenant_id, baseline_source_type=resolution.baseline_source_type, baseline_source_id=baseline.id,
            action="supersede", performed_by="reviewer@local.dev",
        )
        status = veritas_baseline_governance_service.effective_status(db, tenant_id, resolution.baseline_source_type, baseline.id)
        assert status == "superseded"
        assert veritas_baseline_governance_service.is_usable_for_scoring(status) is False
    finally:
        db.close()


# ── 10. supervisor override requires reason ──────────────────────────────────

def test_supervisor_override_requires_reason():
    tenant_id = uid("veritas-t")
    db = SessionLocal()
    try:
        raised = False
        try:
            veritas_feedback_service.submit_feedback(
                db, tenant_id, action="override_evidence_gate", submitted_by="supervisor@local.dev", override_reason="",
            )
        except veritas_feedback_service.OverrideReasonRequiredError:
            raised = True
        assert raised
    finally:
        db.close()


# ── 11. technician cannot approve baseline ───────────────────────────────────

def test_technician_cannot_approve_baseline():
    tenant_id = uid("veritas-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
        _seed_membership(db, tenant_id, role="operator")
    finally:
        db.close()

    r = client.post(
        "/api/veritas/baselines/baseline_library/1/governance-action", json={"action": "approve"},
        headers=_headers(AUTH_OPERATOR, tenant_id),
    )
    assert r.status_code == 403


# ── 12. viewer cannot override evidence gate ─────────────────────────────────

def test_viewer_cannot_override_evidence_gate():
    tenant_id = uid("veritas-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
        _seed_membership(db, tenant_id, role="viewer")
    finally:
        db.close()

    r = client.post(
        "/api/veritas/feedback", json={"action": "override_evidence_gate", "override_reason": "confirmed manually"},
        headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert r.status_code == 403


# ── 13. training candidate requires supervisor validation ───────────────────

def test_training_candidate_requires_supervisor_validation():
    tenant_id = uid("veritas-t")
    db = SessionLocal()
    try:
        img = RetainedImage(tenant_id=tenant_id, sha256="b" * 64, consent_recorded=True, uploaded_by="tech@local.dev", exif_stripped=True)
        db.add(img)
        db.commit()
        db.refresh(img)
        db.add(ImageLabel(tenant_id=tenant_id, image_id=img.id, finding_type="corrosion", severity="moderate", is_gold=False))
        db.commit()

        entry = veritas_training_dataset_service.evaluate_for_training(db, tenant_id, img.id, usage_rights="internal", image_quality_threshold_met=True)
        assert entry.supervisor_validated is False
        assert entry.dataset_status != "approved_for_training"
    finally:
        db.close()


# ── 14. PHI/rights review status is stored ───────────────────────────────────

def test_phi_rights_review_status_is_stored():
    tenant_id = uid("veritas-t")
    db = SessionLocal()
    try:
        img = RetainedImage(tenant_id=tenant_id, sha256="c" * 64, consent_recorded=True, uploaded_by="tech@local.dev", exif_stripped=True)
        db.add(img)
        db.commit()
        db.refresh(img)
        db.add(ImageLabel(tenant_id=tenant_id, image_id=img.id, finding_type="corrosion", severity="moderate", is_gold=True))
        db.commit()

        entry = veritas_training_dataset_service.evaluate_for_training(db, tenant_id, img.id, usage_rights="research_use", image_quality_threshold_met=True)
        data = veritas_training_dataset_service.to_dict(entry)
        assert data["phi_review_status"] == "cleared"
        assert data["usage_rights"] == "research_use"
    finally:
        db.close()


# ── 15. evidence provenance includes model and baseline versions ────────────

def test_evidence_provenance_includes_model_and_baseline_versions():
    tenant_id = uid("veritas-t")
    barcode = uid("instr")
    db = SessionLocal()
    try:
        _mk_inspection(db, tenant_id, barcode=barcode, coverage_pct=90, ai_confidence=0.9, inspected_zones=["jaw", "serrations", "box lock", "hinge", "spring", "ratchet"])
        insp = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).first()

        row = run_evidence_assessment(db, tenant_id, insp.id, model_version="v1.2.3", dataset_version="ds-2024.06")
        assert row.model_version == "v1.2.3"
        assert row.dataset_version == "ds-2024.06"
    finally:
        db.close()


# ── 16. Aegis, Vulcan, Sage, and Veritas outputs remain separately traceable ─

def test_aegis_vulcan_sage_veritas_outputs_remain_separately_traceable():
    tenant_id = uid("veritas-t")
    barcode = uid("instr")
    identity = f"barcode:{barcode}"
    db = SessionLocal()
    try:
        base = datetime.now(timezone.utc)
        insp1 = models.Inspection(tenant_id=tenant_id, file_name="a.jpg", instrument_type="kerrison rongeur", instrument_barcode=barcode, technician="tech-a@local.dev", coverage_pct=90, ai_confidence=0.9, has_image=True, created_at=base)
        db.add(insp1)
        db.commit()
        db.refresh(insp1)
        db.add(InspectionFinding(tenant_id=tenant_id, inspection_id=insp1.id, finding_type="corrosion", zone="jaw", severity_index=2))
        db.commit()

        vulcan_row = run_reliability_assessment(db, tenant_id, identity, instrument_type="kerrison rongeur")
        aegis_signal = compute_process_variation_signal(db, tenant_id, identity, zone="jaw")

        veritas_row = run_evidence_assessment(db, tenant_id, insp1.id)
        veritas_dict = assessment_to_dict(veritas_row)

        vulcan_support = veritas_specialist_collaboration_service.evidence_support_for_vulcan([veritas_dict])
        aegis_support = veritas_specialist_collaboration_service.evidence_support_for_aegis(aegis_signal, veritas_dict)

        # Each source's evidence is independently present and none was overwritten by another.
        assert vulcan_support["source_veritas_assessment_ids"] == [veritas_row.id]
        assert aegis_support["source_aegis_conclusion"] == aegis_signal
        assert aegis_support["source_veritas_assessment_id"] == veritas_row.id
        assert veritas_row.reasoning_narrative != vulcan_row.reasoning_narrative
    finally:
        db.close()


# ── Route smoke tests ─────────────────────────────────────────────────────────

def test_assess_and_workspace_routes():
    tenant_id = uid("veritas-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
        insp = _mk_inspection(db, tenant_id, coverage_pct=80, ai_confidence=0.8, inspected_zones=["jaw"])
    finally:
        db.close()

    r = client.post(f"/api/veritas/assess/{insp.id}", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 201
    body = r.json()
    assert body["recommended_gate"]
    assert body["human_review_required"] is True

    r2 = client.get("/api/veritas/workspace", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert "evidence_readiness_overview" in r2.json()

    r3 = client.get("/api/veritas/data-quality", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200

    r4 = client.get("/api/veritas/watchlists", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200
    assert "no_approved_baseline" in r4.json()
