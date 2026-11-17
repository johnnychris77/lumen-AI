"""Stage 6C/6D §6 — traceable review records + match/miss/conflict.

Laboratory confirmation is a RESOLVED record-backed object (never an arbitrary bool).
"""
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
from research.lens_vision.scientific_authorization import LabConfirmation


def _confirmed(identity="iron_oxide", rid=7):
    return LabConfirmation(confirmed=True, identity=identity, evidence_record_id=rid, reason="resolved")


def _unconfirmed():
    return LabConfirmation(confirmed=False, identity=None, evidence_record_id=None, reason="no_evidence")


def test_compare_match_miss_conflict_and_unavailable():
    assert compare_prediction_to_ground_truth(
        predicted_positive=True, ground_truth_label="abnormal", lab_confirmed=True) == MATCH
    assert compare_prediction_to_ground_truth(
        predicted_positive=False, ground_truth_label="abnormal", lab_confirmed=True) == MISS
    assert compare_prediction_to_ground_truth(
        predicted_positive=True, ground_truth_label="verified_normal") == CONFLICT
    assert compare_prediction_to_ground_truth(
        predicted_positive=False, ground_truth_label="verified_normal") == MATCH
    assert compare_prediction_to_ground_truth(
        predicted_positive=True, ground_truth_label="abnormal", lab_confirmed=False) == GT_UNAVAILABLE
    assert compare_prediction_to_ground_truth(predicted_positive=True, ground_truth_label=None) == GT_UNAVAILABLE


def test_review_record_uses_resolved_lab_confirmation():
    r = build_review_record(
        specimen_id="SPEC-1", image_id=1, image_sha256="a" * 64, modality="borescope",
        model_name="padim", predicted_positive=True, anomaly_score=7.1, spatial_mask_ref="artifact://m",
        human_visual_interpretation="possible corrosion", visual_reviewer_id="rev@x",
        lab_confirmation=_confirmed("iron_oxide", 42), approved_ground_truth_label="abnormal")
    assert r.outcome == MATCH
    assert r.confirmed_material_identity == "iron_oxide"           # only from resolved evidence
    assert r.laboratory_evidence_ref == "veritas_evidence:42"
    assert r.clinical_disposition is None and r.confirmed_diagnosis is None
    assert r.severity_estimate is None and r.instrument_release_decision is None


def test_identity_not_set_without_resolved_confirmation():
    r = build_review_record(
        specimen_id="SPEC-2", image_id=2, image_sha256="b" * 64, model_name="patchcore",
        predicted_positive=True, lab_confirmation=_unconfirmed(), approved_ground_truth_label="abnormal")
    assert r.confirmed_material_identity is None and r.lab_confirmed is False
    assert r.outcome == GT_UNAVAILABLE


def test_no_confirmation_object_means_not_confirmed():
    r = build_review_record(
        specimen_id="SPEC-3", image_id=3, image_sha256="c" * 64, model_name="padim",
        predicted_positive=True, approved_ground_truth_label="abnormal")   # no lab_confirmation
    assert r.lab_confirmed is False and r.outcome == GT_UNAVAILABLE


def test_summarize_surfaces_false_negatives():
    recs = [
        build_review_record(specimen_id="s", image_id=0, image_sha256="x", model_name="padim",
                            predicted_positive=True, lab_confirmation=_confirmed(), approved_ground_truth_label="abnormal"),
        build_review_record(specimen_id="s", image_id=1, image_sha256="x", model_name="padim",
                            predicted_positive=False, lab_confirmation=_confirmed(), approved_ground_truth_label="abnormal"),
        build_review_record(specimen_id="s", image_id=2, image_sha256="x", model_name="padim",
                            predicted_positive=True, approved_ground_truth_label="verified_normal"),
        build_review_record(specimen_id="s", image_id=3, image_sha256="x", model_name="padim",
                            predicted_positive=True, lab_confirmation=_unconfirmed(), approved_ground_truth_label="abnormal"),
    ]
    summ = summarize_outcomes(recs)
    assert summ["false_negatives"] == 1 and summ["conflicts"] == 1
    assert summ["outcomes"][MATCH] == 1 and summ["ground_truth_unavailable"] == 1
    assert "accuracy" not in summ
