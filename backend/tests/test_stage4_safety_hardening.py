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
    HEALTH_SHADOW_ONLY,
    load_active_model,
    predict as live_predict,
    shadow_evaluate,
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


def _grant_governance_role(db, actor="admin@x", role="admin"):
    from app.models.user_role_assignment import UserRoleAssignment
    if db.query(UserRoleAssignment).filter(UserRoleAssignment.username == actor).first() is None:
        db.add(UserRoleAssignment(username=actor, role=role))
        db.commit()


def _clinical_evidence_records(db, tenant):
    from app.models.consent_record import ConsentRecord
    from app.models.veritas_evidence import VeritasEvidenceProvenanceRecord
    src = VeritasEvidenceProvenanceRecord(
        tenant_id=tenant, evidence_type="clinical_image", source="hospital-ground-truth",
        organization="St. Example Hospital",
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    consent = ConsentRecord(
        id=str(uuid.uuid4()), tenant_id=tenant, user_email="deident@example",
        consent_type="regulatory_evidence", jurisdiction="us", granted=True,
    )
    db.add(consent)
    db.commit()
    return str(src.id), consent.id


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


def test_shadow_only_model_is_not_actionable_via_predict():
    """A model authorized only for shadow evaluation (deployment_status=shadow)
    must never reach the technician-facing clinical path: load_active_model on
    the actionable path reports HEALTH_SHADOW_ONLY and predict() returns a
    non-actionable ai_unavailable contract with no observation."""
    tenant = f"hard-shadow-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            clinical_review_status="approved",
            approval_status="validated",
            deployment_status="shadow",
        )
        loaded = load_active_model(db, tenant_id=tenant)  # actionable path (default)
        assert loaded["status"] == HEALTH_SHADOW_ONLY
        result = live_predict(db, tenant_id=tenant, image_bytes=None)
        assert result["analysis_status"] == "ai_unavailable"
        assert result["model"]["status"] == HEALTH_SHADOW_ONLY
        assert result["observation"] is None
        assert result["human_review_required"] is True
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


def test_shadow_model_loadable_in_shadow_eval_mode_only():
    """The SAME shadow model is loadable on the shadow-evaluation path
    (require_actionable=False) — it passes authorization there (reaching the
    artifact check) — and shadow_evaluate never returns an actionable payload."""
    tenant = f"hard-shadoweval-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            clinical_review_status="approved",
            approval_status="validated",
            deployment_status="shadow",
        )
        # Shadow-eval path passes governance and proceeds to the artifact check
        # (no artifact on disk here) — i.e. it is NOT blocked as shadow_only.
        loaded = load_active_model(db, tenant_id=tenant, require_actionable=False)
        assert loaded["status"] == HEALTH_ARTIFACT_MISSING
        ev = shadow_evaluate(db, tenant_id=tenant, image_bytes=None)
        assert ev["actionable"] is False
        assert ev["clinical_recommendation_shown"] is False
        assert "analysis_status" not in ev and "observation" not in ev
    finally:
        db.query(ModelRegistryEntry).filter(ModelRegistryEntry.tenant_id == tenant).delete()
        db.commit()
        db.close()


def test_deployed_model_remains_actionable():
    """A deployed, reviewed, approved model still passes the actionable gate
    (reaching the artifact check), so the hardening does not over-block."""
    tenant = f"hard-deployed-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        _add_model(
            db, tenant,
            clinical_review_status="approved",
            approval_status="validated",
            deployment_status="deployed",
        )
        loaded = load_active_model(db, tenant_id=tenant)
        assert loaded["status"] == HEALTH_ARTIFACT_MISSING  # passed governance
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
        _grant_governance_role(db)
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
        _grant_governance_role(db)
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
        _grant_governance_role(db)
        source_id, rights_ref = _clinical_evidence_records(db, tenant)
        result = set_provenance_classification(
            db, entry=entry, provenance_class="real_clinical", actor="admin@x",
            actor_role="admin", approve=True, tenant_id=tenant,
            source_id=source_id, source_institution="St. Example Hospital",
            rights_evidence_ref=rights_ref,
        )
        assert result.provenance_approval_status == "approved"
        assert result.provenance_approved_by == "admin@x"
    finally:
        db.close()


# ── T1.2 — approval requires verifiable authorized source/rights + real role ──

def test_approval_rejects_unresolvable_source_record():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        _grant_governance_role(db)
        _, rights_ref = _clinical_evidence_records(db, tenant)
        with pytest.raises(ProvenanceEvidenceError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="admin@x",
                actor_role="admin", approve=True, tenant_id=tenant,
                source_id="999999999", source_institution="St. Example",  # no such record
                rights_evidence_ref=rights_ref,
            )
    finally:
        db.close()


def test_approval_rejects_unresolvable_rights_record():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        _grant_governance_role(db)
        source_id, _ = _clinical_evidence_records(db, tenant)
        with pytest.raises(ProvenanceEvidenceError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="admin@x",
                actor_role="admin", approve=True, tenant_id=tenant,
                source_id=source_id, source_institution="St. Example",
                rights_evidence_ref=str(uuid.uuid4()),  # no such consent record
            )
    finally:
        db.close()


def test_approval_rejects_withdrawn_rights_record():
    from app.models.consent_record import ConsentRecord
    from app.models.veritas_evidence import VeritasEvidenceProvenanceRecord
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        _grant_governance_role(db)
        from datetime import datetime, timezone
        src = VeritasEvidenceProvenanceRecord(tenant_id=tenant, evidence_type="clinical_image", source="h")
        db.add(src)
        db.commit()
        db.refresh(src)
        consent = ConsentRecord(
            id=str(uuid.uuid4()), tenant_id=tenant, user_email="d@x",
            consent_type="regulatory_evidence", granted=True,
            withdrawn_at=datetime.now(timezone.utc),  # withdrawn
        )
        db.add(consent)
        db.commit()
        with pytest.raises(ProvenanceEvidenceError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="admin@x",
                actor_role="admin", approve=True, tenant_id=tenant,
                source_id=str(src.id), source_institution="H", rights_evidence_ref=consent.id,
            )
    finally:
        db.close()


def test_approval_rejects_actor_without_authenticated_role():
    """A caller-supplied role is not proof: an actor with no UserRoleAssignment
    cannot approve, even claiming actor_role='admin'."""
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        source_id, rights_ref = _clinical_evidence_records(db, tenant)
        with pytest.raises(ProvenanceAuthorityError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="ghost@x",  # no role record
                actor_role="admin", approve=True, tenant_id=tenant,
                source_id=source_id, source_institution="H", rights_evidence_ref=rights_ref,
            )
    finally:
        db.close()


def test_approval_rejects_role_claim_mismatching_authenticated_role():
    tenant = f"prov-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        entry = _registered_entry(db, tenant)
        _grant_governance_role(db, actor="spd@x", role="spd_manager")
        source_id, rights_ref = _clinical_evidence_records(db, tenant)
        with pytest.raises(ProvenanceAuthorityError):
            set_provenance_classification(
                db, entry=entry, provenance_class="real_clinical", actor="spd@x",
                actor_role="admin",  # claims admin but authenticated role is spd_manager
                approve=True, tenant_id=tenant,
                source_id=source_id, source_institution="H", rights_evidence_ref=rights_ref,
            )
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


# ── T1.3 — identities propagate through Canvas→Lens; promotion needs grouping ──

def test_to_split_sample_propagates_grouping_identities():
    from app.services.ml.lens_training_pipeline import _to_split_sample
    out = _to_split_sample({
        "id": 1, "inspection_id": 7, "digital_twin_id": "SER-123",
        "specimen_id": "SPEC-9", "session_id": "SESS-3", "image_sha256": "abc123",
        "label": "probable_retained_debris",
    })
    assert out["specimen_id"] == "SPEC-9"
    assert out["session_id"] == "SESS-3"
    assert out["image_sha256"] == "abc123"
    assert out["instrument_serial"] == "SER-123"
    assert out["inspection_id"] == 7


def _png(seed: int) -> bytes:
    import io
    import random
    from PIL import Image
    rnd = random.Random(seed)
    raw = bytes(rnd.getrandbits(8) for _ in range(48 * 48 * 3))
    buf = io.BytesIO()
    Image.frombytes("RGB", (48, 48), raw).save(buf, format="PNG")
    return buf.getvalue()


def _lens_eligibility(grouped: bool):
    from app.services.ml.lens_training_pipeline import NEGATIVE_LABEL
    pos = "probable_retained_debris"
    samples = []
    sid = 0
    for label in (pos, NEGATIVE_LABEL):
        for _ in range(6):
            sample = {
                "id": sid, "label": label, "image_bytes": _png(sid),
                "image_sha256": f"lenssha-{sid}",
                "instrument_family": "scissors", "anatomy_zone": "hinge",
                "manufacturer": "Acme", "image_quality": "Good",
                # Grouped: each sample anchored to a real inspection identity.
                # Ungrouped: no instrument/inspection/specimen/session identity.
                "inspection_id": sid if grouped else None,
                "specimen_id": f"SPEC-{sid}" if grouped else "",
                "digital_twin_id": "",
                "session_id": None,
            }
            samples.append(sample)
            sid += 1
    return {
        "samples": samples,
        "eligible_classes": [pos, NEGATIVE_LABEL],
        "label_counts": {pos: 6, NEGATIVE_LABEL: 6},
        "excluded_classes": [],
        "data_provenance": "real_clinical",
        "clinical_promotion_eligible": True,
    }


def test_lens_run_clinical_promotion_requires_reliable_grouping():
    """A provenance-clinical-eligible cohort whose samples lack real grouping
    identity must NOT be clinically promotable from the run (grouping gate),
    while a reliably-grouped cohort is."""
    from app.services.ml.lens_training_pipeline import run_lens_training
    from app.services.ml.training_config import TrainingConfig

    ungrouped = run_lens_training(_lens_eligibility(grouped=False), config=TrainingConfig(seed=3, epochs=40))
    assert ungrouped["training_status"] == "trained"
    assert ungrouped["grouping_reliable"] is False
    assert ungrouped["provenance_clinical_promotion_eligible"] is True
    assert ungrouped["clinical_promotion_eligible"] is False  # grouping gate blocks it

    grouped = run_lens_training(_lens_eligibility(grouped=True), config=TrainingConfig(seed=3, epochs=40))
    assert grouped["training_status"] == "trained"
    assert grouped["grouping_reliable"] is True
    assert grouped["clinical_promotion_eligible"] is True
