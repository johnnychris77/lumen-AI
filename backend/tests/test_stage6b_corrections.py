"""Stage 6B — regression tests for the three independent-review corrections (§2).

1. Comprehensive grouping / leakage over ALL identity tokens, across modalities.
2. Checkpoint governance fail-closed; random-weight backbone never scientific.
3. Readiness integrity decomposed into independent dimensions; small/complete
   manifests are never "scientifically ready".
"""
from __future__ import annotations

import pytest

# Init app layer before research imports (cold circular-import avoidance).
from app.db.session import SessionLocal  # noqa: F401

from research.lens_vision import checkpoint as ckpt
from research.lens_vision.cohort_readiness import (
    GT_VERIFIED_NORMAL,
    MODALITY_BORESCOPE,
    MODALITY_EXTERNAL,
    generate_cohort_readiness_report,
    image_identity_tokens,
    validate_image_readiness,
)


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


# ── §2a comprehensive grouping / leakage ─────────────────────────────────────

def test_identity_tokens_are_comprehensive():
    toks = image_identity_tokens(_img(repeat_imaging_group="R1"))
    assert "instrument:INS-1" in toks and "specimen:SPEC-1" in toks
    assert "session:SESS-1" in toks and "batch:BATCH-1" in toks
    assert "sha:" + "a" * 64 in toks and "repeat:R1" in toks


def test_instrument_level_leakage_detected_even_with_different_specimens():
    # Different specimens, but the SAME physical instrument appears in fit and
    # sealed_test — first-identity-only grouping (Stage 6A) would have missed this.
    manifest = [
        _img(image_id="a", split="fit", instrument_id="INS-9", specimen_id="S1", image_sha256="1" * 64),
        _img(image_id="b", split="sealed_test", instrument_id="INS-9", specimen_id="S2", image_sha256="2" * 64),
    ]
    rep = generate_cohort_readiness_report(manifest)
    assert rep["cross_split_leakage"]
    assert any("instrument:INS-9" in x for x in rep["cross_split_leakage"])
    assert rep["ready_for_scientific_benchmark"] is False


def test_leakage_detected_across_modalities():
    # Same specimen imaged in external (fit) and borescope (sealed_test) is leakage.
    manifest = [
        _img(image_id="a", split="fit", modality=MODALITY_EXTERNAL, specimen_id="SP-X", image_sha256="1" * 64),
        _img(image_id="b", split="sealed_test", modality=MODALITY_BORESCOPE, specimen_id="SP-X",
             image_sha256="2" * 64),
    ]
    rep = generate_cohort_readiness_report(manifest)
    assert any("specimen:SP-X" in x for x in rep["cross_split_leakage"])


def test_repeat_imaging_relationship_prevents_split_straddle():
    manifest = [
        _img(image_id="a", split="fit", specimen_id="S1", image_sha256="1" * 64, repeat_imaging_group="RG"),
        _img(image_id="b", split="validation", specimen_id="S2", image_sha256="2" * 64, repeat_imaging_group="RG"),
    ]
    rep = generate_cohort_readiness_report(manifest)
    assert any("repeat:RG" in x for x in rep["cross_split_leakage"])


# ── §2b checkpoint governance fail-closed ────────────────────────────────────

def test_random_weight_checkpoint_never_scientific(tmp_path):
    w = tmp_path / "rand.pt"
    w.write_bytes(b"random")
    rec = ckpt.register_operator_approved_checkpoint(
        "rand_exec", file_path=str(w), architecture="resnet18", license="n/a", source_url="",
        description="random", compatibility_policy={"policy_id": "p", "reason": "r",
                                                     "scientifically_valid": False},
        approver_id="op@x", research_execution_only=True)
    assert rec.rights_cleared is True and rec.scientific_use_approved is False
    with pytest.raises(ckpt.CheckpointScientificUseError):
        ckpt.assert_scientific_checkpoint(rec)
    del ckpt._REGISTRY["rand_exec"]


def test_scientific_use_requires_evidence_even_with_real_weights(tmp_path):
    w = tmp_path / "real.pt"
    w.write_bytes(b"weights")
    # Real weights but NO license/source evidence -> not scientific, not rights-cleared.
    rec = ckpt.register_operator_approved_checkpoint(
        "real_noev", file_path=str(w), architecture="resnet18", license="Apache-2.0", source_url="u",
        description="real", approver_id="op@x")
    assert rec.scientific_use_approved is False and rec.rights_cleared is False
    with pytest.raises(ckpt.CheckpointScientificUseError):
        ckpt.assert_scientific_checkpoint(rec)
    del ckpt._REGISTRY["real_noev"]


# ── §2c readiness integrity decomposition ────────────────────────────────────

def test_readiness_has_five_independent_dimensions():
    rep = generate_cohort_readiness_report([_img()])
    dims = rep["dimensions"]
    assert set(dims) == {
        "metadata_completeness", "verified_authorization", "ground_truth_readiness",
        "model_execution_readiness", "statistical_adequacy",
    }


def test_complete_manifest_not_ready_without_stats_and_checkpoint():
    # Even a large, complete, leakage-free manifest is not scientifically ready
    # without a statistical-reviewer sign-off AND an approved scientific checkpoint.
    manifest = []
    for sp, n in (("fit", 25), ("calibration", 25), ("validation", 25), ("sealed_test", 35)):
        for i in range(n):
            # Every physical identity is unique per image -> no cross-split leakage.
            manifest.append(_img(
                image_id=f"{sp}-{i}", split=sp,
                instrument_id=f"{sp}-INS{i}", specimen_id=f"{sp}-S{i}",
                imaging_session_id=f"{sp}-SESS{i}", study_batch_id=f"{sp}-B{i}",
                image_sha256=f"{sp}{i:060d}"[:64].ljust(64, '0')))
    rep = generate_cohort_readiness_report(manifest)
    assert rep["dimensions"]["statistical_adequacy"]["ready"] is False      # no sign-off
    assert rep["dimensions"]["model_execution_readiness"]["ready"] is False  # no checkpoint
    assert rep["ready_for_scientific_benchmark"] is False
    # With both supplied, and sizes met, it becomes ready.
    rep2 = generate_cohort_readiness_report(
        manifest, scientific_checkpoint_approved=True,
        statistical_reviewer_signoff={"reviewer": "stat@x", "approved_sizes": True})
    assert rep2["dimensions"]["statistical_adequacy"]["ready"] is True
    assert rep2["ready_for_scientific_benchmark"] is True


def test_metadata_and_authorization_dimensions_separate():
    # Missing authorization but complete other metadata: only authorization fails.
    img = _img(institutional_authorization_ref="", data_rights="")
    r = validate_image_readiness(img)
    assert r["authorization_blockers"] and not r["ground_truth_blockers"]
