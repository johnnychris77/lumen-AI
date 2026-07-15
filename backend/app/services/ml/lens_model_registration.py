"""Project Lens — Sections 11-13: model export, registry, and card
generation, the one documented orchestration step tying the eligibility
report + training run together into a real, persisted
``ModelRegistryEntry``.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.model_registry import ModelRegistryEntry
from app.services.ml.lens_training_pipeline import export_artifact
from app.services.ml.model_card import generate_model_card

MODEL_ID = "lumenai-vision-lens"
MODEL_TYPE = "lens_hierarchical_observation_classifier"


def register_lens_model(
    db: Session, *, tenant_id: str, run: dict, model_version: str, dataset_version_id: int | None = None,
    artifact_dir: str | None = None,
) -> ModelRegistryEntry:
    """Persists one training run as a real ``ModelRegistryEntry``.

    ``candidate_stage`` is never set to "Candidate" for a run whose
    ``data_provenance`` is "synthetic_experimental" — per
    ``FIRST_MODEL_SCOPE.md``'s explicit commitment, a model trained on this
    sprint's one declared experimental run stays "Experimental" throughout,
    regardless of how well it trained. Only a run over real, governed
    clinical Ground Truth (``data_provenance == "real"``) is eligible for
    "Candidate", and even then only once genuinely trained (never for an
    ``insufficient_data`` run).
    """
    artifact_path, checksum = export_artifact(
        run, model_id=MODEL_ID, model_version=model_version, artifact_dir=artifact_dir,
    )
    trained = run.get("training_status") == "trained"
    is_real_data = run.get("data_provenance") == "real"
    candidate_stage = "Candidate" if (trained and is_real_data) else "Experimental"

    row = ModelRegistryEntry(
        tenant_id=tenant_id,
        model_id=MODEL_ID,
        model_version=model_version,
        model_type=MODEL_TYPE,
        dataset_version=str(dataset_version_id or ""),
        dataset_version_id=dataset_version_id,
        training_date=run.get("trained_at", ""),
        training_status=run.get("training_status", "not_started"),
        architecture="hierarchical_logistic_regression_one_vs_rest_pure_python",
        framework="pure_python_baseline",
        hyperparameters=json.dumps(run.get("config") or {}),
        git_commit=run.get("git_commit", ""),
        training_metrics=json.dumps(run.get("training_metrics") or {}),
        evaluation_metrics=json.dumps(run.get("evaluation_metrics") or run.get("validation_metrics") or {}),
        calibration_report=json.dumps(run.get("calibration") or {}),
        error_analysis_report=json.dumps(run.get("error_analysis") or {}),
        artifact_path=artifact_path,
        artifact_checksum=checksum,
        preprocessing_version=run.get("preprocessing_version", ""),
        training_run_id=run.get("config_hash", ""),
        candidate_stage=candidate_stage,
        known_limitations=(
            (
                "Trained exclusively on this sprint's one declared EXPERIMENTAL run — "
                "synthetic images pushed through the real governed review/Ground-Truth "
                "pipeline, never real clinical images. Never presented as, or promoted "
                "toward, a real clinical candidate. "
            ) if not is_real_data else ""
        ) + (
            "Hierarchical Stage B (abnormality)/Stage C (category) one-vs-rest "
            "logistic-regression baseline over Pillow-computed image features "
            "(brightness/sharpness/aspect ratio) — a foundation-scale linear "
            "classifier, not a trained convolutional/vision-transformer model. "
            f"Categories reported as not-evaluated: {run.get('not_evaluated_classes', [])}."
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
