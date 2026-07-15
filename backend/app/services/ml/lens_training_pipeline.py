"""Project Lens — Sections 5-10: the hierarchical (Stage A/B/C) candidate
training pipeline.

Reuses rather than duplicates: ``training_execution``'s real Pillow-computed
feature vector and pure-Python logistic-regression trainer,
``candidate_training``'s one-vs-rest multiclass helpers,
``dataset_integrity``'s reject-gate, ``dataset_split``'s leakage-safe split,
``augmentation``'s deterministic transforms, ``evaluation``'s metrics/
calibration-bin report, ``error_analysis``'s root-cause classification, and
``lens_calibration``'s temperature scaling — no metric or trainer is
reimplemented here.

Stage A (image-quality gate) is NOT a trained model — every sample reaching
this pipeline already passed the real, pixel-computed quality assessment at
ingestion time (``app.services.ml.image_quality``); Stage A's abstention
outcome is applied by the live adapter at inference time (Section 2), not
trained here.
"""
from __future__ import annotations

import json
import os
from typing import Any

from app.services.ml.augmentation import augment_image_bytes
from app.services.ml.candidate_training import _predict_multiclass, _train_one_vs_rest
from app.services.ml.dataset_integrity import check_class_balance, check_diversity, check_no_duplicate_images
from app.services.ml.dataset_split import has_no_group_leakage, split_dataset
from app.services.ml.error_analysis import analyze_errors
from app.services.ml.evaluation import calibration_report as build_calibration_report
from app.services.ml.evaluation import evaluate
from app.services.ml.lcid_service import is_untracked_twin
from app.services.ml.lens_calibration import calibrated_confidences, fit_temperature, resolve_abstention_threshold
from app.services.ml.training_config import TrainingConfig
from app.services.ml.training_execution import _feature_vector, _predict_proba, _train_logistic_regression, git_commit

NEGATIVE_LABEL = "no_observable_abnormality"
PREPROCESSING_VERSION = "lens-pillow-features-v1"  # brightness/sharpness/aspect, see training_execution._feature_vector
DEFAULT_ARTIFACT_DIR = os.getenv("LUMENAI_MODEL_ARTIFACT_DIR", "model_artifacts")


class DatasetInvalidError(ValueError):
    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__(f"Dataset failed integrity checks: {report}")


def predict_stage_b(stage_b_weights: list[float] | None, x: list[float]) -> tuple[str, float]:
    """Shared by training-time evaluation and the live inference adapter —
    identical code path, not two implementations of the same rule."""
    if stage_b_weights is None:
        return "observable_abnormality", 1.0  # no negative-class evidence to gate on; never fabricate a quality gate
    p = _predict_proba(stage_b_weights, x)
    return (NEGATIVE_LABEL, 1 - p) if p < 0.5 else ("observable_abnormality", p)


def predict_hierarchical_from_weights(
    *, stage_b_weights: list[float] | None, stage_c_weights_by_class: dict[str, list[float]],
    eligible_classes: list[str], feature_vector: list[float],
) -> tuple[str, float]:
    """The one hierarchical (Stage B -> Stage C) prediction function — used
    identically by ``run_lens_training()``'s own evaluation and by
    ``live_inference_adapter.predict()``, so a live prediction is
    provably the same computation the registered evaluation metrics
    describe, not a second, drifting reimplementation."""
    b_label, b_conf = predict_stage_b(stage_b_weights, feature_vector)
    if b_label == NEGATIVE_LABEL:
        return NEGATIVE_LABEL, b_conf
    if not stage_c_weights_by_class:
        return "unknown_review_required", 0.0
    return _predict_multiclass(stage_c_weights_by_class, feature_vector, eligible_classes)


def _to_split_sample(s: dict[str, Any]) -> dict[str, Any]:
    """Map an eligibility-report sample onto ``dataset_split.split_dataset``'s
    expected shape — grouping by ``digital_twin_id`` (Section 6 fix) rather
    than leaving every image its own ungrouped sample.

    A ``digital_twin_id`` of the form ``untracked:{instrument_type}:{...}``
    (``lcid_service.is_untracked_twin()``) is NOT a real distinguishable
    physical instrument — it is `instrument_digital_twin_id()`'s honest
    fallback for "no barcode/UDI captured." Feeding it to the splitter as a
    grouping key would incorrectly collapse every image sharing an
    instrument *type* (not a real instrument) into one giant group. Only a
    real, barcode/UDI-backed twin ID is used for grouping; an untracked one
    falls back to `dataset_split`'s own per-inspection/per-sample grouping.
    """
    twin_id = s.get("digital_twin_id") or ""
    instrument_serial = twin_id if twin_id and not is_untracked_twin(twin_id) else None
    return {
        "id": s["id"],
        "inspection_id": s.get("inspection_id"),
        "instrument_serial": instrument_serial,
        "instrument_family": s.get("instrument_family", "unknown"),
        "anatomy_zone": s.get("anatomy_zone", "unknown"),
        "finding": s.get("label", "none"),
        "severity": "none",
        "manufacturer": s.get("manufacturer", "unknown"),
        "image_quality": s.get("image_quality", "unknown"),
    }


def run_lens_training(
    eligibility: dict[str, Any], *, config: TrainingConfig | None = None,
) -> dict[str, Any]:
    """Pure computation (no DB, no filesystem) over an eligibility report's
    ``samples``. Returns training/evaluation/calibration/error-analysis
    results for both Stage B (abnormality) and Stage C (category)."""
    cfg = config or TrainingConfig()
    samples = eligibility["samples"]
    eligible_classes = [c for c in eligibility["eligible_classes"] if c != NEGATIVE_LABEL]
    has_negative_class = NEGATIVE_LABEL in eligibility["eligible_classes"]

    if not samples:
        return {
            "training_status": "insufficient_data",
            "note": "No eligible samples were available for training.",
            "eligible_classes": eligible_classes,
        }

    dup_check = check_no_duplicate_images(samples)
    if not dup_check["passed"]:
        raise DatasetInvalidError({"duplicate_images": dup_check})

    # ── Feature extraction (augmented, deterministic) ───────────────────────
    features_by_id: dict[Any, list[float]] = {}
    for s in samples:
        augmented = augment_image_bytes(
            s["image_bytes"], sample_id=str(s["id"]), seed=str(cfg.seed), augmentations=cfg.augmentation,
        )
        vec = _feature_vector(augmented)
        if vec is not None:
            features_by_id[s["id"]] = vec
    usable = [s for s in samples if s["id"] in features_by_id]
    excluded_undecodable = len(samples) - len(usable)

    # ── Leakage-safe split, grouped by physical-instrument identity ─────────
    split_samples = [_to_split_sample(s) for s in usable]
    split = split_dataset(split_samples, seed=str(cfg.seed), group_by_serial=True)
    leakage_free = has_no_group_leakage(split)
    if not leakage_free:
        raise DatasetInvalidError({"leakage_free": leakage_free})

    assignments = split["assignments"]
    by_id = {s["id"]: s for s in usable}

    def _subset(name: str) -> list[dict]:
        return [by_id[sid] for sid, split_name in assignments.items() if split_name == name and sid in by_id]

    train_samples, val_samples, test_samples = _subset("train"), _subset("validation"), _subset("test")

    diversity = check_diversity(usable)
    balance = {
        "train": check_class_balance(train_samples, split_name="train"),
        "validation": check_class_balance(val_samples, split_name="validation"),
        "test": check_class_balance(test_samples, split_name="test"),
    }

    if len(train_samples) < 2:
        return {
            "training_status": "insufficient_data",
            "note": "The training split has fewer than 2 samples after leakage-safe grouping.",
            "split_counts": {"train": len(train_samples), "validation": len(val_samples), "test": len(test_samples)},
            "eligible_classes": eligible_classes,
        }

    # ── Stage B — abnormality detector (binary one-vs-rest) ────────────────
    def _binary_labels(subset: list[dict]) -> list[int]:
        return [0 if s["label"] == NEGATIVE_LABEL else 1 for s in subset]

    X_train = [features_by_id[s["id"]] for s in train_samples]
    y_train_bin = _binary_labels(train_samples)
    stage_b_weights: list[float] | None = None
    if has_negative_class and len(set(y_train_bin)) >= 2:
        stage_b_weights = _train_logistic_regression(X_train, y_train_bin, epochs=cfg.epochs, learning_rate=cfg.learning_rate)

    # ── Stage C — category classifier (multiclass one-vs-rest), abnormal-only ──
    abnormal_train = [s for s in train_samples if s["label"] != NEGATIVE_LABEL]
    X_abnormal = [features_by_id[s["id"]] for s in abnormal_train]
    y_abnormal = [s["label"] for s in abnormal_train]
    stage_c_weights = (
        _train_one_vs_rest(X_abnormal, y_abnormal, eligible_classes, epochs=cfg.epochs, learning_rate=cfg.learning_rate)
        if eligible_classes and len(abnormal_train) >= 2 else {}
    )

    def _evaluate_split(split_samples_: list[dict]) -> tuple[dict | None, list[dict], list[bool], list[float]]:
        if not split_samples_:
            return None, [], [], []
        y_true = [s["label"] for s in split_samples_]
        y_pred, confidences = [], []
        for s in split_samples_:
            label, conf = predict_hierarchical_from_weights(
                stage_b_weights=stage_b_weights, stage_c_weights_by_class=stage_c_weights,
                eligible_classes=eligible_classes, feature_vector=features_by_id[s["id"]],
            )
            y_pred.append(label)
            confidences.append(conf)
        all_classes = sorted(set(y_true) | set(y_pred))
        report = evaluate(
            y_true, y_pred, all_classes,
            groups={
                "facility": [s.get("facility", "unknown") for s in split_samples_],
                "manufacturer": [s.get("manufacturer", "unknown") for s in split_samples_],
                "instrument_family": [s.get("instrument_family", "unknown") for s in split_samples_],
                "anatomy_zone": [s.get("anatomy_zone", "unknown") for s in split_samples_],
                "image_quality": [s.get("image_quality", "unknown") for s in split_samples_],
            },
        )
        error_samples = [
            {
                "id": s["id"], "true_label": t, "predicted_label": p, "confidence": c,
                "anatomy_zone": s.get("anatomy_zone"), "annotation_disagreement": False,
            }
            for s, t, p, c in zip(split_samples_, y_true, y_pred, confidences)
        ]
        correct = [t == p for t, p in zip(y_true, y_pred)]
        return report, error_samples, correct, confidences

    train_report, _, _, _ = _evaluate_split(train_samples)
    validation_report, val_errors, val_correct, val_conf = _evaluate_split(val_samples)
    test_report, test_errors, test_correct, test_conf = _evaluate_split(test_samples)

    calibration_split_correct = test_correct or val_correct
    calibration_split_conf = test_conf or val_conf
    temperature_fit = fit_temperature(calibration_split_correct, calibration_split_conf) if calibration_split_correct else {
        "temperature": 1.0, "nll": None, "note": "No held-out predictions to fit a temperature on.",
    }
    calibrated = calibrated_confidences(calibration_split_conf, temperature_fit["temperature"]) if calibration_split_conf else []
    reliability = build_calibration_report(calibration_split_correct, calibrated) if calibration_split_correct else {
        "bins": [], "expected_calibration_error": None, "recommended_threshold": None,
        "note": "No predictions to calibrate.",
    }
    abstention_threshold, threshold_is_data_derived = resolve_abstention_threshold(reliability)

    error_source = test_errors or val_errors
    error_analysis = analyze_errors(error_source) if error_source else None

    return {
        "training_status": "trained",
        "eligible_classes": eligible_classes,
        "has_negative_class": has_negative_class,
        "config": cfg.to_dict(),
        "config_hash": cfg.config_hash(),
        "preprocessing_version": PREPROCESSING_VERSION,
        "sample_count": len(usable),
        "excluded_undecodable_image": excluded_undecodable,
        "split_counts": {"train": len(train_samples), "validation": len(val_samples), "test": len(test_samples)},
        "leakage_free": leakage_free,
        "diversity": diversity,
        "class_balance": balance,
        "stage_b_weights": stage_b_weights,
        "stage_c_weights_by_class": stage_c_weights,
        "training_metrics": train_report,
        "validation_metrics": validation_report,
        "evaluation_metrics": test_report,
        "calibration": {
            "temperature": temperature_fit["temperature"],
            "temperature_fit_nll": temperature_fit["nll"],
            "temperature_fit_note": temperature_fit["note"],
            "reliability_report": reliability,
            "abstention_threshold": abstention_threshold,
            "abstention_threshold_is_data_derived": threshold_is_data_derived,
        },
        "error_analysis": error_analysis,
        "git_commit": git_commit(),
        "label_counts": eligibility["label_counts"],
        "not_evaluated_classes": eligibility["excluded_classes"],
        "data_provenance": eligibility["data_provenance"],
        "note": (
            "Real, deterministic, pure-Python hierarchical (Stage B abnormality / Stage C category) "
            "one-vs-rest logistic-regression baseline over Pillow-computed image features. "
            "Foundation-scale infrastructure — not a clinically validated model."
        ),
    }


def export_artifact(run: dict[str, Any], *, model_id: str, model_version: str, artifact_dir: str | None = None) -> tuple[str, str]:
    """Model export (Section 11) — JSON only, never pickle. Returns
    ``(artifact_path, sha256_checksum)``; empty strings when there is
    nothing to export (insufficient_data runs)."""
    import hashlib

    if run.get("training_status") != "trained":
        return "", ""
    directory = artifact_dir or DEFAULT_ARTIFACT_DIR
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{model_id}_{model_version}.json")
    payload = {
        "model_id": model_id,
        "model_version": model_version,
        "eligible_classes": run["eligible_classes"],
        "negative_label": NEGATIVE_LABEL,
        "has_negative_class": run["has_negative_class"],
        "stage_b_weights": run["stage_b_weights"],
        "stage_c_weights_by_class": run["stage_c_weights_by_class"],
        "preprocessing_version": run["preprocessing_version"],
        "calibration": run["calibration"],
        "config": run["config"],
        "config_hash": run["config_hash"],
        "git_commit": run["git_commit"],
        "not_evaluated_classes": run["not_evaluated_classes"],
        "data_provenance": run["data_provenance"],
    }
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    with open(path, "w") as f:
        f.write(serialized)
    checksum = hashlib.sha256(serialized.encode()).hexdigest()
    return path, checksum
