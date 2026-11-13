"""Stage 5C — scientific evidence, calibration, artifact-integrity tests.

Runs WITHOUT torch/Anomalib (real PaDiM/PatchCore are governed blockers). Covers
model execution, checkpoint approval, provenance/supplied-dataset governance,
scientific evidence linkage + category requirements, mask alignment,
calibration-data separation (frozen thresholds), leakage (incl. lab batch),
cross-tenant denial, artifact integrity, and the research-only invariants.
"""
from __future__ import annotations

import importlib.util

import pytest

# Init app layer before research imports (cold circular-import avoidance).
from app.db.session import SessionLocal  # noqa: F401

from research.lens_vision import checkpoint as ckpt
from research.lens_vision.anomaly_experiment import LeakageError, run_anomaly_experiment
from research.lens_vision.anomaly_localization import PadimLocalizer, PatchCoreLocalizer, StubLocalizer
from research.lens_vision.artifact_store import (
    MalformedHeatmapError,
    MalformedMaskError,
    NonFiniteValueError,
    ResearchArtifactStore,
    sanitize_score,
    validate_heatmap,
    validate_mask,
)
from research.lens_vision.calibration import classification_metrics, fit_frozen_threshold, wilson_interval
from research.lens_vision.config import ResearchRunConfig
from research.lens_vision.governance import (
    SuppliedDatasetGovernanceError,
    enforce_supplied_dataset_governance,
)
from research.lens_vision.scientific_annotation import (
    AnnotationAlignmentError,
    relate_region_to_reference,
    verify_bbox,
    verify_mask_alignment,
)
from research.lens_vision.scientific_evidence import (
    BLOOD_LIKE_RESIDUE,
    BONE_TISSUE_LIKE,
    CORROSION_LIKE,
    PITTING_LOCALIZED,
    REL_INDETERMINATE,
    REL_SUPPORTED,
    ForbiddenInferenceError,
    LaboratoryEvidence,
    ReviewerAuthorization,
    infer_identity_from_rgb,
    is_lab_confirmed,
    link_observation,
    validate_evidence,
)
from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset

TORCH = importlib.util.find_spec("torch") is not None


def _cfg(**kw):
    base = dict(run_id="c5", seed=5, checkpoint_id="stub_backbone",
                source_provenance_class="synthetic_experimental", embedder="stub_padim_like")
    base.update(kw)
    return ResearchRunConfig(**base)


def _evidence(category, **over):
    base = dict(
        image_id=1, image_sha256="a" * 64, instrument_id="INS-1", specimen_id="SPEC-1",
        imaging_session_id="SESS-1", evidence_category=category, material_type="stainless_steel",
        instrument_anatomy="hinge", source_laboratory="Lab A", study_id="STUDY-1",
        reference_method="", verification_status="verified", reviewer_id="rev@x",
        approval_evidence_ref="APPR-1", measurement_uncertainty=0.1,
    )
    base.update(over)
    return LaboratoryEvidence(**base)


# ── 1 & 2 — model execution + checkpoint approval/SHA ───────────────────────

def test_real_models_blocked_and_stub_runs():
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        PadimLocalizer(backbone_checkpoint_id="resnet18_imagenet")
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        PatchCoreLocalizer(backbone_checkpoint_id="resnet18_imagenet")
    normal, test = synthetic_anomaly_dataset(n_normal=8, n_anomalous=6)
    rep = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(), synthetic_technical_test=True)
    assert rep["research_only"] is True and rep["localizer"] == "stub_padim_like"


def test_checkpoint_sha_verification(tmp_path, monkeypatch):
    import hashlib
    w = tmp_path / "bb.bin"
    w.write_bytes(b"weights")
    rec = ckpt.CheckpointRecord(
        checkpoint_id="bb", description="t", license="BSD-3", source_url="",
        expected_sha256=hashlib.sha256(b"weights").hexdigest(), approved=True, rights_cleared=True,
        requires_file=True, architecture="resnet18", preprocessing={"resize": [224, 224]},
    )
    monkeypatch.setitem(ckpt._REGISTRY, "bb", rec)
    assert ckpt.verify_checkpoint("bb", file_path=str(w)).checkpoint_id == "bb"
    w.write_bytes(b"tampered")
    with pytest.raises(ckpt.CheckpointVerificationError):
        ckpt.verify_checkpoint("bb", file_path=str(w))


# ── 3 & 9 — supplied-dataset provenance + cross-tenant denial ───────────────

def test_supplied_dataset_governance_enforced():
    normal, _ = synthetic_anomaly_dataset(n_normal=4, n_anomalous=0)
    # clean synthetic -> ok
    enforce_supplied_dataset_governance(normal)
    # non-authorized provenance
    bad = [dict(normal[0], data_provenance_class="real_clinical", provenance_approval_status="pending")]
    with pytest.raises(SuppliedDatasetGovernanceError):
        enforce_supplied_dataset_governance(bad)
    # missing integrity hash
    noimg = [dict(normal[0], image_sha256="")]
    with pytest.raises(SuppliedDatasetGovernanceError):
        enforce_supplied_dataset_governance(noimg)
    # cross-tenant mixing
    mixed = [dict(normal[0], tenant_id="A"), dict(normal[1], tenant_id="B")]
    with pytest.raises(SuppliedDatasetGovernanceError):
        enforce_supplied_dataset_governance(mixed)


# ── 4 & 5 — scientific evidence linkage + category/measurement consistency ──

def test_evidence_category_requirements():
    # corrosion needs material characterization + affected-area measurement
    assert validate_evidence(_evidence(CORROSION_LIKE, reference_method="eds",
                                       measurement_value=12.5, measurement_units="mm2")) == []
    assert "reference_method_not_appropriate_for_corrosion_like_surface" in \
        validate_evidence(_evidence(CORROSION_LIKE, reference_method="guesswork",
                                    measurement_value=1, measurement_units="mm2"))
    assert any("missing_quantitative" in r for r in
               validate_evidence(_evidence(CORROSION_LIKE, reference_method="eds")))
    # pitting needs microscopy/profilometry + pit geometry
    assert validate_evidence(_evidence(PITTING_LOCALIZED, reference_method="profilometry",
                                       measurement_value=40.0, measurement_units="um")) == []
    # blood-like needs soil identity confirmation + identity
    assert validate_evidence(_evidence(BLOOD_LIKE_RESIDUE, reference_method="protein_assay",
                                       verified_material_identity="hemoglobin")) == []
    assert "missing_verified_material_identity" in \
        validate_evidence(_evidence(BLOOD_LIKE_RESIDUE, reference_method="protein_assay"))
    # bone/tissue needs composition/identity
    assert validate_evidence(_evidence(BONE_TISSUE_LIKE, reference_method="composition_analysis",
                                       verified_material_identity="hydroxyapatite")) == []


def test_uncertainty_not_fabricated():
    e = _evidence(CORROSION_LIKE, reference_method="eds", measurement_value=1, measurement_units="mm2")
    assert validate_evidence(e) == []                         # 0.1 ok
    assert validate_evidence(_evidence(CORROSION_LIKE, reference_method="eds", measurement_value=1,
                                       measurement_units="mm2", measurement_uncertainty="unknown")) == []
    assert validate_evidence(_evidence(CORROSION_LIKE, reference_method="eds", measurement_value=1,
                                       measurement_units="mm2", measurement_uncertainty=float("inf"))) != []


def test_observation_keeps_layers_separate():
    # The anomaly must carry the image/specimen identity it was detected on, so lab
    # evidence from a DIFFERENT image/specimen can never be attached to it.
    ai = {"image_level_anomaly_score": 9.0, "research_only": True, "confirmed_diagnosis": None,
          "image_sha256": "a" * 64, "specimen_id": "SPEC-1"}
    ev = _evidence(CORROSION_LIKE, reference_method="eds", measurement_value=10, measurement_units="mm2",
                   verified_material_identity="iron_oxide")
    authz = ReviewerAuthorization(reviewer_id="rev@x", authenticated=True, roles=("scientific_reviewer",))
    # Without an authorized reviewer -> indeterminate, no confirmed identity.
    obs = link_observation(ai, laboratory_evidence=ev, reviewer_authorization=None)
    assert obs.ai_to_material_relationship == REL_INDETERMINATE
    assert obs.confirmed_material_identity is None
    # With an authenticated, authorized, matching reviewer + verified evidence ->
    # supported + identity from LAB only.
    obs2 = link_observation(ai, laboratory_evidence=ev, reviewer_authorization=authz)
    assert obs2.ai_to_material_relationship == REL_SUPPORTED
    assert obs2.confirmed_material_identity == "iron_oxide"
    # Invariants
    for o in (obs, obs2):
        assert o.research_only is True and o.clinical_promotion_eligible is False
        assert o.confirmed_diagnosis is None and o.human_review_required is True
        assert o.clinical_disposition is None


def test_is_lab_confirmed_requires_verified_reviewed_approved():
    ok = _evidence(CORROSION_LIKE, reference_method="eds", measurement_value=1, measurement_units="mm2")
    assert is_lab_confirmed(ok) is True
    assert is_lab_confirmed(_evidence(CORROSION_LIKE, reference_method="eds", measurement_value=1,
                                      measurement_units="mm2", verification_status="pending")) is False


def test_forbidden_rgb_inference():
    with pytest.raises(ForbiddenInferenceError):
        infer_identity_from_rgb([[1, 2, 3]])


# ── 6 — mask alignment / coordinate verification ────────────────────────────

def test_mask_and_bbox_alignment():
    good = [[0, 1], [1, 0]]
    assert verify_mask_alignment(good, image_width=2, image_height=2, annotation_version=1)["aligned"] is True
    with pytest.raises(AnnotationAlignmentError):
        verify_mask_alignment(good, image_width=3, image_height=2, annotation_version=1)   # dim mismatch
    with pytest.raises(AnnotationAlignmentError):
        verify_mask_alignment(good, image_width=2, image_height=2, annotation_version=None)  # no version
    assert verify_bbox({"x": 0, "y": 0, "width": 2, "height": 2}, image_width=4, image_height=4)["within_bounds"]
    with pytest.raises(AnnotationAlignmentError):
        verify_bbox({"x": 3, "y": 0, "width": 5, "height": 1}, image_width=4, image_height=4)


def test_region_reference_relationship_indeterminate_without_reference():
    pred = [[1, 1], [0, 0]]
    assert relate_region_to_reference(pred, None, image_width=2, image_height=2) == REL_INDETERMINATE
    assert relate_region_to_reference(pred, [[1, 1], [0, 0]], image_width=2, image_height=2) == REL_SUPPORTED
    assert relate_region_to_reference(pred, [[0, 0], [0, 1]], image_width=2, image_height=2) == REL_INDETERMINATE


# ── 7 — calibration-data separation + frozen thresholds ─────────────────────

def test_frozen_threshold_from_calibration_and_metrics():
    thr = fit_frozen_threshold([1.0, 2.0, 3.0, 4.0], [0.1, 0.2, 0.3], target_fpr=0.1)
    assert thr.frozen is True and thr.image_threshold >= 3.0
    m = classification_metrics([5, 1, 6, 0], [1, 0, 1, 0], thr.image_threshold)
    assert m["threshold"] == round(thr.image_threshold, 6)
    assert wilson_interval(2, 2) is not None


def test_experiment_uses_frozen_threshold_and_is_deterministic():
    normal, test = synthetic_anomaly_dataset(n_normal=10, n_anomalous=6)
    r1 = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(), synthetic_technical_test=True)
    r2 = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(), synthetic_technical_test=True)
    assert r1["frozen_threshold"]["frozen"] is True
    assert r1["n_calibration_normal"] >= 1 and r1["n_fit_normal"] >= 1
    assert r1["image_level_metrics"]["at_frozen_threshold"] is not None
    assert r1["image_level_metrics"]["auroc_ci95"] is not None
    assert r1["frozen_threshold"] == r2["frozen_threshold"]           # deterministic calibration
    assert [x["image_level_anomaly_score"] for x in r1["results"]] == \
           [x["image_level_anomaly_score"] for x in r2["results"]]


# ── 8 — leakage incl. laboratory batch ──────────────────────────────────────

def test_lab_batch_leakage_rejected():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    for s in normal:
        s["laboratory_batch_id"] = "BATCH-7"
    leaky = dict(test[0], laboratory_batch_id="BATCH-7")          # same lab batch as training
    with pytest.raises(LeakageError):
        run_anomaly_experiment(normal, [leaky], config=_cfg(), localizer=StubLocalizer())


# ── 10 & 11 — research invariants + artifact integrity ──────────────────────

def test_results_are_research_only_and_finite():
    normal, test = synthetic_anomaly_dataset(n_normal=8, n_anomalous=6)
    rep = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer())
    for res in rep["results"]:
        assert res["research_only"] is True and res["clinical_promotion_eligible"] is False
        assert res["confirmed_diagnosis"] is None and res["human_review_required"] is True
        assert res["uncertainty_status"] == "unknown"
        for r in res["proposed_regions"]:
            assert r["uncertainty"] is None                      # never NaN/fabricated
            import math
            assert math.isfinite(r["anomaly_score"])


def test_artifact_store_integrity(tmp_path):
    store = ResearchArtifactStore(str(tmp_path))
    ref = store.store_heatmap(tenant_id="t", run_id="r", image_id="img1", heatmap=[[0.1, 0.2], [0.3, 0.4]])
    assert ref and store.exists(ref, requesting_tenant_id="t") and store.resolve(ref, requesting_tenant_id="t")
    assert store.store_heatmap(tenant_id="t", run_id="r", image_id="bad", heatmap=[[0.1], [0.2, 0.3]]) is None  # malformed
    assert store.resolve("artifact://t/r/does-not-exist", requesting_tenant_id="t") is None
    with pytest.raises(NonFiniteValueError):
        sanitize_score(float("nan"))
    with pytest.raises(MalformedHeatmapError):
        validate_heatmap([[0.1, float("inf")]])
    with pytest.raises(MalformedMaskError):
        validate_mask([[2]], width=1, height=1)


def test_experiment_heatmap_refs_resolve(tmp_path):
    store = ResearchArtifactStore(str(tmp_path))
    normal, test = synthetic_anomaly_dataset(n_normal=8, n_anomalous=4)
    rep = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(), artifact_store=store)
    refs = [r["heatmap_ref"] for r in rep["results"]]
    # Every ref resolves to a stored artifact for its OWNING tenant only.
    assert all(ref and store.exists(ref, requesting_tenant_id="research-tenant") for ref in refs)


def test_no_store_means_no_dangling_reference():
    normal, test = synthetic_anomaly_dataset(n_normal=8, n_anomalous=4)
    rep = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer())  # no store
    assert all(r["heatmap_ref"] == "" for r in rep["results"])    # no fabricated/dangling ref


@pytest.mark.skipif(not TORCH, reason="torch/anomalib not installed (research extra)")
def test_real_padim_blocked_even_with_torch():
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        PadimLocalizer(backbone_checkpoint_id="resnet18_imagenet")
