"""Stage 5A — research-only vision foundation regression + governance tests.

Runs WITHOUT PyTorch (the real DINOv2 path is skipped when torch is absent). The
governance, isolation, determinism, splitting, checkpoint-verification, and
"no production change" tests always run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os

import pytest
from PIL import Image

from app.db.session import SessionLocal
from app.models.retained_image import RetainedImage
from app.services.ml import dataset_registry

from research.lens_vision import checkpoint as ckpt
from research.lens_vision.anomaly_feasibility import (
    AnomalyRegion,
    ClinicalDiagnosisForbiddenError,
    feasibility_assessment,
)
from research.lens_vision.benchmark import run_research_benchmark
from research.lens_vision.config import ResearchRunConfig
from research.lens_vision.deps import ResearchDependencyMissing, require_torch, torch_available
from research.lens_vision.embeddings import StubEmbedder
from research.lens_vision.images import InvalidImageError, decode_rgb
from research.lens_vision.model_card import write_model_card
from research.lens_vision.provenance import (
    ResearchProvenanceError,
    assert_research_authorized,
    is_clinically_promotable,
)
from research.lens_vision.synthetic_fixtures import synthetic_research_dataset

TORCH = importlib.util.find_spec("torch") is not None


def _cfg(**kw):
    base = dict(run_id="t", seed=7, checkpoint_id="smoke_stub",
                source_provenance_class="synthetic_experimental", embedder="smoke_stub")
    base.update(kw)
    return ResearchRunConfig(**base)


# ── Optional dependency isolation / baseline without torch ──────────────────

def test_research_package_imports_and_torch_is_optional():
    # The package imported above without torch; the real path raises clearly.
    assert torch_available() is TORCH
    if not TORCH:
        with pytest.raises(ResearchDependencyMissing):
            require_torch()


def test_baseline_pillow_path_works_without_torch():
    from app.services.ml.training_execution import _feature_vector
    data = synthetic_research_dataset(n_per_class=1)[0]["image_bytes"]
    assert _feature_vector(data) is not None           # production baseline unaffected
    assert len(StubEmbedder().embed(data)) > 0          # research stub works without torch


# ── Research-only provenance enforcement ────────────────────────────────────

def test_research_provenance_enforcement():
    ok = [{"data_provenance_class": c} for c in
          ("synthetic_experimental", "external_nonclinical", "laboratory_controlled")]
    assert_research_authorized(ok)  # no raise

    for bad in ("real_clinical", "unknown", "legacy_unverified", ""):
        with pytest.raises(ResearchProvenanceError):
            assert_research_authorized([{"data_provenance_class": bad}])


def test_approved_clinical_allowed_only_with_optin_and_never_promotable():
    approved_clinical = [{"data_provenance_class": "real_clinical", "provenance_approval_status": "approved"}]
    with pytest.raises(ResearchProvenanceError):
        assert_research_authorized(approved_clinical)              # default: refused
    assert_research_authorized(approved_clinical, allow_approved_clinical=True)  # opt-in: allowed
    assert is_clinically_promotable({"anything": True}) is False  # never promotable


# ── Checkpoint loading + verification ───────────────────────────────────────

def test_checkpoint_stub_approved_dinov2_blocked():
    assert ckpt.verify_checkpoint("smoke_stub").approved is True
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        ckpt.verify_checkpoint("dinov2_vits14")
    with pytest.raises(ckpt.CheckpointNotRegisteredError):
        ckpt.verify_checkpoint("not_a_real_checkpoint")


def test_checkpoint_file_hash_verification(tmp_path, monkeypatch):
    weights = tmp_path / "w.bin"
    weights.write_bytes(b"fake-weights")
    digest = hashlib.sha256(b"fake-weights").hexdigest()
    rec = ckpt.CheckpointRecord(
        checkpoint_id="test_ckpt", description="t", license="test", source_url="",
        expected_sha256=digest, approved=True, rights_cleared=True, requires_file=True,
    )
    monkeypatch.setitem(ckpt._REGISTRY, "test_ckpt", rec)
    assert ckpt.verify_checkpoint("test_ckpt", file_path=str(weights)).checkpoint_id == "test_ckpt"
    # wrong content -> verification error
    weights.write_bytes(b"tampered")
    with pytest.raises(ckpt.CheckpointVerificationError):
        ckpt.verify_checkpoint("test_ckpt", file_path=str(weights))
    # missing file -> file-missing error
    with pytest.raises(ckpt.CheckpointFileMissingError):
        ckpt.verify_checkpoint("test_ckpt", file_path=str(tmp_path / "nope.bin"))


# ── Deterministic feature extraction ────────────────────────────────────────

def test_stub_embedding_is_deterministic():
    data = synthetic_research_dataset(n_per_class=1)[0]["image_bytes"]
    assert StubEmbedder().embed(data) == StubEmbedder().embed(data)


def test_benchmark_is_reproducible():
    samples = synthetic_research_dataset(n_per_class=6)
    r1 = run_research_benchmark(samples, config=_cfg())
    r2 = run_research_benchmark(samples, config=_cfg())
    assert r1["metrics"] == r2["metrics"]
    assert r1["config_fingerprint"] == r2["config_fingerprint"]


# ── Missing / invalid image handling ────────────────────────────────────────

def test_invalid_image_handling():
    for bad in (None, b"", b"not-an-image"):
        with pytest.raises(InvalidImageError):
            decode_rgb(bad)
    with pytest.raises(InvalidImageError):
        StubEmbedder().embed(b"not-an-image")


# ── Group-safe dataset splitting ────────────────────────────────────────────

def test_benchmark_reports_grouping_reliability():
    reliable = run_research_benchmark(synthetic_research_dataset(n_per_class=6, reliable_grouping=True), config=_cfg())
    assert reliable["grouping_reliable"] is True
    unreliable = run_research_benchmark(
        synthetic_research_dataset(n_per_class=6, reliable_grouping=False), config=_cfg())
    assert unreliable["grouping_reliable"] is False


# ── Research-only artifact registration / no clinical promotion ─────────────

def test_benchmark_result_is_research_only_and_not_promotable():
    result = run_research_benchmark(synthetic_research_dataset(n_per_class=6), config=_cfg())
    assert result["research_only"] is True
    assert result["clinical_promotion_eligible"] is False
    assert result["status"] == "completed"
    assert result["metrics"]["research_embedding_accuracy"] is not None


def test_external_and_lab_data_never_clinically_promotable():
    for cls in ("external_nonclinical", "laboratory_controlled"):
        samples = synthetic_research_dataset(n_per_class=6)
        for s in samples:
            s["data_provenance_class"] = cls
            s["provenance_approval_status"] = "not_required"
        result = run_research_benchmark(samples, config=_cfg(source_provenance_class=cls))
        assert result["clinical_promotion_eligible"] is False


def test_model_card_written_marks_research_only(tmp_path):
    result = run_research_benchmark(synthetic_research_dataset(n_per_class=6), config=_cfg())
    path = os.path.join(tmp_path, "card.json")
    card = write_model_card(path, _cfg(), result)
    assert card["research_only"] is True
    assert card["clinical_promotion_eligible"] is False
    with open(path) as f:
        on_disk = json.load(f)
    assert "RESEARCH ONLY" in on_disk["banner"]
    assert on_disk["checkpoint"]["status"] == "approved"  # smoke_stub


# ── Anomaly feasibility stays research-only (no auto-diagnosis) ──────────────

def test_anomaly_region_cannot_become_clinical_diagnosis():
    fa = feasibility_assessment()
    assert fa["research_only"] is True
    assert fa["data_status"] == "awaiting_qualified_image_data"
    region = AnomalyRegion(x=0, y=0, width=1, height=1, anomaly_score=0.9, uncertainty=0.3)
    assert region.confirmed_diagnosis is None
    with pytest.raises(ClinicalDiagnosisForbiddenError):
        region.to_clinical_label()


# ── No change to production inference / baseline comparison ─────────────────

def test_production_live_inference_unchanged():
    db = SessionLocal()
    try:
        from app.services.ml.live_inference_adapter import predict
        res = predict(db, tenant_id="s5a-no-model-tenant", image_bytes=None)
        assert res["analysis_status"] == "ai_unavailable"
        assert res["observation"] is None
        assert res["human_review_required"] is True
    finally:
        db.close()


def test_production_baseline_comparison_unchanged():
    from app.services.ml import image_similarity_service
    buf = io.BytesIO()
    Image.new("RGB", (120, 120), (90, 90, 90)).save(buf, format="PNG")
    data = buf.getvalue()
    res = image_similarity_service.compare_image_bytes(data, data)
    assert res["status"] == image_similarity_service.STATUS_EXACT_MATCH
    assert res["similarity"] == 1.0


# ── No cross-tenant data access (tenant-scoped research loader) ──────────────

def _seed_entry(
    db, tenant, label="no_observable_abnormality", *, provenance="synthetic_experimental",
    usage_rights="internal_use", phi="verified", retention="active", active_annotation=True,
    digital_twin_id="", approve_clinical=False,
):
    """Seed a RetainedImage + governed DatasetRegistryEntry, optionally with an
    ACTIVE Annotation (ground truth) and all usage gates satisfied. Returns the
    entry id. Pass flags to exercise each governance-failure path."""
    import uuid as _uuid
    from app.models.annotation_database import GROUND_TRUTH_ACTIVE, Annotation
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (123, 123, 123)).save(buf, format="PNG")
    data = buf.getvalue()
    sha = hashlib.sha256(data + tenant.encode() + str(_uuid.uuid4()).encode()).hexdigest()
    r = RetainedImage(
        tenant_id=tenant, deident_name="t", instrument_type="scissors", content_type="image/png",
        size_bytes=len(data), sha256=sha, exif_stripped=True, source="test",
        consent_recorded=True, uploaded_by="t", image_bytes=data,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    v = dataset_registry.create_dataset_version(db, tenant_id=tenant, version_label=f"s5a-{tenant}-{sha[:8]}")
    entry = dataset_registry.register_image(
        db, tenant_id=tenant, dataset_version_id=v.id, retained_image_id=r.id, image_sha256=sha,
        instrument_family="scissors", manufacturer="Acme", facility="H", operator="t",
        capture_device="phone", image_resolution="64x64", data_provenance_class=provenance,
        usage_rights=usage_rights, phi_verification=phi, retention_status=retention,
        digital_twin_id=digital_twin_id,
    )
    entry.image_quality = "Good"
    if approve_clinical:
        entry.provenance_approval_status = "approved"
    db.commit()
    if active_annotation:
        db.add(Annotation(
            tenant_id=tenant, ann_id=f"ANN-{_uuid.uuid4().hex[:10]}", retained_image_id=r.id,
            primary_observation=label, ground_truth_status=GROUND_TRUTH_ACTIVE, digital_twin_id=digital_twin_id,
        ))
        db.commit()
    return entry.id


def test_research_loader_is_tenant_scoped():
    from research.lens_vision.data_loader import load_research_samples
    import uuid
    ta = f"s5a-A-{uuid.uuid4().hex[:6]}"
    tb = f"s5a-B-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        _seed_entry(db, ta)
        _seed_entry(db, tb)
        samples_a = load_research_samples(db, tenant_id=ta)
        assert len(samples_a) >= 1
        assert all(s["tenant_id"] == ta for s in samples_a)
        # none of tenant B's entries leak into tenant A's load
        a_ids = {s["id"] for s in samples_a}
        samples_b = load_research_samples(db, tenant_id=tb)
        b_ids = {s["id"] for s in samples_b}
        assert a_ids.isdisjoint(b_ids)
    finally:
        db.close()


@pytest.mark.skipif(not TORCH, reason="PyTorch not installed in this environment (research extra)")
def test_dinov2_path_requires_approved_checkpoint_even_with_torch():
    from research.lens_vision.embeddings import Dinov2Embedder
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        Dinov2Embedder(checkpoint_id="dinov2_vits14")


# ── H1 — authorized data USAGE, not merely provenance classification ─────────

def _load(db, tenant, **kw):
    from research.lens_vision.data_loader import load_research_samples
    return load_research_samples(db, tenant_id=tenant, **kw)


def test_loader_rejects_rights_restricted_and_phi_and_retention():
    import uuid
    db = SessionLocal()
    try:
        t = f"s5a-usage-{uuid.uuid4().hex[:6]}"
        _seed_entry(db, t)                               # authorized baseline
        _seed_entry(db, t, usage_rights="")              # rights restricted
        _seed_entry(db, t, phi="pending")                # PHI not verified
        _seed_entry(db, t, retention="purged")           # retention not active
        samples = _load(db, t)
        assert len(samples) == 1                         # only the fully-authorized one
    finally:
        db.close()


def test_external_lab_not_eligible_by_class_alone():
    import uuid
    db = SessionLocal()
    try:
        t = f"s5a-extlab-{uuid.uuid4().hex[:6]}"
        # Correct provenance class but FAILS the usage gate (no rights) -> excluded.
        _seed_entry(db, t, provenance="external_nonclinical", usage_rights="")
        _seed_entry(db, t, provenance="laboratory_controlled", phi="pending")
        assert _load(db, t) == []
        # Same classes WITH usage authorization -> eligible.
        _seed_entry(db, t, provenance="external_nonclinical")
        assert len(_load(db, t)) == 1
    finally:
        db.close()


def test_clinical_requires_opt_in_and_verified_research_use_scope():
    import uuid
    from app.models.consent_record import ConsentRecord
    db = SessionLocal()
    try:
        t = f"s5a-clin-{uuid.uuid4().hex[:6]}"
        _seed_entry(db, t, provenance="real_clinical", approve_clinical=True)
        # No opt-in -> excluded even though approved.
        assert _load(db, t, allow_approved_clinical=False) == []
        # Opt-in but NO research-use scope consent -> still excluded.
        assert _load(db, t, allow_approved_clinical=True) == []
        # Add a granted research-use consent -> now eligible with opt-in.
        db.add(ConsentRecord(
            id=str(uuid.uuid4()), tenant_id=t, user_email="d@x",
            consent_type="benchmarking_contribution", granted=True,
        ))
        db.commit()
        assert len(_load(db, t, allow_approved_clinical=True)) == 1
    finally:
        db.close()


# ── H2 — ground-truth integrity (no implicit missing-label -> normal) ────────

def test_unlabeled_image_is_not_loaded_as_normal():
    import uuid
    from research.lens_vision.governance import GT_UNLABELED, ground_truth_status
    db = SessionLocal()
    try:
        t = f"s5a-gt-{uuid.uuid4().hex[:6]}"
        eid = _seed_entry(db, t, active_annotation=False)  # no ACTIVE annotation
        # require_ground_truth default -> excluded entirely (never defaulted to normal)
        assert _load(db, t) == []
        # and its GT status is 'unlabeled', not normal
        from app.models.dataset_governance import DatasetRegistryEntry
        entry = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.id == eid).first()
        status, label = ground_truth_status(db, tenant_id=t, retained_image_id=entry.retained_image_id)
        assert status == GT_UNLABELED and label is None
    finally:
        db.close()


def test_verified_normal_only_excludes_unlabeled_unknown_abnormal():
    import uuid
    from research.lens_vision.data_loader import verified_normal_only
    from research.lens_vision.governance import GT_ABNORMAL, GT_VERIFIED_NORMAL
    db = SessionLocal()
    try:
        t = f"s5a-normal-{uuid.uuid4().hex[:6]}"
        _seed_entry(db, t, label="no_observable_abnormality")             # verified normal
        _seed_entry(db, t, label="probable_corrosion_like_degradation")   # abnormal
        _seed_entry(db, t, active_annotation=False)                        # unlabeled (excluded by loader)
        loaded = _load(db, t)
        statuses = {s["ground_truth_status"] for s in loaded}
        assert GT_VERIFIED_NORMAL in statuses and GT_ABNORMAL in statuses
        normals = verified_normal_only(loaded)
        assert normals and all(s["ground_truth_status"] == GT_VERIFIED_NORMAL for s in normals)
        assert all(s["label"] == "no_observable_abnormality" for s in normals)
    finally:
        db.close()


# ── H3 — leakage: untracked digital twin is not a reliable serial ───────────

def test_untracked_twin_not_used_as_instrument_serial():
    import uuid
    db = SessionLocal()
    try:
        t = f"s5a-twin-{uuid.uuid4().hex[:6]}"
        _seed_entry(db, t, digital_twin_id="untracked:scissors:xyz")
        _seed_entry(db, t, digital_twin_id="SER-REAL-1")
        loaded = _load(db, t)
        serials = {s["id"]: s["instrument_serial"] for s in loaded}
        vals = set(serials.values())
        assert None in vals                     # untracked -> not a serial
        assert "SER-REAL-1" in vals             # real twin -> kept
        assert not any(str(v).startswith("untracked:") for v in vals if v)
    finally:
        db.close()


# ── H4 — reproducibility: embedder identity + checkpoint metadata ───────────

def test_benchmark_rejects_embedder_identity_mismatch():
    from research.lens_vision.benchmark import EmbedderIdentityError, run_research_benchmark
    samples = synthetic_research_dataset(n_per_class=6)
    with pytest.raises(EmbedderIdentityError):
        # config declares dinov2 but the actual embedder is the stub
        run_research_benchmark(samples, config=_cfg(embedder="dinov2"), embedder=StubEmbedder())


def test_checkpoint_records_architecture_and_preprocessing():
    rec = ckpt.get_record("dinov2_vits14")
    assert rec.architecture == "vit_small_patch14_dinov2"
    assert rec.preprocessing and "mean" in rec.preprocessing and "std" in rec.preprocessing


def test_model_card_records_checkpoint_architecture_and_digest(tmp_path):
    from research.lens_vision.model_card import build_model_card
    result = run_research_benchmark(synthetic_research_dataset(n_per_class=6), config=_cfg())
    card = build_model_card(_cfg(checkpoint_id="dinov2_vits14"), result)
    assert card["checkpoint"]["architecture"] == "vit_small_patch14_dinov2"
    assert "digest_sha256" in card["checkpoint"] and "preprocessing" in card["checkpoint"]
    assert card["checkpoint"]["status"] == "blocked"  # dinov2 not approved/rights-cleared


def test_benchmark_reports_identity_and_dropped_unlabelled():
    result = run_research_benchmark(synthetic_research_dataset(n_per_class=6), config=_cfg())
    assert result["embedder_identity_verified"] is True
    assert result["dropped_unlabelled_count"] == 0  # synthetic fixtures are all labelled
