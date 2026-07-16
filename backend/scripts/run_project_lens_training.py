"""
Project Lens — Training Command (Section 7's single documented command)

Runs the full, real, reproducible pipeline: (optionally) generate the one
declared experimental dataset -> compute training eligibility from real
Annotation-level ACTIVE Ground Truth -> leakage-safe hierarchical training
(Stage B/C) -> calibration -> error analysis -> artifact export -> Model
Registry registration -> Model Card generation. No hidden notebook-only
steps — every step below is a plain function call in this repository.

Usage:
    cd backend
    RETAIN_INSPECTION_IMAGES=true PYTHONPATH=. python scripts/run_project_lens_training.py

Environment variables:
    DATABASE_URL              — defaults to whatever app.db.session already resolves
    TENANT_ID                 — defaults to "default-tenant"
    MODEL_VERSION             — defaults to "0.1.0-experimental"
    GENERATE_EXPERIMENTAL     — "1" (default) to run the declared experimental
                                 generator first; "0" to train only against
                                 whatever real ACTIVE Ground Truth already
                                 exists for TENANT_ID
    SAMPLES_PER_CLASS         — experimental generator sample count (default 8)
    SEED / EPOCHS / LEARNING_RATE — training config knobs (TrainingConfig)

This script never fabricates a metric: an ``insufficient_data`` outcome is
printed and the model is still registered (honestly, as not trained) rather
than silently discarded.
"""
from __future__ import annotations

import json
import os

TENANT_ID = os.getenv("TENANT_ID", "default-tenant")
MODEL_VERSION = os.getenv("MODEL_VERSION", "0.1.0-experimental")
GENERATE_EXPERIMENTAL = os.getenv("GENERATE_EXPERIMENTAL", "1").strip() in {"1", "true", "yes"}
SAMPLES_PER_CLASS = int(os.getenv("SAMPLES_PER_CLASS", "8"))
SEED = int(os.getenv("SEED", "42"))
EPOCHS = int(os.getenv("EPOCHS", "500"))
LEARNING_RATE = float(os.getenv("LEARNING_RATE", "0.3"))


def main() -> None:
    from app.db.session import SessionLocal
    from app.services.ml.experimental_dataset_generator import generate_experimental_dataset
    from app.services.ml.lens_model_registration import register_lens_model
    from app.services.ml.lens_training_pipeline import run_lens_training
    from app.services.ml.training_config import TrainingConfig
    from app.services.ml.training_eligibility_service import compute_training_eligibility

    db = SessionLocal()
    dataset_version_id: int | None = None
    try:
        if GENERATE_EXPERIMENTAL:
            summary = generate_experimental_dataset(db, tenant_id=TENANT_ID, samples_per_class=SAMPLES_PER_CLASS)
            dataset_version_id = summary["dataset_version_id"]
            print("Experimental dataset generated:", json.dumps(summary, default=str, indent=2))

        eligibility = compute_training_eligibility(db, tenant_id=TENANT_ID)
        print("Eligibility report:")
        print(json.dumps({k: v for k, v in eligibility.items() if k != "samples"}, indent=2))

        config = TrainingConfig(seed=SEED, epochs=EPOCHS, learning_rate=LEARNING_RATE)
        run = run_lens_training(eligibility, config=config)
        print("Training status:", run.get("training_status"))
        if run.get("training_status") == "trained":
            print("Split counts:", run["split_counts"])
            print("Evaluation metrics (test split):")
            print(json.dumps(run.get("evaluation_metrics") or run.get("validation_metrics"), indent=2))
            print("Calibration:", json.dumps(run["calibration"], indent=2))
            print("Error analysis summary:", json.dumps(
                {k: v for k, v in (run.get("error_analysis") or {}).items() if k != "errors"}, indent=2,
            ))

        model = register_lens_model(
            db, tenant_id=TENANT_ID, run=run, model_version=MODEL_VERSION,
            dataset_version_id=dataset_version_id,
        )
        print(f"Registered ModelRegistryEntry id={model.id} candidate_stage={model.candidate_stage} "
              f"artifact_path={model.artifact_path!r} artifact_checksum={model.artifact_checksum[:12]}...")
    finally:
        db.close()


if __name__ == "__main__":
    main()
