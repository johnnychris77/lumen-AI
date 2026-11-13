"""Stage 6C/6D — authenticated scientific-approval resolution (fail-closed).

Every approval resolves against authoritative records (UserRoleAssignment,
GovernanceApproval, ConsentRecord, VeritasEvidenceProvenanceRecord) and binds to the
authenticated AuthContext. Covers forged approvers, nonexistent/unapproved evidence,
withdrawn permissions, impersonation, use-scope, dataset-specific authorization, and
record-backed laboratory confirmation.
"""
from __future__ import annotations

import datetime as dt
import json
import uuid

import pytest

from app.auth.context import AuthContext
from app.db.session import SessionLocal
from app.models.consent_record import ConsentRecord
from app.models.governance_approval import GovernanceApproval
from app.models.user_role_assignment import UserRoleAssignment

from research.lens_vision import checkpoint as ckpt
from research.lens_vision import scientific_authorization as sa
from research.lens_vision.research_acquisition import acquire_research_cohort

TENANT = "stage6c-tenant"


def _auth(actor, role, tenant=TENANT):
    return AuthContext(actor=actor, role=role, tenant_id=tenant)


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
    db.add(UserRoleAssignment(username=username, role=role))
    db.commit()
    created["users"].append(username)


def _approval(db, created, *, request_type, target_resource_id, status="approved", reviewed_by="dir@x",
              use_scope=None):
    payload = json.dumps({"use_scope": use_scope}) if use_scope else ""
    row = GovernanceApproval(
        tenant_id=TENANT, tenant_name="T", request_type=request_type, target_resource="x",
        target_resource_id=target_resource_id, requested_by="req@x", status=status,
        reviewed_by=reviewed_by, requested_payload=payload,
    )
    db.add(row)
    db.commit()
    created["approvals"].append(row.id)
    return row


def _consent(db, created, *, granted=True, withdrawn=False):
    row = ConsentRecord(
        id=str(uuid.uuid4()), tenant_id=TENANT, user_email="owner@x", consent_type="benchmarking_contribution",
        granted=granted, withdrawn_at=(dt.datetime.now(dt.timezone.utc) if withdrawn else None),
    )
    db.add(row)
    db.commit()
    created["consents"].append(row.id)
    return row


def _grant_full_data_auth(db, created, dataset_id="DS-1"):
    _user(db, created, "dir@x", "quality_director")
    _approval(db, created, request_type=sa.REQ_DATA_AUTHORIZATION, target_resource_id=dataset_id, reviewed_by="dir@x")
    _approval(db, created, request_type=sa.REQ_RESEARCH_CONSENT, target_resource_id=dataset_id, reviewed_by="dir@x")
    _consent(db, created, granted=True, withdrawn=False)


# ── approver role + authenticated-context binding ────────────────────────────

def test_forged_or_unknown_approver_rejected(db):
    s, created = db
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_role(s, "ghost@x", allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES)
    _user(s, created, "viewer@x", "viewer")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_role(s, "viewer@x", allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES)
    _user(s, created, "dir@x", "quality_director")
    assert sa.authorize_scientific_actor(
        s, _auth("dir@x", "quality_director"), allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES) == "dir@x"


def test_impersonation_via_mismatched_context_rejected(db):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    # A context that claims admin role for an actor recorded as quality_director.
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.authorize_scientific_actor(s, _auth("dir@x", "admin"), allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES)
    # A context whose actor has no role record at all.
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.authorize_scientific_actor(s, _auth("ghost@x", "admin"), allowed_roles=sa.SCIENTIFIC_APPROVER_ROLES)


# ── governance-approval resolution (status, authority, use scope) ────────────

def test_nonexistent_or_unapproved_or_unauthenticated_evidence_rejected(db):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                       target_resource_id="LIC-missing")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-1", status="pending")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                       target_resource_id="LIC-1")
    # Approved but reviewer has no authenticated role.
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-rogue",
              reviewed_by="rogue@x")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                       target_resource_id="LIC-rogue")


def test_use_scope_enforced(db):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-noscope", reviewed_by="dir@x")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                       target_resource_id="LIC-noscope", required_use_scope=sa.USE_SCOPE_SCIENTIFIC)
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-scope",
              reviewed_by="dir@x", use_scope=sa.USE_SCOPE_SCIENTIFIC)
    rec = sa.resolve_governance_approval(s, tenant_id=TENANT, request_type=sa.REQ_CHECKPOINT_LICENSE,
                                         target_resource_id="LIC-scope", required_use_scope=sa.USE_SCOPE_SCIENTIFIC)
    assert rec.status == "approved"


# ── dataset-specific data authorization ──────────────────────────────────────

def test_data_authorization_is_dataset_specific(db):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    # Only institutional approval + tenant consent, but NO dataset-scoped consent record.
    _approval(s, created, request_type=sa.REQ_DATA_AUTHORIZATION, target_resource_id="DS-1", reviewed_by="dir@x")
    _consent(s, created, granted=True, withdrawn=False)
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.verify_data_authorization(s, tenant_id=TENANT, dataset_id="DS-1")
    # Add the dataset-scoped research-use consent record -> resolves.
    _approval(s, created, request_type=sa.REQ_RESEARCH_CONSENT, target_resource_id="DS-1", reviewed_by="dir@x")
    sa.verify_data_authorization(s, tenant_id=TENANT, dataset_id="DS-1")


def test_withdrawn_tenant_consent_blocks(db):
    s, created = db
    _grant_full_data_auth(s, created, "DS-2")
    sa.verify_data_authorization(s, tenant_id=TENANT, dataset_id="DS-2")  # ok
    # Withdraw tenant consent.
    for cid in created["consents"]:
        row = s.query(ConsentRecord).filter(ConsentRecord.id == cid).first()
        row.withdrawn_at = dt.datetime.now(dt.timezone.utc)
    s.commit()
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.verify_data_authorization(s, tenant_id=TENANT, dataset_id="DS-2")


def test_cross_tenant_authorization_rejected(db):
    s, created = db
    _grant_full_data_auth(s, created, "DS-3")
    # A different tenant cannot use this tenant's dataset authorization.
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.verify_data_authorization(s, tenant_id="other-tenant", dataset_id="DS-3")


# ── statistical sign-off bound to authenticated context ──────────────────────

def test_statistical_signoff_requires_authenticated_reviewer(db):
    s, created = db
    _user(s, created, "stat@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_STATISTICAL_PROTOCOL, target_resource_id="PROTO-1", reviewed_by="stat@x")
    out = sa.verify_statistical_signoff(s, auth=_auth("stat@x", "quality_director"), tenant_id=TENANT,
                                        protocol_id="PROTO-1")
    assert out["resolved"] is True
    # A different authenticated actor cannot claim the sign-off.
    _user(s, created, "tech@x", "technician")
    with pytest.raises(sa.ScientificAuthorizationError):
        sa.verify_statistical_signoff(s, auth=_auth("tech@x", "technician"), tenant_id=TENANT, protocol_id="PROTO-1")


# ── scientific checkpoint registration ───────────────────────────────────────

def test_register_scientific_checkpoint_resolves_records(db, tmp_path):
    s, created = db
    _user(s, created, "dir@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-9",
              reviewed_by="dir@x", use_scope=sa.USE_SCOPE_SCIENTIFIC)
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_SOURCE, target_resource_id="SRC-9",
              reviewed_by="dir@x", use_scope=sa.USE_SCOPE_SCIENTIFIC)
    w = tmp_path / "rn18.pt"
    w.write_bytes(b"real-weights")
    rec = sa.register_scientific_checkpoint(
        s, "sci_ckpt_6c", file_path=str(w), architecture="resnet18", tenant_id=TENANT,
        auth=_auth("dir@x", "quality_director"), license_approval_id="LIC-9", source_approval_id="SRC-9",
        license="Apache-2.0", source_url="https://example/model")
    assert rec.scientific_use_approved is True
    ckpt.assert_scientific_checkpoint(rec)
    with pytest.raises(sa.ScientificAuthorizationError):      # missing source -> fail-closed
        sa.register_scientific_checkpoint(
            s, "sci_ckpt_bad", file_path=str(w), architecture="resnet18", tenant_id=TENANT,
            auth=_auth("dir@x", "quality_director"), license_approval_id="LIC-9", source_approval_id="SRC-missing")
    del ckpt._REGISTRY["sci_ckpt_6c"]


# ── overall readiness assessment ─────────────────────────────────────────────

def test_assess_readiness_blocks_then_resolves(db, tmp_path):
    s, created = db
    r = sa.assess_scientific_readiness(
        s, tenant_id=TENANT, dataset_id="DS-7", checkpoint_id="smoke_stub",
        statistical_auth=None, statistical_protocol_id="PROTO-7")
    assert r["ready_for_scientific_benchmark"] is False
    assert r["checks"]["scientific_checkpoint"].startswith("BLOCKED")

    _user(s, created, "dir@x", "quality_director")
    _approval(s, created, request_type=sa.REQ_DATA_AUTHORIZATION, target_resource_id="DS-7", reviewed_by="dir@x")
    _approval(s, created, request_type=sa.REQ_RESEARCH_CONSENT, target_resource_id="DS-7", reviewed_by="dir@x")
    _approval(s, created, request_type=sa.REQ_STATISTICAL_PROTOCOL, target_resource_id="PROTO-7", reviewed_by="dir@x")
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_LICENSE, target_resource_id="LIC-7",
              reviewed_by="dir@x", use_scope=sa.USE_SCOPE_SCIENTIFIC)
    _approval(s, created, request_type=sa.REQ_CHECKPOINT_SOURCE, target_resource_id="SRC-7",
              reviewed_by="dir@x", use_scope=sa.USE_SCOPE_SCIENTIFIC)
    _consent(s, created, granted=True, withdrawn=False)
    w = tmp_path / "rn18.pt"
    w.write_bytes(b"real-weights-7")
    sa.register_scientific_checkpoint(
        s, "sci_ckpt_ready", file_path=str(w), architecture="resnet18", tenant_id=TENANT,
        auth=_auth("dir@x", "quality_director"), license_approval_id="LIC-7", source_approval_id="SRC-7")
    r2 = sa.assess_scientific_readiness(
        s, tenant_id=TENANT, dataset_id="DS-7", checkpoint_id="sci_ckpt_ready",
        statistical_auth=_auth("dir@x", "quality_director"), statistical_protocol_id="PROTO-7")
    assert r2["ready_for_scientific_benchmark"] is True
    del ckpt._REGISTRY["sci_ckpt_ready"]


# ── §3/§4 acquisition is authorization-gated ─────────────────────────────────

def test_acquisition_blocked_without_authorization(db):
    s, _ = db
    out = acquire_research_cohort(s, [{"image_id": "a"}], tenant_id=TENANT, dataset_id="DS-NA")
    assert out["status"] == "BLOCKED_ACQUISITION" and out["imported"] == 0


def test_acquisition_authorized_imports_zero_without_bytes(db):
    s, created = db
    _grant_full_data_auth(s, created, "DS-OK")
    manifest = [{
        "image_id": "a", "image_sha256": "a" * 64, "instrument_id": "I1", "specimen_id": "S1",
        "modality": "external_camera", "anatomy_zone": "hinge", "imaging_session_id": "SE1",
        "imaging_device": "cam", "data_provenance_class": "external_nonclinical",
        "institutional_authorization_ref": "IRB", "data_rights": "research", "retention_status": "active",
        "study_batch_id": "B1", "split": "fit", "ground_truth_status": "verified_normal",
        "label_reviewer_id": "rev@x", "specimen_category": "verified_clean",
    }]
    out = acquire_research_cohort(s, manifest, tenant_id=TENANT, dataset_id="DS-OK", import_images=True)
    assert out["status"] == "AUTHORIZED"
    assert out["imported"] == 0                                  # no bytes -> nothing imported
    assert out["ingestion"][0]["reason"] == "no_bytes_present"
    assert "measured_pitting" in out["missing_specimen_categories"]
