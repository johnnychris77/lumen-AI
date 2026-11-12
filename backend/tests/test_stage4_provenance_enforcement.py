"""Stage 4 — Data Provenance Enforcement regression suite.

Covers: each provenance category, missing/forged provenance, legacy records,
rights, cross-tenant denial, mixed cohorts, research-only vs clinical eligibility,
failed clinical promotion from external data, self-declared real_clinical,
no automatic Candidate advancement, and migration/compatibility.
"""
import io
import uuid

import pytest
from PIL import Image

from app.db.session import SessionLocal
from app.models.annotation_database import GROUND_TRUTH_ACTIVE, Annotation
from app.models.dataset_governance import (
    PROVENANCE_APPROVAL_APPROVED,
    PROVENANCE_APPROVAL_PENDING,
    PROVENANCE_LEGACY_UNVERIFIED,
)
from app.services.ml import dataset_registry
from app.services.ml.candidate_training import TrainingConfig, run_full_candidate_pipeline
from app.services.ml.lens_model_registration import register_lens_model
from app.services.ml.provenance_governance import (
    ProvenanceAuthorityError,
    clinical_exclusion_reason,
    is_clinical_evidence,
    normalize_provenance_class,
    set_provenance_classification,
    summarize_cohort_provenance,
)
from app.services.ml.training_eligibility_service import compute_training_eligibility


def _png(seed: int) -> bytes:
    import random
    rnd = random.Random(seed)
    raw = bytes(rnd.getrandbits(8) for _ in range(64 * 64 * 3))
    buf = io.BytesIO()
    Image.frombytes("RGB", (64, 64), raw).save(buf, format="PNG")
    return buf.getvalue()


def _retained(db, tenant, sha):
    from app.models.retained_image import RetainedImage
    r = RetainedImage(
        tenant_id=tenant, deident_name="t", instrument_type="scissors", content_type="image/png",
        size_bytes=10, sha256=sha, exif_stripped=True, source="test", consent_recorded=True,
        uploaded_by="t", image_bytes=_png(hash(sha) % 9999),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _entry(db, tenant, *, provenance_class="", approve=False, label="probable_retained_debris", serial="SER-1",
           usage_rights="internal_use", phi="verified"):
    sha = uuid.uuid4().hex
    r = _retained(db, tenant, sha)
    v = dataset_registry.create_dataset_version(db, tenant_id=tenant, version_label=f"v-{uuid.uuid4().hex[:8]}")
    entry = dataset_registry.register_image(
        db, tenant_id=tenant, dataset_version_id=v.id, retained_image_id=r.id, image_sha256=sha,
        instrument_family="scissors", instrument_model="X1", manufacturer="Acme", facility="Test Hospital",
        operator="tech", capture_device="phone", image_resolution="300x300",
        instrument_id=serial, anatomy_zone="hinge",
        usage_rights=usage_rights, phi_verification=phi, data_provenance_class=provenance_class,
    )
    entry.image_quality = "Good"
    entry.current_label = label
    db.commit()
    if approve:
        set_provenance_classification(
            db, entry=entry, provenance_class=provenance_class or "real_clinical",
            actor="admin@x", actor_role="admin", approve=True, tenant_id=tenant,
            source_id="HOSP-GT-SRC", source_institution="St. Example Hospital",
            rights_evidence_ref="RIGHTS-DOC-001",
        )
    ann = Annotation(
        tenant_id=tenant, ann_id=f"ANN-{uuid.uuid4().hex[:10]}", retained_image_id=r.id,
        primary_observation=label, ground_truth_status=GROUND_TRUTH_ACTIVE, digital_twin_id=serial,
    )
    db.add(ann)
    db.commit()
    return entry


# ── Fail-closed classification ────────────────────────────────────────────────
def test_normalize_is_fail_closed():
    assert normalize_provenance_class("") == PROVENANCE_LEGACY_UNVERIFIED
    assert normalize_provenance_class(None) == PROVENANCE_LEGACY_UNVERIFIED
    assert normalize_provenance_class("totally_made_up") == PROVENANCE_LEGACY_UNVERIFIED
    assert normalize_provenance_class("real") == PROVENANCE_LEGACY_UNVERIFIED  # the old fail-open string
    assert normalize_provenance_class("REAL_CLINICAL") == "real_clinical"


def test_is_clinical_evidence_requires_approved_real_clinical():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        pending = _entry(db, t, provenance_class="real_clinical", approve=False)
        approved = _entry(db, t, provenance_class="real_clinical", approve=True)
        external = _entry(db, t, provenance_class="external_nonclinical")
        legacy = _entry(db, t, provenance_class="")  # defaults legacy_unverified
        assert is_clinical_evidence(approved) is True
        assert is_clinical_evidence(pending) is False
        assert is_clinical_evidence(external) is False
        assert is_clinical_evidence(legacy) is False
        assert clinical_exclusion_reason(approved) is None
        assert "not_approved" in clinical_exclusion_reason(pending)
        assert clinical_exclusion_reason(external).startswith("research_provenance")
        assert clinical_exclusion_reason(legacy).startswith("unverified_provenance")
    finally:
        db.close()


# ── Legacy / migration compatibility ──────────────────────────────────────────
def test_legacy_entry_defaults_fail_closed():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        e = _entry(db, t, provenance_class="")  # no declared provenance
        assert e.data_provenance_class == PROVENANCE_LEGACY_UNVERIFIED
        assert e.provenance_approval_status == PROVENANCE_APPROVAL_PENDING
        assert is_clinical_evidence(e) is False
    finally:
        db.close()


# ── Self-declared real_clinical cannot auto-qualify ──────────────────────────
def test_ingestion_cannot_self_certify_real_clinical():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        # A client declaring real_clinical at ingestion is stored PENDING, never approved.
        e = _entry(db, t, provenance_class="real_clinical", approve=False)
        assert e.data_provenance_class == "real_clinical"
        assert e.provenance_approval_status == PROVENANCE_APPROVAL_PENDING
        assert is_clinical_evidence(e) is False
    finally:
        db.close()


# ── Approval authority + audit + cross-tenant ────────────────────────────────
def test_unauthorized_role_cannot_approve_clinical_provenance():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        e = _entry(db, t, provenance_class="real_clinical", approve=False)
        with pytest.raises(ProvenanceAuthorityError):
            set_provenance_classification(
                db, entry=e, provenance_class="real_clinical", actor="tech@x",
                actor_role="technician", approve=True, tenant_id=t,
            )
    finally:
        db.close()


def test_authorized_approval_is_audited():
    from app.models.audit_log import AuditLog
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        e = _entry(db, t, provenance_class="real_clinical", approve=False)
        set_provenance_classification(
            db, entry=e, provenance_class="real_clinical", actor="admin@x",
            actor_role="admin", approve=True, tenant_id=t, source_id="HOSP-GT-9",
            source_institution="St. Example", rights_evidence_ref="RIGHTS-DOC-7",
        )
        assert e.provenance_approval_status == PROVENANCE_APPROVAL_APPROVED
        assert e.provenance_approved_by == "admin@x"
        audit = (
            db.query(AuditLog)
            .filter(AuditLog.action_type == "dataset.provenance.classified")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit is not None
    finally:
        db.close()


def test_cross_tenant_provenance_change_denied():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        e = _entry(db, t, provenance_class="real_clinical", approve=False)
        with pytest.raises(ProvenanceAuthorityError):
            set_provenance_classification(
                db, entry=e, provenance_class="real_clinical", actor="admin@x", actor_role="admin",
                approve=True, tenant_id="some-other-tenant",
            )
    finally:
        db.close()


# ── Cohort summary: clinical vs research vs mixed ────────────────────────────
def test_cohort_clinical_only_when_all_approved_clinical():
    clinical = {"data_provenance_class": "real_clinical", "provenance_approval_status": "approved"}
    research = {"data_provenance_class": "external_nonclinical", "provenance_approval_status": "not_required"}
    legacy = {"data_provenance_class": "legacy_unverified", "provenance_approval_status": "pending"}

    all_clinical = summarize_cohort_provenance([clinical, clinical])
    assert all_clinical["clinical_promotion_eligible"] is True
    assert all_clinical["aggregate_class"] == "real_clinical"

    mixed = summarize_cohort_provenance([clinical, research])
    assert mixed["clinical_promotion_eligible"] is False
    assert mixed["aggregate_class"] == "mixed"

    research_only = summarize_cohort_provenance([research, research])
    assert research_only["clinical_promotion_eligible"] is False
    assert research_only["research_experiment_eligible"] is True

    with_legacy = summarize_cohort_provenance([research, legacy])
    assert with_legacy["research_experiment_eligible"] is False  # unverified present

    assert summarize_cohort_provenance([])["clinical_promotion_eligible"] is False


# ── Eligibility derives provenance from records, not facility strings ─────────
def test_eligibility_uses_verified_records_not_facility_string():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        # Real clinical photos whose facility name does NOT contain any marker —
        # under the old fail-open these would have been counted "real" from the
        # string alone. Here they are external_nonclinical and never clinical.
        _entry(db, t, provenance_class="external_nonclinical", serial="A1")
        _entry(db, t, provenance_class="external_nonclinical", serial="A2")
        rep = compute_training_eligibility(db, tenant_id=t)
        assert rep["clinical_promotion_eligible"] is False
        assert rep["data_provenance"] != "real_clinical"
        assert rep["provenance_breakdown"].get("external_nonclinical") == 2
    finally:
        db.close()


def test_eligibility_clinical_only_for_approved_real_clinical():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        _entry(db, t, provenance_class="real_clinical", approve=True, serial="C1")
        _entry(db, t, provenance_class="real_clinical", approve=True, serial="C2")
        rep = compute_training_eligibility(db, tenant_id=t)
        assert rep["clinical_promotion_eligible"] is True
        assert rep["data_provenance"] == "real_clinical"
    finally:
        db.close()


def test_eligibility_mixed_cohort_not_clinically_promotable():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        _entry(db, t, provenance_class="real_clinical", approve=True, serial="M1")
        _entry(db, t, provenance_class="laboratory_controlled", serial="M2")
        rep = compute_training_eligibility(db, tenant_id=t)
        assert rep["clinical_promotion_eligible"] is False
        assert rep["data_provenance"] == "mixed"
    finally:
        db.close()


# ── Promotion gates: no automatic Candidate from non-clinical data ───────────
def _trained_lens_run(*, data_provenance, clinical_promotion_eligible):
    """A minimal but export-complete trained run dict for register_lens_model."""
    return {
        "training_status": "trained", "data_provenance": data_provenance,
        "clinical_promotion_eligible": clinical_promotion_eligible,
        "eligible_classes": ["probable_retained_debris"], "has_negative_class": False,
        "stage_b_weights": [0.0], "stage_c_weights_by_class": {}, "preprocessing_version": "v1",
        "calibration": {}, "config": {}, "config_hash": "abc", "git_commit": "deadbeef",
        "not_evaluated_classes": [], "training_metrics": {}, "evaluation_metrics": {},
        "error_analysis": {},
    }


def test_lens_registration_no_candidate_for_nonclinical(tmp_path):
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        run = _trained_lens_run(data_provenance="external_nonclinical", clinical_promotion_eligible=False)
        row = register_lens_model(db, tenant_id=t, run=run, model_version="x1", artifact_dir=str(tmp_path))
        assert row.candidate_stage == "Experimental"
    finally:
        db.close()


def test_lens_registration_candidate_only_for_approved_clinical(tmp_path):
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        run = _trained_lens_run(data_provenance="real_clinical", clinical_promotion_eligible=True)
        row = register_lens_model(db, tenant_id=t, run=run, model_version="x2", artifact_dir=str(tmp_path))
        assert row.candidate_stage == "Candidate"
        # ...but a 'real_clinical' string WITHOUT the verified flag still stays Experimental.
        run2 = _trained_lens_run(data_provenance="real_clinical", clinical_promotion_eligible=False)
        row2 = register_lens_model(db, tenant_id=t, run=run2, model_version="x3", artifact_dir=str(tmp_path))
        assert row2.candidate_stage == "Experimental"
    finally:
        db.close()


def test_genesis_pipeline_no_candidate_for_research_cohort(tmp_path):
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        # A trained model from laboratory_controlled research data — never Candidate.
        samples = []
        for i in range(12):
            label = ["debris", "corrosion", "no_actionable_finding"][i % 3]
            samples.append({
                "id": f"r-{i}", "image_bytes": _png(i), "label": label, "inspection_id": i,
                "instrument_family": f"inst{i % 3}", "manufacturer": f"M{i % 3}", "facility": f"F{i % 3}",
                "anatomy_zone": "hinge", "image_sha256": f"rsha-{i}", "instrument_id": f"SER-{i}",
                "data_provenance_class": "laboratory_controlled", "provenance_approval_status": "not_required",
            })
        row = run_full_candidate_pipeline(
            db, tenant_id=t, samples=samples, config=TrainingConfig(seed=5, epochs=50),
            model_id="g-research", model_version="0.1.0", artifact_dir=str(tmp_path),
        )
        assert row.training_status == "trained"
        assert row.candidate_stage == "Experimental"  # research data never auto-advances
    finally:
        db.close()


# ── Rights / PHI gates still enforced ────────────────────────────────────────
def test_rights_restricted_and_phi_unverified_excluded():
    db = SessionLocal()
    try:
        t = f"t-{uuid.uuid4().hex[:8]}"
        _entry(db, t, provenance_class="real_clinical", approve=True, usage_rights="", serial="R1")
        _entry(db, t, provenance_class="real_clinical", approve=True, phi="pending", serial="R2")
        rep = compute_training_eligibility(db, tenant_id=t)
        assert rep["total_eligible_samples"] == 0
        assert rep["excluded_counts"].get("rights_restricted", 0) >= 1
        assert rep["excluded_counts"].get("phi_not_verified", 0) >= 1
    finally:
        db.close()
