"""Phase 17 §1 — Training pipeline foundation.

Orchestrates the repeatable path: image ingestion → label ingestion → dataset
split → (train/val/test sets) → model-artifact output → evaluation report →
registry entry. Training itself is a stub: with no labeled data yet, the pipeline
prepares and validates everything around training and records a `not_started`
registry entry rather than fabricating a trained model or metrics.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.services.ml.dataset_split import has_no_group_leakage, split_dataset
from app.services.ml.model_tasks import MODEL_TASKS, is_valid_task, task_labels


def dataset_version(samples: list[dict], seed: str) -> str:
    """Deterministic dataset fingerprint so a registry entry pins its exact data."""
    ids = sorted(str(s.get("id")) for s in samples)
    digest = hashlib.sha256((seed + "|" + ",".join(ids)).encode()).hexdigest()[:12]
    return f"ds-{len(samples)}-{digest}"


def prepare_training_run(
    task_key: str,
    samples: list[dict],
    *,
    seed: str = "lumenai-v1",
    group_by_serial: bool = False,
) -> dict[str, Any]:
    """Prepare (not execute) a training run: validate the task, split the data
    with leakage checks, and assemble the run manifest a real trainer would use.

    Honest: returns ``training_status: not_started`` and no metrics — there is no
    labeled dataset to train on yet. Everything *around* training is real.
    """
    if not is_valid_task(task_key):
        raise ValueError(f"Unknown model task '{task_key}'.")

    split = split_dataset(samples, seed=seed, group_by_serial=group_by_serial)
    leakage_free = has_no_group_leakage(split)
    dsv = dataset_version(samples, seed)

    return {
        "task": task_key,
        "task_name": MODEL_TASKS[task_key]["name"],
        "labels": task_labels(task_key),
        "safety_critical": MODEL_TASKS[task_key]["safety_critical"],
        "dataset_version": dsv,
        "split_counts": split["counts"],
        "split": split,
        "leakage_free": leakage_free,
        "training_status": "not_started",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "model_artifact": None,
        "evaluation_report": None,
        "note": (
            "Pipeline prepared and split validated. Training is not executed — no "
            "labeled dataset exists yet. No metrics are fabricated."
        ),
    }


def build_registry_payload(run: dict, model_id: str, model_version: str,
                           known_limitations: str = "") -> dict[str, Any]:
    """Turn a prepared run into the fields for a ModelRegistryEntry (experimental)."""
    return {
        "model_id": model_id,
        "model_version": model_version,
        "model_type": run["task"],
        "dataset_version": run["dataset_version"],
        "training_date": "",
        "training_status": run["training_status"],
        "evaluation_metrics": json.dumps({}),
        "known_limitations": known_limitations or (
            "Untrained scaffold entry — no validated performance. Experimental; "
            "shadow mode only until a human validates real metrics."
        ),
        "approval_status": "experimental",
    }
