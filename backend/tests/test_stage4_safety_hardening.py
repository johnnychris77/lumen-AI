"""Pre-merge safety-hardening regression tests for the Stage 4 PR (#162).

These tests pin the specific bypasses closed by the hardening pass. They are
deliberately NEGATIVE/SECURITY-oriented: each asserts that a model, dataset, or
provenance record that lacks the required human-led authorization or tenant
ownership is REFUSED, so a future regression that re-opens a bypass fails here.

No new detector, model architecture, or commercial feature is exercised — only
the existing governance gates.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.model_registry import ModelRegistryEntry
from app.models.retained_image import RetainedImage
from app.services.ml import dataset_registry
from app.services.ml.dataset_split import grouping_is_reliable, has_no_group_leakage, split_dataset
from app.services.ml.live_inference_adapter import (
    HEALTH_ARTIFACT_MISSING,
    HEALTH_NOT_AUTHORIZED,
    HEALTH_NOT_PROMOTED,
    load_active_model,
)
from app.services.ml.lens_model_registration import MODEL_ID
from app.services.ml.provenance_governance import (
    ProvenanceAuthorityError,
    ProvenanceEvidenceError,
    set_provenance_classification,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"
OTHER_TENANT = "other-tenant"


def _valid_metadata(**overrides):
    base = dict(
        instrument_family="scissors", manufacturer="Acme", facility="Test Hospital",
        operator="tech1", capture_device="phone", image_resolution="300x300",
    )
    base.update(overrides)
    return base


def _make_retained(tenant: str, sha256: str) -> int:
    db = SessionLocal()
    try:
        row = RetainedImage(
            tenant_id=tenant, deident_name="hard", instrument_type="scissors",
            content_type="image/png", size_bytes=10, sha256=sha256,
            exif_stripped=True, source="test", consent_recorded=True, uploaded_by="t",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _registered_entry(db, tenant: str):
    """A minimal registered DatasetRegistryEntry declaring real_clinical (PENDING
    until an authorized, evidenced approval)."""
    sha = "e" * 56 + uuid.uuid4().hex[:8]
    rid = _make_retained(tenant, sha)
    v = dataset_registry.create_dataset_version(db, tenant_id=tenant, version_label=f"v-{uuid.uuid4().hex[:8]}")
    return dataset_registry.register_image(
        db, tenant_id=tenant, dataset_version_id=v.id, retained_image_id=rid, image_sha256=sha,
        instrument_family="scissors", manufacturer="Acme", facility="Hosp",
        operator="tech", capture_device="phone", image_resolution="300x300",
        data_provenance_class="real_clinical",
    )


def _add_model(db, tenant, **overrides):
    entry = ModelRegistryEntry(
        tenant_id=tenant,
        model_id=MODEL_ID,
        model_version=f"hard-{uuid.uuid4().hex[:8]}",
        model_type="classification",
        training_status="trained",
        candidate_stage="Candidate",
    )
    for key, value in overrides.items():
        setattr(entry, key, value)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ── Item 1 — live serving requires clinical review + approval + deployment ──

def test_trained_candidate_alone_is_not_served():
    """A model that is merely trained and marked Candidate — the exact state the
    registration pathways produce (approval_status='experimental',
    clinical_review_status='pending', deployment_status='not_deployed') — must
    NOT be served for live clinical inference."""
    tenant = f"hard-cand-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(db, tenant)  # pathway defaults only
        result = load_active_model(db, tenant_id=tenant)
        assert result["status"] == HEALTH_NOT_AUTHORIZED
        assert result["artifact"] is None
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


def test_missing_clinical_review_blocks_serving():
    tenant = f"hard-noreview-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            clinical_review_status="pending",  # not approved
            approval_status="validated",
            deployment_status="deployed",
        )
        result = load_active_model(db, tenant_id=tenant)
        assert result["status"] == HEALTH_NOT_AUTHORIZED
        assert "clinical review" in result["reason"].lower()
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


def test_missing_model_approval_blocks_serving():
    tenant = f"hard-noapprove-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            clinical_review_status="approved",
            approval_status="experimental",  # not pilot/validated
            deployment_status="deployed",
        )
        result = load_active_model(db, tenant_id=tenant)
        assert result["status"] == HEALTH_NOT_AUTHORIZED
        assert "approved to drive" in result["reason"].lower()
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


def test_missing_deployment_authorization_blocks_serving():
    tenant = f"hard-nodeploy-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            clinical_review_status="approved",
            approval_status="validated",
            deployment_status="not_deployed",  # not shadow/deployed
        )
        result = load_active_model(db, tenant_id=tenant)
        assert result["status"] == HEALTH_NOT_AUTHORIZED
        assert "deployment is not authorized" in result["reason"].lower()
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


def test_fully_authorized_model_passes_governance_gate():
    """When all three sign-offs are present the governance gate PASSES — proven
    by the adapter advancing past HEALTH_NOT_AUTHORIZED to the artifact check
    (no artifact on disk here, so HEALTH_ARTIFACT_MISSING). This confirms the
    gate authorizes a legitimately-governed model rather than blocking all."""
    tenant = f"hard-ok-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            clinical_review_status="approved",
            approval_status="validated",
            deployment_status="deployed",
            artifact_path="",  # no real artifact -> next gate, NOT not_authorized
        )
        result = load_active_model(db, tenant_id=tenant)
        assert result["status"] == HEALTH_ARTIFACT_MISSING
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


def test_experimental_stage_still_reports_not_promoted_first():
    """Stage gate remains defense-in-depth: an Experimental model is rejected as
    NOT_PROMOTED before authorization is even considered."""
    tenant = f"hard-exp-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            candidate_stage="Experimental",
            clinical_review_status="approved",
            approval_status="validated",
            deployment_status="deployed",
        )
        result = load_active_model(db, tenant_id=tenant)
        assert result["status"] == HEALTH_NOT_PROMOTED
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


# ── Item 2 — dataset registration cannot reference another tenant's image ───

def test_service_verifier_rejects_cross_tenant_retained_image():
    sha = "x" * 56 + uuid.uuid4().hex[:8]
    rid = _make_retained(OTHER_TENANT, sha)
    db = SessionLocal()
    try:
        with pytest.raises(dataset_registry.CrossTenantImageError):
            dataset_registry.verify_retained_image_for_registration(
                db, tenant_id=TENANT, retained_image_id=rid, image_sha256=sha,
            )
    finally:
        db.query(RetainedImage).filter(RetainedImage.id == rid).delete()
        db.commit()
        db.close()


def test_service_verifier_rejects_sha_mismatch():
    sha = "y" * 56 + uuid.uuid4().hex[:8]
    rid = _make_retained(TENANT, sha)
    db = SessionLocal()
    try:
        with pytest.raises(dataset_registry.ImageIdentityMismatchError):
            dataset_registry.verify_retained_image_for_registration(
                db, tenant_id=TENANT, retained_image_id=rid, image_sha256="z" * 64,
            )
    finally:
        db.query(RetainedImage).filter(RetainedImage.id == rid).delete()
        db.commit()
        db.close()


def test_service_verifier_rejects_missing_retained_image():
    db = SessionLocal()
    try:
        with pytest.raises(dataset_registry.RetainedImageNotFoundError):
            dataset_registry.verify_retained_image_for_registration(
                db, tenant_id=TENANT, retained_image_id=987654321, image_sha256="q" * 64,
            )
    finally:
        db.close()


def test_route_rejects_registering_another_tenants_image():
    """A tenant-authenticated registration that points at another tenant's
    retained image is refused (404 — existence never confirmed)."""
    sha = "a" * 56 + uuid.uuid4().hex[:8]
    rid = _make_retained(OTHER_TENANT, sha)
    try:
        vr = client.post(
            "/api/dataset-registry/versions",
            json={"version_label": f"hard-xtenant-{uuid.uuid4().hex[:6]}"}, headers=AUTH_ADMIN,
        )
        vid = vr.json()["id"]
        r = client.post(
            "/api/dataset-registry/images",
            json={"dataset_version_id": vid, "retained_image_id": rid, "image_sha256": sha, **_valid_metadata()},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 404, r.text
    finally:
        db = SessionLocal()
        db.query(RetainedImage).filter(RetainedImage.id == rid).delete()
        db.commit()
        db.close()


def test_route_rejects_sha_mismatch_on_own_image():
    sha = "b" * 56 + uuid.uuid4().hex[:8]
    rid = _make_retained(TENANT, sha)
    try:
        vr = client.post(
            "/api/dataset-registry/versions",
            json={"version_label": f"hard-sha-{uuid.uuid4().hex[:6]}"}, headers=AUTH_ADMIN,
        )
        vid = vr.json()["id"]
        r = client.post(
            "/api/dataset-registry/images",
            json={"dataset_version_id": vid, "retained_image_id": rid, "image_sha256": "c" * 64, **_valid_metadata()},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 409, r.text
    finally:
        db = SessionLocal()
        db.query(RetainedImage).filter(RetainedImage.id == rid).delete()
        db.commit()
        db.close()


def test_route_accepts_own_image_with_matching_sha():
    sha = "d" * 56 + uuid.uuid4().hex[:8]
    rid = _make_retained(TENANT, sha)
    try:
        vr = client.post(
            "/api/dataset-registry/versions",
            json={"version_label": f"hard-ok-{uuid.uuid4().hex[:6]}"}, headers=AUTH_ADMIN,
        )
        vid = vr.json()["id"]
        r = client.post(
            "/api/dataset-registry/images",
            json={"dataset_version_id": vid, "retained_image_id": rid, "image_sha256": sha, **_valid_metadata()},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 201, r.text
    finally:
        db = SessionLocal()
        db.query(RetainedImage).filter(RetainedImage.id == rid).delete()
        db.commit()
        db.close()


# ── Item 3 — provenance approval authority + mandatory verified evidence ─────

def test_provenance_approval_requires_tenant_identity():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        with pytest.raises(ProvenanceAuthorityError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="admin@x",
                actor_role="admin", approve=True, tenant_id="",  # blank tenant identity
                source_id="S1", source_institution="Inst", rights_evidence_ref="R1",
            )
    finally:
        db.close()


def test_provenance_clinical_approval_requires_verified_evidence():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        # Authorized admin, correct tenant, but NO supporting source/rights
        # evidence — must be refused rather than approved on blank strings.
        with pytest.raises(ProvenanceEvidenceError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="admin@x",
                actor_role="admin", approve=True, tenant_id=tenant,
            )
    finally:
        db.close()


def test_provenance_clinical_approval_requires_rights_evidence_specifically():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        # Source present but rights/licence evidence missing — still refused.
        with pytest.raises(ProvenanceEvidenceError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="admin@x",
                actor_role="admin", approve=True, tenant_id=tenant,
                source_id="HOSP-GT-1", source_institution="St. Example", rights_evidence_ref="",
            )
    finally:
        db.close()


def test_provenance_approval_requires_authenticated_actor():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        with pytest.raises(ProvenanceAuthorityError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="",  # no actor identity
                actor_role="admin", approve=True, tenant_id=tenant,
                source_id="S1", source_institution="Inst", rights_evidence_ref="R1",
            )
    finally:
        db.close()


def test_provenance_fully_evidenced_authorized_approval_succeeds():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        result = set_provenance_classification(
            db, entry=entry, provenance_class="real_clinical", actor="admin@x",
            actor_role="admin", approve=True, tenant_id=tenant,
            source_id="HOSP-GT-42", source_institution="St. Example Hospital",
            rights_evidence_ref="RIGHTS-DOC-42",
        )
        assert result.provenance_approval_status == "approved"
        assert result.provenance_approved_by == "admin@x"
    finally:
        db.close()


# ── Item 4 — split grouping covers specimen/session/repeat; flags unsupported ─

def test_same_specimen_across_inspections_never_straddles_split():
    """Two images of the SAME specimen logged under DIFFERENT inspections must
    stay in one split — single-key (inspection) grouping would miss this."""
    samples = []
    for i in range(40):
        samples.append({
            "id": f"s{i}", "inspection_id": i, "specimen_id": f"SPEC-{i % 10}",
            "instrument_family": "scissors", "finding": "debris", "manufacturer": "M",
        })
    r = split_dataset(samples, seed="spec-seed")
    assert has_no_group_leakage(r)
    by_spec = {}
    for s in samples:
        by_spec.setdefault(s["specimen_id"], set()).add(r["assignments"][s["id"]])
    assert all(len(v) == 1 for v in by_spec.values()), "a specimen straddled the split"


def test_same_session_never_straddles_split():
    samples = [
        {"id": f"s{i}", "session_id": f"SESS-{i % 8}", "instrument_family": "scissors",
         "finding": "debris", "manufacturer": "M"}
        for i in range(40)
    ]
    r = split_dataset(samples, seed="sess-seed")
    by_sess = {}
    for s in samples:
        by_sess.setdefault(s["session_id"], set()).add(r["assignments"][s["id"]])
    assert all(len(v) == 1 for v in by_sess.values())


def test_identical_image_never_straddles_split():
    samples = [
        {"id": f"s{i}", "inspection_id": i, "image_sha256": f"sha-{i % 12}",
         "instrument_family": "scissors", "finding": "debris", "manufacturer": "M"}
        for i in range(48)
    ]
    r = split_dataset(samples, seed="img-seed")
    by_img = {}
    for s in samples:
        by_img.setdefault(s["image_sha256"], set()).add(r["assignments"][s["id"]])
    assert all(len(v) == 1 for v in by_img.values())


def test_cohort_without_grouping_identity_is_flagged_unreliable():
    """A cohort whose samples carry NO real grouping identity (no instrument,
    inspection, specimen, or session) must be reported as unreliable for
    independent validation rather than silently passing as leakage-free."""
    samples = [
        {"id": f"s{i}", "image_sha256": f"only-sha-{i}", "instrument_family": "scissors",
         "finding": "debris", "manufacturer": "M"}
        for i in range(20)
    ]
    r = split_dataset(samples, seed="nogroup-seed")
    assert r["grouping_reliable"] is False
    assert r["ungrouped_sample_count"] == 20
    assert grouping_is_reliable(r) is False


def test_cohort_with_grouping_identity_is_reliable():
    samples = [
        {"id": f"s{i}", "inspection_id": i, "instrument_family": "scissors",
         "finding": "debris", "manufacturer": "M"}
        for i in range(20)
    ]
    r = split_dataset(samples, seed="group-seed")
    assert r["grouping_reliable"] is True
    assert grouping_is_reliable(r) is True
