"""Project Lens — Sections 15/16/19: the real live inference adapter.

Loads only a real, checksummed, sufficiently-promoted ``ModelRegistryEntry``
artifact; decodes actual uploaded image bytes; applies the exact registered
preprocessing contract, calibration, and abstention thresholds; returns the
Section 19 result contract. Never derives a prediction from an image hash,
never uses a deterministic seeded placeholder, never scores an unsupported
category, never invents a baseline similarity.

When no eligible model is available, or no real image bytes exist for this
submission, returns a safe, honestly-labeled unavailable state (Section 16)
— it never silently falls back to the deterministic placeholder
(``app.services.baseline_comparison_scoring_service``/``app.ai.inference``)
to manufacture a result.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import QUALITY_POOR, QUALITY_REJECT
from app.models.model_registry import ModelRegistryEntry
from app.services.ml.candidate_promotion import CANDIDATE_STAGES
from app.services.ml.image_quality import assess_image_bytes
from app.services.ml.lens_calibration import apply_temperature
from app.services.ml.lens_training_pipeline import NEGATIVE_LABEL, PREPROCESSING_VERSION, predict_hierarchical_from_weights
from app.services.ml.lens_model_registration import MODEL_ID
from app.services.ml.training_execution import _feature_vector
from app.services.observation_taxonomy import display_label

# Section 16 — the complete set of safe model-health outcomes.
HEALTH_AVAILABLE = "available"
HEALTH_UNAVAILABLE = "unavailable"
HEALTH_ARTIFACT_MISSING = "artifact_missing"
HEALTH_CHECKSUM_FAILED = "checksum_failed"
HEALTH_INCOMPATIBLE_PREPROCESSING = "incompatible_preprocessing"
HEALTH_INCOMPATIBLE_LABEL_MAP = "incompatible_label_map"
HEALTH_NOT_PROMOTED = "not_promoted"
HEALTH_INITIALIZATION_FAILED = "initialization_failed"

# A model must be promoted at least this far up the (Experimental ->
# Candidate -> Validated Candidate -> Pilot -> Production) ladder before the
# live adapter will use it for a real inference. Every model this sprint
# registers stays "Experimental" (see FIRST_MODEL_SCOPE.md) — so, by
# design, this adapter reports HEALTH_NOT_PROMOTED for every model produced
# by this sprint's declared experimental run. That is the correct, honest
# outcome: nothing here is presented as live-quality until real governed
# clinical Ground Truth trains a model that clears this bar.
MIN_STAGE_FOR_LIVE_SERVING = "Candidate"


def _stage_rank(stage: str) -> int:
    return CANDIDATE_STAGES.index(stage) if stage in CANDIDATE_STAGES else -1


def load_active_model(db: Session, *, tenant_id: str, model_id: str = MODEL_ID) -> dict[str, Any]:
    """Returns ``{"status": <health state>, "reason": str, "model": entry|None,
    "artifact": payload|None}``. Only ever returns ``status="available"``
    when a real artifact file exists on disk, its checksum matches the
    registry row, and its preprocessing version matches what this adapter
    implements."""
    candidates = (
        db.query(ModelRegistryEntry)
        .filter(
            ModelRegistryEntry.tenant_id == tenant_id,
            ModelRegistryEntry.model_id == model_id,
            ModelRegistryEntry.training_status == "trained",
        )
        .order_by(ModelRegistryEntry.id.desc())
        .all()
    )
    if not candidates:
        return {"status": HEALTH_UNAVAILABLE, "reason": "No trained model is registered for this tenant.", "model": None, "artifact": None}

    best = max(candidates, key=lambda m: (_stage_rank(m.candidate_stage), m.id))
    if _stage_rank(best.candidate_stage) < _stage_rank(MIN_STAGE_FOR_LIVE_SERVING):
        return {
            "status": HEALTH_NOT_PROMOTED, "model": best, "artifact": None,
            "reason": (
                f"The most advanced registered model (id={best.id}) is at stage "
                f"'{best.candidate_stage}', below the minimum '{MIN_STAGE_FOR_LIVE_SERVING}' "
                "required for live inference."
            ),
        }

    if not best.artifact_path or not os.path.exists(best.artifact_path):
        return {"status": HEALTH_ARTIFACT_MISSING, "model": best, "artifact": None,
                "reason": f"Artifact file not found at '{best.artifact_path}'."}

    with open(best.artifact_path, "rb") as f:
        raw = f.read()
    checksum = hashlib.sha256(raw).hexdigest()
    if checksum != best.artifact_checksum:
        return {"status": HEALTH_CHECKSUM_FAILED, "model": best, "artifact": None,
                "reason": "Artifact file checksum does not match the registered checksum."}

    if best.preprocessing_version != PREPROCESSING_VERSION:
        return {"status": HEALTH_INCOMPATIBLE_PREPROCESSING, "model": best, "artifact": None,
                "reason": f"Artifact preprocessing version '{best.preprocessing_version}' is not "
                          f"compatible with this adapter's '{PREPROCESSING_VERSION}'."}

    try:
        artifact = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"status": HEALTH_INITIALIZATION_FAILED, "model": best, "artifact": None,
                "reason": "Artifact file could not be parsed."}

    if not isinstance(artifact.get("eligible_classes"), list):
        return {"status": HEALTH_INCOMPATIBLE_LABEL_MAP, "model": best, "artifact": None,
                "reason": "Artifact label map is missing or malformed."}

    return {"status": HEALTH_AVAILABLE, "model": best, "artifact": artifact, "reason": ""}


def _limitations() -> list[str]:
    return [
        "This is a probable visual observation.",
        "Material identity has not been laboratory confirmed.",
        "Human action remains governed by organization policy.",
    ]


def _unavailable_contract(health: str, reason: str, *, model_id: str = MODEL_ID) -> dict[str, Any]:
    return {
        "analysis_status": "ai_unavailable",
        "model": {"model_id": model_id, "model_version": None, "status": health, "preprocessing_version": None, "calibration_version": None},
        "image_quality": None,
        "observation": None,
        "supported_categories": [],
        "unsupported_categories": [],
        "baseline_comparison": None,
        "limitations": _limitations() + [f"AI analysis is unavailable: {reason}"],
        "human_review_required": True,
        "inference_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def predict(
    db: Session, *, tenant_id: str, image_bytes: bytes | None, instrument_family: str = "", model_id: str = MODEL_ID,
) -> dict[str, Any]:
    """The real live inference entry point. Never uses the deterministic
    placeholder; returns a safe unavailable contract instead when no
    eligible model or no real image bytes exist for this request."""
    loaded = load_active_model(db, tenant_id=tenant_id, model_id=model_id)
    if loaded["status"] != HEALTH_AVAILABLE:
        return _unavailable_contract(loaded["status"], loaded["reason"], model_id=model_id)

    model, artifact = loaded["model"], loaded["artifact"]
    supported_categories = list(artifact["eligible_classes"])
    if artifact.get("has_negative_class"):
        supported_categories.append(NEGATIVE_LABEL)
    unsupported_categories = list(artifact.get("not_evaluated_classes") or [])

    if image_bytes is None:
        contract = _unavailable_contract(
            HEALTH_UNAVAILABLE,
            "No real image bytes were retained for this submission (retention/consent not enabled) — "
            "a trained model cannot evaluate real pixel content for this request.",
            model_id=model_id,
        )
        contract["model"]["model_version"] = model.model_version
        contract["model"]["status"] = "candidate"
        contract["supported_categories"] = supported_categories
        contract["unsupported_categories"] = unsupported_categories
        return contract

    quality = assess_image_bytes(image_bytes)
    model_block = {
        "model_id": model.model_id, "model_version": model.model_version, "status": model.candidate_stage.lower(),
        "preprocessing_version": model.preprocessing_version, "calibration_version": model.training_run_id,
    }

    if not quality["decodable"] or quality["overall_quality"] in (QUALITY_REJECT, QUALITY_POOR):
        return {
            "analysis_status": "completed",
            "model": model_block,
            "image_quality": {"status": "insufficient_image_quality", "confidence": None, "grade": quality.get("overall_quality")},
            "observation": {
                "category": "insufficient_image_quality", "display_label": display_label("insufficient_image_quality"),
                "raw_probability": None, "calibrated_confidence": None, "abstained": True,
                "abstention_reason": "insufficient_image_quality",
            },
            "supported_categories": supported_categories,
            "unsupported_categories": unsupported_categories,
            "baseline_comparison": None,
            "limitations": _limitations(),
            "human_review_required": True,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    vec = _feature_vector(image_bytes)
    if vec is None:
        return {
            "analysis_status": "completed",
            "model": model_block,
            "image_quality": {"status": "insufficient_image_quality", "confidence": None, "grade": quality.get("overall_quality")},
            "observation": {
                "category": "insufficient_image_quality", "display_label": display_label("insufficient_image_quality"),
                "raw_probability": None, "calibrated_confidence": None, "abstained": True,
                "abstention_reason": "insufficient_image_quality",
            },
            "supported_categories": supported_categories,
            "unsupported_categories": unsupported_categories,
            "baseline_comparison": None,
            "limitations": _limitations(),
            "human_review_required": True,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    label, raw_probability = predict_hierarchical_from_weights(
        stage_b_weights=artifact.get("stage_b_weights"),
        stage_c_weights_by_class=artifact.get("stage_c_weights_by_class") or {},
        eligible_classes=artifact["eligible_classes"], feature_vector=vec,
    )

    temperature = artifact["calibration"]["temperature"]
    calibrated_confidence = round(apply_temperature(raw_probability, temperature), 4) if raw_probability else raw_probability
    threshold = artifact["calibration"]["abstention_threshold"]

    if label == "unknown_review_required":
        abstained, abstention_reason = True, "unknown_review_required"
    elif calibrated_confidence is not None and calibrated_confidence < threshold:
        abstained, abstention_reason = True, "confidence_below_threshold"
    else:
        abstained, abstention_reason = False, None

    return {
        "analysis_status": "completed",
        "model": model_block,
        "image_quality": {"status": "sufficient_for_evaluation", "confidence": None, "grade": quality.get("overall_quality")},
        "observation": {
            "category": label if not abstained else "unknown_review_required",
            "display_label": display_label(label) if not abstained else "Unknown finding — review required",
            "raw_probability": round(raw_probability, 4) if raw_probability is not None else None,
            "calibrated_confidence": calibrated_confidence,
            "abstained": abstained,
            "abstention_reason": abstention_reason,
        },
        "supported_categories": supported_categories,
        "unsupported_categories": unsupported_categories,
        "baseline_comparison": None,  # populated by the caller via image_similarity_service, kept separate per Section 17
        "limitations": _limitations(),
        "human_review_required": True,
        "inference_timestamp": datetime.now(timezone.utc).isoformat(),
    }
