"""Stage 6C §2 — authenticated scientific-approval resolution (fail-closed).

Every approval is resolved against authoritative records (UserRoleAssignment,
GovernanceApproval, ConsentRecord). Caller-supplied strings/bools/dicts are never
accepted as proof. Tests cover forged approvers, nonexistent evidence, withdrawn
permissions, and unsupported scientific-readiness claims.
"""
from __future__ import annotations

import uuid

import pytest

from app.db.session import SessionLocal
from app.models.consent_record import ConsentRecord
from app.models.governance_approval import GovernanceApproval
from app.models.user_role_assignment import UserRoleAssignment

from research.lens_vision import checkpoint as ckpt
from research.lens_vision import scientific_authorization as sa
from research.lens_vision.research_acquisition import acquire_research_cohort

TENANT = "stage6c-tenant"


@pytest.fixture()
def db():
    s = SessionLocal()
    created = {"users": [], "approvals": [], "consents": []}
    try:
        yield s, created
    finally:
        for u in created["users"]:
            s.query(UserRoleAssignment).filter(UserRoleAssignment.username == u).delete()
        for a in created["approvals"]:
            s.query(GovernanceApproval).filter(GovernanceApproval.id == a).delete()
        for c in created["consents"]:
            s.query(ConsentRecord).filter(ConsentRecord.id == c).delete()
        s.commit()
        s.close()


def _user(db, created, username, role):
    row = UserRoleAssignment(username=username, role=role)
    db.add(row)
    db.commit()
    created["users"].append(username)
    return row


def _approval(db, created, *, request_type, target_resource_id, status="approved", reviewed_by="dir@x"):
    row = GovernanceApproval(
        tenant_id=TENANT, tenant_name="T", request_type=request_type, target_resource="checkpoint",
        target_resource_id=target_resource_id, requested_by="req@x", status=status, reviewed_by=reviewed_by,
    )
    db.add(row)
    db.commit()
    created["approvals"].append(row.id)
    return row


def _consent(db, created, *, consent_type="benchmarking_contribution", granted=True, withdrawn=False):
    import datetime as dt
    row = ConsentRecord(
        id=str(uuid.uuid4()), tenant_id=TENANT, user_email="owner@x", consent_type=consent_type,
        granted=granted, withdrawn_at=(dt.datetime.now(dt.timezone.utc) if withdrawn else None),
    )
    db.add(row)
    db.commit()
    created["consents"].append(row.id)
    return row


# ── approver role resolution ─────────────────────────────────────────────────

def test_forged_or_unknown_approver_rejected(db):
    s, created = db
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_role(s, "ghost@x", allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES)   # no record
    _user(s, created, "viewer@x", "viewer")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_role(s, "viewer@x", allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES)  # wrong role
    _user(s, created, "dir@x", "quality_director")
    assert sa.resolve_role(s, "dir@x", allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES) == "quality_director"


# ── governance-approval (evidence) resolution ────────────────────────────────

def test_nonexistent_or_unapproved_evidence_rejected(db):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    with pytest.raises(sa.ScientificAuthorizationError):               # no record
        sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                       target_resource_id="LIC-missing")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-1", status="pending")
    with pytest.raises(sa.ScientificAuthorizationError):               # pending, not approved
        sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                       target_resource_id="LIC-1")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-2",
              status="approved", reviewed_by="dir@x")
    rec = sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                         target_resource_id="LIC-2")
    assert rec.status == "approved"


def test_approval_reviewed_by_unauthenticated_reviewer_rejected(db):
    s, created = db
    # Reviewer 'rogue@x' has no role assignment -> approval cannot be trusted.
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-3",
              status="approved", reviewed_by="rogue@x")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                       target_resource_id="LIC-3")


# ── data authorization: approval + non-withdrawn consent ─────────────────────

def test_data_authorization_requires_approval_and_live_consent(db):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_DATA_AUTHORIZATION, target_resource_id="DS-1",
              reviewed_by="dir@x")
    # No consent yet -> blocked.
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.verify_data_authorization(s, tenant_id=TENANT, user_email="owner@x", dataset_id="DS-1")
    c = _consent(s, created, granted=True, withdrawn=False)
    sa.verify_data_authorization(s, tenant_id=TENANT, user_email="owner@x", dataset_id="DS-1")  # ok
    # Withdraw consent -> blocked again.
    import datetime as dt
    c.withdrawn_at = dt.datetime.now(dt.timezone.utc)
    s.commit()
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.verify_data_authorization(s, tenant_id=TENANT, user_email="owner@x", dataset_id="DS-1")


# ── statistical reviewer sign-off ────────────────────────────────────────────

def test_statistical_signoff_resolved_from_records(db):
    s, created = db
    _user(s, created, "stat@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_STATISTICAL_PROTOCOL, target_resource_id="PROTO-1",
              reviewed_by="stat@x")
    out = sa.verify_statistical_signoff(s, reviewer_username="stat@x", tenant_id=TENANT, protocol_id="PROTO-1")
    assert out["resolved"] is True and out["reviewer"] == "stat@x"
    # A different (unauthorized) reviewer cannot claim the sign-off.
    _user(s, created, "tech@x", "technician")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.verify_statistical_signoff(s, reviewer_username="tech@x", tenant_id=TENANT, protocol_id="PROTO-1")


# ── register scientific checkpoint resolves records ──────────────────────────

def test_register_scientific_checkpoint_resolves_records(db, tmp_path):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-9", reviewed_by="dir@x")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_SOURCE, target_resource_id="SRC-9", reviewed_by="dir@x")
    w = tmp_path / "rn18.pt"
    w.write_bytes(b"real-weights")
    rec = sa.register_scientific_checkpoint(
        s, "sci_ckpt_6c", file_path=str(w), architecture="resnet18", tenant_id=TENANT,
        approver_username="dir@x", license_approval_id="LIC-9", source_approval_id="SRC-9",
        license="Apache-2.0", source_url="https://example/model")
    assert rec.scientific_use_approved is True and rec.rights_cleared is True
    ckpt.assert_scientific_checkpoint(rec)
    # Missing source approval -> fail-closed.
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.register_scientific_checkpoint(
            s, "sci_ckpt_6c_bad", file_path=str(w), architecture="resnet18", tenant_id=TENANT,
            approver_username="dir@x", license_approval_id="LIC-9", source_approval_id="SRC-missing")
    del ckpt._REGISTRY["sci_ckpt_6c"]


# ── overall readiness assessment: fail-closed, no caller bool accepted ────────

def test_assess_readiness_blocks_without_records_then_resolves(db, tmp_path):
    s, created = db
    r = sa.assess_scientific_readiness(
        s, tenant_id=TENANT, dataset_id="DS-7", dataset_owner_email="owner@x",
        checkpoint_id="smoke_stub", statistical_reviewer_username="stat@x", statistical_protocol_id="PROTO-7")
    assert r["ready_for_scientific_benchmark"] is False
    assert all(isinstance(v, str) for v in r["checks"].values())
    assert r["checks"]["data_authorization"].startswith("BLOCKED")
    # smoke_stub is approved but NOT scientific -> scientific_checkpoint blocked.
    assert r["checks"]["scientific_checkpoint"].startswith("BLOCKED")

    # Now satisfy every record-backed prerequisite.
    _user(s, created, "dir@x", "quality_director")
    _user(s, created, "stat@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_DATA_AUTHORIZATION, target_resource_id="DS-7", reviewed_by="dir@x")
    _approval(s, created, request_type=sa.REQ_STATISTICAL_PROTOCOL, target_resource_id="PROTO-7", reviewed_by="stat@x")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-7", reviewed_by="dir@x")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_SOURCE, target_resource_id="SRC-7", reviewed_by="dir@x")
    _consent(s, created, granted=True, withdrawn=False)
    w = tmp_path / "rn18.pt"
    w.write_bytes(b"real-weights-7")
    sa.register_scientific_checkpoint(
        s, "sci_ckpt_ready", file_path=str(w), architecture="resnet18", tenant_id=TENANT,
        approver_username="dir@x", license_approval_id="LIC-7", source_approval_id="SRC-7")
    r2 = sa.assess_scientific_readiness(
        s, tenant_id=TENANT, dataset_id="DS-7", dataset_owner_email="owner@x",
        checkpoint_id="sci_ckpt_ready", statistical_reviewer_username="stat@x", statistical_protocol_id="PROTO-7")
    assert r2["ready_for_scientific_benchmark"] is True
    del ckpt._REGISTRY["sci_ckpt_ready"]


# ── §3 acquisition workflow is authorization-gated ───────────────────────────

def test_acquisition_blocked_without_authorization(db):
    s, _ = db
    out = acquire_research_cohort(
        s, [{"image_id": "a"}], tenant_id=TENANT, dataset_id="DS-NA", dataset_owner_email="owner@x")
    assert out["status"] == "BLOCKED_ACQUISITION" and out["imported"] == 0
    assert out["authorization"].startswith("BLOCKED")


def test_acquisition_authorized_reports_quality_without_importing(db):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_DATA_AUTHORIZATION, target_resource_id="DS-OK", reviewed_by="dir@x")
    _consent(s, created, granted=True, withdrawn=False)
    manifest = [{
        "image_id": "a", "image_sha256": "a" * 64, "instrument_id": "I1", "specimen_id": "S1",
        "modality": "external_camera", "anatomy_zone": "hinge", "imaging_session_id": "SE1",
        "imaging_device": "cam", "data_provenance_class": "external_nonclinical",
        "institutional_authorization_ref": "IRB", "data_rights": "research", "retention_status": "active",
        "study_batch_id": "B1", "split": "fit", "ground_truth_status": "verified_normal",
        "label_reviewer_id": "rev@x", "specimen_category": "verified_clean",
    }]
    out = acquire_research_cohort(
        s, manifest, tenant_id=TENANT, dataset_id="DS-OK", dataset_owner_email="owner@x")
    assert out["status"] == "AUTHORIZED" and out["imported"] == 0       # authorized but ingests nothing here
    assert out["n_contract_valid"] == 1
    assert "measured_pitting" in out["missing_specimen_categories"]     # feasibility cohort incomplete
