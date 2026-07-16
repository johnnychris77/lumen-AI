"""Dataset Registry & AI Model Development Foundation — Section 10.

Real training-pipeline execution. Extends (does not replace)
``app.services.ml.training_pipeline.prepare_training_run()``, which
deliberately stops short of executing training because — until this pass —
no labeled image bytes were available to train on. This module adds the
actual execution step for when real, decodable image bytes and labels DO
exist (e.g. opt-in ``RetainedImage`` rows), producing a genuinely trained,
genuinely evaluated baseline classifier.

Scope, by design:
  * No new label taxonomy — trains a binary detector for one EXISTING label
    from ``app.services.ml.model_tasks.FINDING_LABELS`` (default "debris")
    versus everything else, exactly the categories this platform's deployed
    model already targets (see Sprint 2's ``SUPPORTED_MODEL_CATEGORIES``).
  * No numpy/sklearn dependency — a small, real, pure-Python logistic
    regression trained by gradient descent over Pillow-computed image
    features (brightness, sharpness, aspect ratio — the same real
    computation as ``app.services.ml.image_quality``).
  * Deterministic and reproducible: no random initialization or shuffling;
    the leakage-safe split is seeded (``app.services.ml.dataset_split``).
  * Honest about scale: this is foundation-level infrastructure ("the
    output of this sprint is NOT a better model"), not a clinically
    validated classifier. When too little real data exists — the common
    case in this repository today — it reports ``insufficient_data``
    rather than fabricating metrics, exactly like ``prepare_training_run``
    already does for the "no labeled dataset" case.
"""
from __future__ import annotations

import json
import math
import subprocess
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.services.ml.dataset_split import has_no_group_leakage, split_dataset
from app.services.ml.evaluation import evaluate, roc_curve
from app.services.ml.image_quality import assess_image_bytes

MIN_SAMPLES_PER_CLASS = 3
ARCHITECTURE = "logistic_regression_pure_python"
FRAMEWORK = "pure_python_baseline"
DEFAULT_HYPERPARAMETERS = {"epochs": 500, "learning_rate": 0.3}


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _feature_vector(image_bytes: bytes) -> list[float] | None:
    q = assess_image_bytes(image_bytes)
    if not q["decodable"]:
        return None
    aspect = (q["width"] / q["height"]) if q["height"] else 0.0
    return [q["brightness_mean"] / 255.0, min(q["sharpness_score"] / 50.0, 1.0), aspect]


def _sigmoid(z: float) -> float:
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def _train_logistic_regression(
    X: list[list[float]], y: list[int], *, epochs: int, learning_rate: float,
) -> list[float]:
    n_features = len(X[0])
    weights = [0.0] * (n_features + 1)  # index 0 is the bias term
    n = len(X)
    for _ in range(epochs):
        grads = [0.0] * (n_features + 1)
        for xi, yi in zip(X, y):
            z = weights[0] + sum(w * x for w, x in zip(weights[1:], xi))
            error = _sigmoid(z) - yi
            grads[0] += error
            for j, x in enumerate(xi):
                grads[j + 1] += error * x
        weights = [w - learning_rate * (g / n) for w, g in zip(weights, grads)]
    return weights


def _predict_proba(weights: list[float], x: list[float]) -> float:
    z = weights[0] + sum(w * xi for w, xi in zip(weights[1:], x))
    return _sigmoid(z)


def run_training_pipeline(
    samples: list[dict[str, Any]],
    *,
    positive_label: str = "debris",
    seed: str = "lumenai-v1",
    hyperparameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Steps: load dataset (``samples``) -> validate metadata -> preprocess
    images -> train -> validate -> evaluate -> export model.

    Each sample dict: ``{id, image_bytes, label, inspection_id,
    instrument_family, ...}`` (extra fields are passed through to the
    leakage-safe splitter for grouping/stratification).
    """
    hp = {**DEFAULT_HYPERPARAMETERS, **(hyperparameters or {})}

    # ── Validate metadata ────────────────────────────────────────────────
    with_metadata = [s for s in samples if s.get("image_bytes") and s.get("label") is not None]
    excluded_invalid_metadata = len(samples) - len(with_metadata)

    # ── Preprocess images (real feature extraction, not fabricated) ──────
    features_by_id: dict[Any, list[float]] = {}
    for s in with_metadata:
        vec = _feature_vector(s["image_bytes"])
        if vec is not None:
            features_by_id[s["id"]] = vec
    usable = [s for s in with_metadata if s["id"] in features_by_id]
    excluded_undecodable = len(with_metadata) - len(usable)

    label_counts = Counter(s["label"] for s in usable)
    pos_count = label_counts.get(positive_label, 0)
    neg_count = len(usable) - pos_count

    if pos_count < MIN_SAMPLES_PER_CLASS or neg_count < MIN_SAMPLES_PER_CLASS:
        return {
            "training_status": "insufficient_data",
            "sample_count": len(usable),
            "excluded_invalid_metadata": excluded_invalid_metadata,
            "excluded_undecodable_image": excluded_undecodable,
            "positive_count": pos_count,
            "negative_count": neg_count,
            "minimum_required_per_class": MIN_SAMPLES_PER_CLASS,
            "model_artifact": None,
            "training_metrics": None,
            "validation_metrics": None,
            "evaluation_metrics": None,
            "note": (
                "Not enough labeled, decodable images to train a meaningful model "
                f"(need >= {MIN_SAMPLES_PER_CLASS} of '{positive_label}' and >= "
                f"{MIN_SAMPLES_PER_CLASS} other). No metrics fabricated."
            ),
        }

    # ── Split (leakage-safe, reused from Section 7) ──────────────────────
    split = split_dataset(usable, seed=seed)
    leakage_free = has_no_group_leakage(split)
    assignments = split["assignments"]

    def _subset(split_name: str) -> list[dict]:
        return [s for s in usable if assignments.get(s["id"]) == split_name]

    train_samples, val_samples, test_samples = _subset("train"), _subset("validation"), _subset("test")

    y_train = [1 if s["label"] == positive_label else 0 for s in train_samples]
    if len(train_samples) < 2 or len(set(y_train)) < 2:
        return {
            "training_status": "insufficient_data",
            "sample_count": len(usable),
            "split_counts": {"train": len(train_samples), "validation": len(val_samples), "test": len(test_samples)},
            "model_artifact": None,
            "training_metrics": None,
            "validation_metrics": None,
            "evaluation_metrics": None,
            "note": "The training split does not contain both classes after leakage-safe grouping. No metrics fabricated.",
        }

    # ── Train (real, pure-Python logistic regression) ────────────────────
    X_train = [features_by_id[s["id"]] for s in train_samples]
    weights = _train_logistic_regression(X_train, y_train, epochs=hp["epochs"], learning_rate=hp["learning_rate"])

    def _evaluate_split(split_samples: list[dict]) -> dict[str, Any] | None:
        if not split_samples:
            return None
        X = [features_by_id[s["id"]] for s in split_samples]
        y_true_bin = [1 if s["label"] == positive_label else 0 for s in split_samples]
        scores = [_predict_proba(weights, x) for x in X]
        y_pred_bin = [1 if p >= 0.5 else 0 for p in scores]
        y_true_labels = ["positive" if v else "negative" for v in y_true_bin]
        y_pred_labels = ["positive" if v else "negative" for v in y_pred_bin]
        report = evaluate(y_true_labels, y_pred_labels, ["positive", "negative"])
        report["roc"] = roc_curve(y_true_bin, scores)
        return report

    return {
        "training_status": "trained",
        "sample_count": len(usable),
        "excluded_invalid_metadata": excluded_invalid_metadata,
        "excluded_undecodable_image": excluded_undecodable,
        "split_counts": {"train": len(train_samples), "validation": len(val_samples), "test": len(test_samples)},
        "leakage_free": leakage_free,
        "positive_label": positive_label,
        "architecture": ARCHITECTURE,
        "framework": FRAMEWORK,
        "hyperparameters": hp,
        "model_weights": weights,
        "training_metrics": _evaluate_split(train_samples),
        "validation_metrics": _evaluate_split(val_samples),
        "evaluation_metrics": _evaluate_split(test_samples),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "note": (
            "Real logistic-regression baseline trained on real, Pillow-computed image "
            "features. Foundation-scale infrastructure demonstration — not a clinically "
            "validated model. human_review_required is always true regardless of this result."
        ),
    }


def build_registry_payload(
    run: dict[str, Any], *, model_id: str, model_version: str, model_type: str = "finding",
    dataset_version: str = "", dataset_version_id: int | None = None, known_limitations: str = "",
) -> dict[str, Any]:
    """Turn a completed (or insufficient-data) run into ``ModelRegistryEntry``
    fields — the caller persists them. Mirrors
    ``app.services.ml.training_pipeline.build_registry_payload`` but for a
    run that actually executed training."""
    trained = run["training_status"] == "trained"
    return {
        "model_id": model_id,
        "model_version": model_version,
        "model_type": model_type,
        "dataset_version": dataset_version,
        "dataset_version_id": dataset_version_id,
        "training_date": run.get("trained_at", "") if trained else "",
        "training_status": run["training_status"],
        "architecture": run.get("architecture", "") if trained else "",
        "framework": run.get("framework", "") if trained else "",
        "hyperparameters": json.dumps(run.get("hyperparameters", {})),
        "git_commit": run.get("git_commit", ""),
        "training_metrics": json.dumps(run.get("training_metrics") or {}),
        "evaluation_metrics": json.dumps(run.get("evaluation_metrics") or run.get("validation_metrics") or {}),
        "known_limitations": known_limitations or (
            "Foundation-scale baseline over a small, real image-feature set — not a "
            "clinically validated model. Untrained/insufficient-data scaffold entries "
            "carry no validated performance; shadow mode only."
            if not trained else
            "Small-sample, pure-Python logistic-regression baseline. No clinical validation "
            "performed; shadow mode only until a human validates real, larger-scale metrics."
        ),
        "approval_status": "experimental",
    }
