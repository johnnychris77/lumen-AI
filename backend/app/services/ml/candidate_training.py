"""Genesis (Production Model Training, Scientific Validation & Model
Governance) — the full candidate-model training pipeline.

One call, no manual intervention after it starts: dataset validation
(reject-gate) -> duplicate detection -> preprocessing -> augmentation ->
training -> validation -> evaluation -> error analysis -> calibration ->
model export (artifact file) -> model registration -> model card
generation. Reuses rather than duplicates: ``training_execution``'s real
feature extraction and binary logistic-regression trainer (extended here to
one-vs-rest multi-class), ``dataset_split``'s leakage-safe split,
``dataset_integrity``'s reject-gate, ``evaluation``'s metrics,
``error_analysis``, ``augmentation``, and ``model_card``.

Scope (Section 1): the currently approved taxonomy only — debris,
corrosion, no_actionable_finding, and blood ONLY if at least
``MIN_SAMPLES_PER_CLASS`` validated blood samples exist. No other category
is ever trained or scored here; this pipeline does not expand the taxonomy.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.model_registry import ModelRegistryEntry
from app.services.ml.augmentation import augment_image_bytes
from app.services.ml.dataset_integrity import validate_dataset, validate_split
from app.services.ml.dataset_split import split_dataset
from app.services.ml.error_analysis import analyze_errors
from app.services.ml.evaluation import calibration_report as build_calibration_report
from app.services.ml.evaluation import evaluate
from app.services.ml.model_card import generate_model_card
from app.services.ml.training_config import TrainingConfig
from app.services.ml.training_execution import (
    _feature_vector,
    _predict_proba,
    _train_logistic_regression,
    git_commit,
)

CANDIDATE_CLASSES = ["debris", "corrosion", "no_actionable_finding"]
NEGATIVE_LABEL = "no_actionable_finding"
MIN_SAMPLES_PER_CLASS = 3
DEFAULT_ARTIFACT_DIR = os.getenv("LUMENAI_MODEL_ARTIFACT_DIR", "model_artifacts")


class DatasetInvalidError(ValueError):
    """Raised when the dataset fails the Section 4 integrity gate — the
    pipeline refuses to start (or continue) training rather than silently
    training on an invalid dataset."""

    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__(f"Dataset failed integrity validation: {report.get('reasons')}")


def resolve_candidate_classes(samples: list[dict[str, Any]]) -> list[str]:
    """Section 1 — use only the approved scope; include 'blood' only if
    sufficient validated data exists for it."""
    counts = Counter(s.get("label") for s in samples)
    classes = list(CANDIDATE_CLASSES)
    if counts.get("blood", 0) >= MIN_SAMPLES_PER_CLASS:
        classes.append("blood")
    return classes


def _train_one_vs_rest(
    X: list[list[float]], y: list[str], classes: list[str], *, epochs: int, learning_rate: float,
) -> dict[str, list[float]]:
    weights_by_class = {}
    for cls in classes:
        y_bin = [1 if label == cls else 0 for label in y]
        if len(set(y_bin)) < 2:
            continue  # cannot fit a one-vs-rest head with only one class present in the split
        weights_by_class[cls] = _train_logistic_regression(X, y_bin, epochs=epochs, learning_rate=learning_rate)
    return weights_by_class


def _predict_multiclass(
    weights_by_class: dict[str, list[float]], x: list[float], classes: list[str],
) -> tuple[str, float]:
    if not weights_by_class:
        return NEGATIVE_LABEL, 0.0
    scores = {cls: _predict_proba(w, x) for cls, w in weights_by_class.items()}
    best_class = max(scores, key=scores.get)
    return best_class, scores[best_class]


def run_candidate_training(
    samples: list[dict[str, Any]], *, config: TrainingConfig | None = None, dataset_version_id: int | None = None,
) -> dict[str, Any]:
    """Steps: dataset validation -> duplicate detection -> preprocessing ->
    augmentation -> training -> validation -> evaluation -> error analysis
    -> calibration. Pure computation (no DB, no filesystem) — see
    ``export_artifact()`` / ``run_full_candidate_pipeline()`` for the
    remaining "model export"/"model registration" steps.

    Each ``sample`` dict: ``{id, image_bytes, label, inspection_id,
    instrument_family, anatomy_zone, facility, manufacturer, image_sha256,
    annotation_disagreement, blur_flag, focus_flag, lighting_flag,
    exposure_flag, cropping_flag}``.
    """
    cfg = config or TrainingConfig()

    with_metadata = [s for s in samples if s.get("image_bytes") and s.get("label") is not None]
    integrity = validate_dataset(with_metadata)
    if not integrity["valid"]:
        raise DatasetInvalidError(integrity)

    classes = resolve_candidate_classes(with_metadata)

    features_by_id: dict[Any, list[float]] = {}
    for s in with_metadata:
        augmented = augment_image_bytes(
            s["image_bytes"], sample_id=str(s["id"]), seed=str(cfg.seed), augmentations=cfg.augmentation,
        )
        vec = _feature_vector(augmented)
        if vec is not None:
            features_by_id[s["id"]] = vec
    usable = [s for s in with_metadata if s["id"] in features_by_id]
    excluded_undecodable = len(with_metadata) - len(usable)

    normalized_labels = [s["label"] if s["label"] in classes else NEGATIVE_LABEL for s in usable]
    label_counts = Counter(normalized_labels)
    required_classes = [c for c in classes if c != "blood"] + (["blood"] if "blood" in classes else [])
    if any(label_counts.get(c, 0) < MIN_SAMPLES_PER_CLASS for c in required_classes):
        return {
            "training_status": "insufficient_data",
            "candidate_classes": classes,
            "label_counts": dict(label_counts),
            "minimum_required_per_class": MIN_SAMPLES_PER_CLASS,
            "sample_count": len(usable),
            "excluded_undecodable_image": excluded_undecodable,
            "config": cfg.to_dict(),
            "config_hash": cfg.config_hash(),
            "git_commit": git_commit(),
            "training_metrics": None,
            "validation_metrics": None,
            "evaluation_metrics": None,
            "error_analysis": None,
            "calibration_report": None,
            "note": (
                "Not enough labeled, decodable images per required class to train the "
                "candidate model. No metrics fabricated."
            ),
        }

    split = split_dataset(usable, seed=str(cfg.seed))
    samples_by_id = {s["id"]: s for s in usable}
    split_integrity = validate_split(split, samples_by_id)
    if not split_integrity["valid"]:
        raise DatasetInvalidError(split_integrity)

    assignments = split["assignments"]

    def _subset(name: str) -> list[dict]:
        return [s for s in usable if assignments.get(s["id"]) == name]

    train_samples, val_samples, test_samples = _subset("train"), _subset("validation"), _subset("test")

    X_train = [features_by_id[s["id"]] for s in train_samples]
    y_train = [s["label"] if s["label"] in classes else NEGATIVE_LABEL for s in train_samples]
    if len(train_samples) < 2 or len(set(y_train)) < 2:
        return {
            "training_status": "insufficient_data",
            "candidate_classes": classes,
            "split_counts": {"train": len(train_samples), "validation": len(val_samples), "test": len(test_samples)},
            "training_metrics": None, "validation_metrics": None, "evaluation_metrics": None,
            "error_analysis": None, "calibration_report": None,
            "note": "The training split does not contain enough distinct classes after leakage-safe grouping. No metrics fabricated.",
        }

    weights_by_class = _train_one_vs_rest(X_train, y_train, classes, epochs=cfg.epochs, learning_rate=cfg.learning_rate)

    def _predict_split(split_samples: list[dict]) -> tuple[list[str], list[str], list[float]]:
        y_true = [s["label"] if s["label"] in classes else NEGATIVE_LABEL for s in split_samples]
        y_pred, confidences = [], []
        for s in split_samples:
            cls, conf = _predict_multiclass(weights_by_class, features_by_id[s["id"]], classes)
            y_pred.append(cls)
            confidences.append(conf)
        return y_true, y_pred, confidences

    def _evaluate_split(split_samples: list[dict]) -> tuple[dict | None, list[dict]]:
        if not split_samples:
            return None, []
        y_true, y_pred, confidences = _predict_split(split_samples)
        report = evaluate(
            y_true, y_pred, classes,
            groups={
                "facility": [s.get("facility", "unknown") for s in split_samples],
                "manufacturer": [s.get("manufacturer", "unknown") for s in split_samples],
                "instrument_family": [s.get("instrument_family", "unknown") for s in split_samples],
                "anatomy_zone": [s.get("anatomy_zone", "unknown") for s in split_samples],
            },
        )
        error_samples = [
            {
                "id": s["id"], "true_label": t, "predicted_label": p, "confidence": c,
                "blur_flag": s.get("blur_flag"), "focus_flag": s.get("focus_flag"),
                "lighting_flag": s.get("lighting_flag"), "exposure_flag": s.get("exposure_flag"),
                "cropping_flag": s.get("cropping_flag"), "anatomy_zone": s.get("anatomy_zone"),
                "annotation_disagreement": s.get("annotation_disagreement"),
            }
            for s, t, p, c in zip(split_samples, y_true, y_pred, confidences)
        ]
        return report, error_samples

    train_report, _ = _evaluate_split(train_samples)
    validation_report, val_error_samples = _evaluate_split(val_samples)
    test_report, test_error_samples = _evaluate_split(test_samples)

    error_source = test_error_samples if test_samples else val_error_samples
    error_analysis = analyze_errors(error_source) if error_source else None

    calibration_split = test_samples or val_samples
    calibration = None
    if calibration_split:
        y_true, y_pred, confidences = _predict_split(calibration_split)
        correct = [t == p for t, p in zip(y_true, y_pred)]
        calibration = build_calibration_report(correct, confidences)

    return {
        "training_status": "trained",
        "candidate_classes": classes,
        "config": cfg.to_dict(),
        "config_hash": cfg.config_hash(),
        "sample_count": len(usable),
        "excluded_undecodable_image": excluded_undecodable,
        "split_counts": {"train": len(train_samples), "validation": len(val_samples), "test": len(test_samples)},
        "leakage_free": split_integrity["leakage_free"],
        "weights_by_class": weights_by_class,
        "training_metrics": train_report,
        "validation_metrics": validation_report,
        "evaluation_metrics": test_report,
        "error_analysis": error_analysis,
        "calibration_report": calibration,
        "dataset_version_id": dataset_version_id,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "note": (
            "Real, deterministic, pure-Python one-vs-rest logistic-regression baseline. "
            "Foundation-scale infrastructure demonstration — not a clinically validated model."
        ),
    }


def export_artifact(run: dict[str, Any], *, model_id: str, model_version: str, artifact_dir: str | None = None) -> str:
    """Model export (Section 3) — serialize the trained weights + config to
    a JSON file (never pickle: no arbitrary-code-execution risk on load).
    Returns the artifact path, or "" if there is nothing to export
    (insufficient_data runs produce no weights)."""
    if run.get("training_status") != "trained":
        return ""
    directory = artifact_dir or DEFAULT_ARTIFACT_DIR
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{model_id}_{model_version}.json")
    payload = {
        "model_id": model_id,
        "model_version": model_version,
        "candidate_classes": run["candidate_classes"],
        "weights_by_class": run["weights_by_class"],
        "config": run["config"],
        "config_hash": run["config_hash"],
        "git_commit": run["git_commit"],
        "trained_at": run["trained_at"],
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def run_full_candidate_pipeline(
    db: Session, *, tenant_id: str, samples: list[dict[str, Any]], config: TrainingConfig | None = None,
    model_id: str, model_version: str, dataset_version_id: int | None = None, artifact_dir: str | None = None,
) -> ModelRegistryEntry:
    """The single entry point satisfying "no manual intervention after
    training begins": runs training, exports the artifact, registers the
    model, and generates the model card, all in one call. Always returns a
    persisted ``ModelRegistryEntry`` — even an ``insufficient_data`` run is
    registered honestly (candidate_stage stays ``Experimental``) rather than
    silently discarded.
    """
    cfg = config or TrainingConfig()
    run = run_candidate_training(samples, config=cfg, dataset_version_id=dataset_version_id)
    artifact_path = export_artifact(run, model_id=model_id, model_version=model_version, artifact_dir=artifact_dir)

    trained = run["training_status"] == "trained"
    row = ModelRegistryEntry(
        tenant_id=tenant_id,
        model_id=model_id,
        model_version=model_version,
        model_type="candidate_finding_multiclass",
        dataset_version=str(dataset_version_id or ""),
        dataset_version_id=dataset_version_id,
        training_date=run.get("trained_at", ""),
        training_status=run["training_status"],
        architecture="logistic_regression_one_vs_rest_pure_python",
        framework="pure_python_baseline",
        hyperparameters=json.dumps(cfg.to_dict()),
        git_commit=run.get("git_commit", ""),
        training_metrics=json.dumps(run.get("training_metrics") or {}),
        evaluation_metrics=json.dumps(run.get("evaluation_metrics") or run.get("validation_metrics") or {}),
        calibration_report=json.dumps(run.get("calibration_report") or {}),
        error_analysis_report=json.dumps(run.get("error_analysis") or {}),
        artifact_path=artifact_path,
        training_run_id=run.get("config_hash", ""),
        candidate_stage="Candidate" if trained else "Experimental",
        known_limitations=(
            "Foundation-scale, small-sample logistic-regression baseline over Pillow-computed "
            "image features. Not clinically validated. Eligible only for Prospective "
            "Shadow-Mode Clinical Validation, never direct deployment."
            if trained else
            "Insufficient real, labeled, decodable training data at run time — no validated performance."
        ),
        approval_status="experimental",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    row.model_card_markdown = generate_model_card(row)
    db.commit()
    db.refresh(row)
    return row
