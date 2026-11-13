"""Stage 6C §6 — traceable review records + match/miss/conflict comparison."""
from __future__ import annotations

from app.db.session import SessionLocal  # noqa: F401  (init app layer first)

from research.lens_vision.review_record import (
    CONFLICT,
    GT_UNAVAILABLE,
    MATCH,
    MISS,
    build_review_record,
    compare_prediction_to_ground_truth,
    summarize_outcomes,
)


def test_compare_match_miss_conflict_and_unavailable():
    # Predicted positive, lab-confirmed abnormal -> match.
    assert compare_prediction_to_ground_truth(
        predicted_positive=True, ground_truth_label="abnormal", lab_confirmed=True) == MATCH
    # Predicted negative, lab-confirmed abnormal -> miss (false negative).
    assert compare_prediction_to_ground_truth(
        predicted_positive=False, ground_truth_label="abnormal", lab_confirmed=True) == MISS
    # Predicted positive, verified-normal -> conflict (false positive).
    assert compare_prediction_to_ground_truth(
        predicted_positive=True, ground_truth_label="verified_normal") == CONFLICT
    # Predicted negative, verified-normal -> match.
    assert compare_prediction_to_ground_truth(
        predicted_positive=False, ground_truth_label="verified_normal") == MATCH
    # Abnormal but NOT lab-confirmed -> truth not established.
    assert compare_prediction_to_ground_truth(
        predicted_positive=True, ground_truth_label="abnormal", lab_confirmed=False) == GT_UNAVAILABLE
    # No / unknown label -> unavailable.
    assert compare_prediction_to_ground_truth(predicted_positive=True, ground_truth_label=None) == GT_UNAVAILABLE


def test_review_record_keeps_layers_and_no_disposition():
    r = build_review_record(
        specimen_id="SPEC-1", image_id=1, image_sha256="a" * 64, modality="borescope",
        model_name="padim", predicted_positive=True, anomaly_score=7.1, spatial_mask_ref="artifact://m",
        human_visual_interpretation="possible corrosion", visual_reviewer_id="rev@x",
        laboratory_evidence_ref="LAB-1", lab_confirmed=True, confirmed_material_identity="iron_oxide",
        approved_ground_truth_label="abnormal")
    assert r.outcome == MATCH
    assert r.confirmed_material_identity == "iron_oxide"      # only because lab_confirmed
    assert r.clinical_disposition is None and r.confirmed_diagnosis is None
    assert r.severity_estimate is None and r.instrument_release_decision is None
    assert r.research_only is True and r.human_review_required is True


def test_identity_not_set_without_lab_confirmation():
    r = build_review_record(
        specimen_id="SPEC-2", image_id=2, image_sha256="b" * 64, model_name="patchcore",
        predicted_positive=True, confirmed_material_identity="hemoglobin", lab_confirmed=False,
        approved_ground_truth_label="abnormal")
    # AI prediction alone never establishes identity, and truth is not established.
    assert r.confirmed_material_identity is None
    assert r.outcome == GT_UNAVAILABLE


def test_summarize_surfaces_false_negatives():
    recs = [
        build_review_record(specimen_id="s", image_id=i, image_sha256="x", model_name="padim",
                            predicted_positive=pp, lab_confirmed=lc, approved_ground_truth_label=gt)
        for i, (pp, gt, lc) in enumerate([
            (True, "abnormal", True),     # match
            (False, "abnormal", True),    # miss (FN)
            (True, "verified_normal", False),  # conflict (FP)
            (True, "abnormal", False),    # unavailable
        ])
    ]
    summ = summarize_outcomes(recs)
    assert summ["false_negatives"] == 1 and summ["conflicts"] == 1
    assert summ["outcomes"][MATCH] == 1 and summ["ground_truth_unavailable"] == 1
    assert "accuracy" not in summ  # counts only, no accuracy claim
