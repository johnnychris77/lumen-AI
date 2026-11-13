"""Stage 6A — real-data cohort readiness, checkpoint governance, governed execution.

Cohort-readiness and checkpoint-registration tests run without torch. The governed
localizer execution is torch/anomalib-gated (isolated research venv only).
"""
from __future__ import annotations

import hashlib
import importlib.util

import pytest

# Init app layer before research imports (cold circular-import avoidance).
from app.db.session import SessionLocal  # noqa: F401

from research.lens_vision import checkpoint as ckpt
from research.lens_vision.cohort_readiness import (
    GT_ABNORMAL,
    GT_VERIFIED_NORMAL,
    MODALITY_EXTERNAL,
    generate_cohort_readiness_report,
    validate_image_readiness,
)

TORCH = importlib.util.find_spec("torch") is not None


def _img(**over):
    base = dict(
        image_id="img-1", image_sha256="a" * 64, instrument_id="INS-1", specimen_id="SPEC-1",
        modality=MODALITY_EXTERNAL, anatomy_zone="hinge", imaging_session_id="SESS-1",
        imaging_device="camA", data_provenance_class="external_nonclinical",
        institutional_authorization_ref="IRB-1", data_rights="research_use", retention_status="active",
        study_batch_id="BATCH-1", split="fit", ground_truth_status=GT_VERIFIED_NORMAL,
        label_reviewer_id="rev@x",
    )
    base.update(over)
    return base


# ── cohort readiness ─────────────────────────────────────────────────────────

def test_complete_image_is_ready():
    r = validate_image_readiness(_img())
    assert r["ready"] is True and r["blockers"] == []


def test_missing_fields_block():
    r = validate_image_readiness(_img(image_sha256="", institutional_authorization_ref=""))
    assert r["ready"] is False
    assert "missing:image_sha256" in r["blockers"]
    assert "missing:institutional_authorization_ref" in r["blockers"]


def test_unlabeled_cannot_be_verified_normal_training():
    r = validate_image_readiness(_img(ground_truth_status="unlabeled", intended_use="normal_training",
                                      label_reviewer_id=""))
    assert "unlabeled_or_nonnormal_used_as_verified_normal" in r["blockers"]


def test_abnormal_requires_lab_evidence_and_mask():
    r = validate_image_readiness(_img(
        ground_truth_status=GT_ABNORMAL, evidence_category="corrosion_like_surface",
        has_spatial_region="true", laboratory_evidence_ref="", approved_mask_ref=""))
    assert "missing_laboratory_evidence_for:corrosion_like_surface" in r["blockers"]
    assert "missing_approved_mask_for_spatial_region" in r["blockers"]


def test_non_research_provenance_blocked():
    r = validate_image_readiness(_img(data_provenance_class="real_clinical"))
    assert any(b.startswith("provenance_not_research_authorized") for b in r["blockers"])


def test_report_flags_cross_split_leakage_and_blocks_benchmark():
    # Same specimen appears in fit AND sealed_test -> leakage.
    manifest = [
        _img(image_id="a", split="fit", specimen_id="S1", image_sha256="1" * 64),
        _img(image_id="b", split="sealed_test", specimen_id="S1", image_sha256="2" * 64),
    ]
    rep = generate_cohort_readiness_report(manifest)
    assert rep["ready_for_benchmark"] is False
    assert rep["cross_split_leakage"]
    assert any("straddle" in b for b in rep["blockers"])


def test_small_complete_manifest_is_not_scientifically_ready():
    # A handful of fully-populated images must NOT be reported as benchmark-ready:
    # statistical adequacy (min sizes + reviewer sign-off) and an approved scientific
    # checkpoint are both missing.
    manifest = [
        _img(image_id="a", split="fit", specimen_id="S1", image_sha256="1" * 64),
        _img(image_id="b", split="calibration", specimen_id="S2", image_sha256="2" * 64),
        _img(image_id="c", split="sealed_test", specimen_id="S3", image_sha256="3" * 64),
    ]
    rep = generate_cohort_readiness_report(manifest)
    assert rep["n_images"] == 3 and rep["n_ready"] == 3
    assert rep["dimensions"]["metadata_completeness"]["ready"] is True
    assert rep["dimensions"]["statistical_adequacy"]["ready"] is False   # too few + no sign-off
    assert rep["dimensions"]["model_execution_readiness"]["ready"] is False
    assert rep["ready_for_scientific_benchmark"] is False
    assert rep["ready_for_benchmark"] is False


def test_empty_manifest_is_not_ready():
    rep = generate_cohort_readiness_report([])
    assert rep["ready_for_scientific_benchmark"] is False and rep["n_images"] == 0


# ── checkpoint governance (operator approval + SHA verification) ──────────────

def test_register_operator_approved_checkpoint_verifies_sha(tmp_path):
    w = tmp_path / "bb.pt"
    w.write_bytes(b"backbone-weights")
    # Research-execution backbone: approved for execution, NOT for scientific claims.
    rec = ckpt.register_operator_approved_checkpoint(
        "op_bb", file_path=str(w), architecture="resnet18", license="verified-by-operator",
        source_url="", description="operator approved", preprocessing={"resize": [256, 256]},
        compatibility_policy={"policy_id": "p", "reason": "r", "scientifically_valid": False},
        approver_id="op@x", research_execution_only=True,
    )
    assert rec.approved and rec.rights_cleared and rec.requires_file
    assert rec.scientific_use_approved is False
    assert rec.expected_sha256 == hashlib.sha256(b"backbone-weights").hexdigest()
    assert ckpt.verify_checkpoint("op_bb", file_path=str(w)).checkpoint_id == "op_bb"
    with pytest.raises(ckpt.CheckpointScientificUseError):
        ckpt.assert_scientific_checkpoint(rec)          # never for scientific claims
    w.write_bytes(b"tampered")
    with pytest.raises(ckpt.CheckpointVerificationError):
        ckpt.verify_checkpoint("op_bb", file_path=str(w))
    del ckpt._REGISTRY["op_bb"]


def test_checkpoint_governance_fails_closed_without_approver(tmp_path):
    w = tmp_path / "bb.pt"
    w.write_bytes(b"w")
    # No approver_id -> fail-closed.
    with pytest.raises(ckpt.CheckpointRightsError):
        ckpt.register_operator_approved_checkpoint(
            "no_approver", file_path=str(w), architecture="resnet18", license="x",
            source_url="", description="x")
    # Scientific approval without license/source evidence -> not rights-cleared.
    rec = ckpt.register_operator_approved_checkpoint(
        "no_evidence", file_path=str(w), architecture="resnet18", license="x", source_url="",
        description="x", approver_id="op@x")
    assert rec.rights_cleared is False and rec.scientific_use_approved is False
    with pytest.raises(ckpt.CheckpointRightsError):
        ckpt.verify_checkpoint("no_evidence", file_path=str(w))
    del ckpt._REGISTRY["no_evidence"]


def test_scientific_checkpoint_requires_license_and_source_evidence(tmp_path):
    w = tmp_path / "real.pt"
    w.write_bytes(b"real-weights")
    rec = ckpt.register_operator_approved_checkpoint(
        "sci_bb", file_path=str(w), architecture="resnet18", license="Apache-2.0",
        source_url="https://example/model", description="real scientific backbone",
        approver_id="reviewer@x", license_evidence_ref="LIC-1", source_evidence_ref="SRC-1")
    assert rec.rights_cleared is True and rec.scientific_use_approved is True
    ckpt.assert_scientific_checkpoint(rec)              # passes with full evidence
    del ckpt._REGISTRY["sci_bb"]


def test_imagenet_backbone_still_blocked():
    # Real ImageNet weights remain unapproved / rights-not-cleared by default.
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        ckpt.verify_checkpoint("resnet18_imagenet", file_path=None)


# ── governed localizer execution (torch/anomalib-gated) ──────────────────────

# ── §6 governance: readiness has no performance numbers; no promotion ─────────

def test_cohort_readiness_reports_no_performance_numbers():
    # Readiness must never contain accuracy/performance metrics — it reports only
    # what evidence is present/missing (no fabricated denominators or scores).
    rep = generate_cohort_readiness_report([_img(split="fit"), _img(image_id="b", split="sealed_test",
                                                                    specimen_id="S9", image_sha256="9" * 64)])
    forbidden = {"auroc", "sensitivity", "specificity", "accuracy", "precision", "recall", "dice", "iou", "fnr"}
    keys = set()

    def _collect(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.add(str(k).lower())
                _collect(v, prefix)
        elif isinstance(obj, list):
            for v in obj:
                _collect(v, prefix)
    _collect(rep)
    assert forbidden.isdisjoint(keys), f"readiness report leaked performance keys: {forbidden & keys}"


def test_research_benchmark_outputs_stay_research_only():
    from research.lens_vision.anomaly_experiment import run_anomaly_experiment
    from research.lens_vision.anomaly_localization import StubLocalizer
    from research.lens_vision.config import ResearchRunConfig
    from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset

    normal, test = synthetic_anomaly_dataset(n_normal=8, n_anomalous=4)
    cfg = ResearchRunConfig(run_id="g6a", seed=5, checkpoint_id="stub_backbone",
                            source_provenance_class="synthetic_experimental", embedder="stub_padim_like")
    rep = run_anomaly_experiment(normal, test, config=cfg, localizer=StubLocalizer(), synthetic_technical_test=True)
    assert rep["research_only"] is True
    for res in rep["results"]:
        assert res["research_only"] is True and res["clinical_promotion_eligible"] is False
        assert res["confirmed_diagnosis"] is None and res["human_review_required"] is True
        # No research field may authorize release or a candidate promotion.
        assert "promote" not in {k.lower() for k in res} or res.get("clinical_promotion_eligible") is False


@pytest.mark.skipif(not TORCH, reason="requires torch + anomalib (research venv)")
def test_governed_padim_executes_through_localizer(tmp_path):
    import torch
    from anomalib.models.image.padim.torch_model import PadimModel
    from research.lens_vision.anomaly_localization import PadimLocalizer
    from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset

    m = PadimModel(backbone="resnet18", layers=["layer1", "layer2", "layer3"], pre_trained=False, n_features=100)
    sd = m.feature_extractor.state_dict()
    path = tmp_path / "rn18.pt"
    torch.save(sd, path)
    ckpt.register_operator_approved_checkpoint(
        "rn18_test", file_path=str(path), architecture="resnet18", license="local", source_url="",
        description="test", preprocessing={"resize": [256, 256], "mean": [0.485, 0.456, 0.406],
                                           "std": [0.229, 0.224, 0.225]},
        compatibility_policy={"policy_id": "t", "reason": "t", "scientifically_valid": False},
        approver_id="op@x", research_execution_only=True)
    normal, test = synthetic_anomaly_dataset(n_normal=4, n_anomalous=2)
    lz = PadimLocalizer(backbone_checkpoint_id="rn18_test", file_path=str(path))
    lz.fit([s["image_bytes"] for s in normal])
    heatmap, score = lz.score(test[0]["image_bytes"])
    assert lz.load_report.coverage == 1.0 and lz.backbone_scientifically_valid is False
    assert len(heatmap) > 0 and len(heatmap[0]) > 0 and isinstance(score, float)
    del ckpt._REGISTRY["rn18_test"]
