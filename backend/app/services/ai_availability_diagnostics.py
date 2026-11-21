"""Issue #192 — explicit, reason-coded AI_UNAVAILABLE diagnostics.

Before this module every non-completed live-model outcome reached the
clinician as the same sentence, "No eligible trained vision model evaluated
this image", whether no model was registered, a model existed but was not
promoted, its artifact was missing or failed its checksum, the uploaded image
bytes were not available, or a model DID run and abstained. Those failure
modes need different owners and different fixes, so they get distinct codes.

This module only CLASSIFIES the live inference adapter's own contract. It
never changes whether AI is available, never produces a score, probability or
confidence, and never relaxes a gate: every code here still means "no AI
observation — qualified human inspection required".

Messages are written for the inspecting tenant's own operator/administrator.
They name no file path, registry row id, other tenant, hospital, patient or
image content — only the class of failure and who can act on it.
"""
from __future__ import annotations

from typing import Any

# ── reason codes ────────────────────────────────────────────────────────────
NO_MODEL_REGISTERED = "NO_MODEL_REGISTERED"
MODEL_NOT_PROMOTED = "MODEL_NOT_PROMOTED"
ARTIFACT_MISSING = "ARTIFACT_MISSING"
ARTIFACT_INTEGRITY_FAILED = "ARTIFACT_INTEGRITY_FAILED"
MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
NO_IMAGE_BYTES = "NO_IMAGE_BYTES"
ABSTAINED_INSUFFICIENT_IMAGE_QUALITY = "ABSTAINED_INSUFFICIENT_IMAGE_QUALITY"
ABSTAINED_LOW_CONFIDENCE = "ABSTAINED_LOW_CONFIDENCE"
ABSTAINED_UNKNOWN_REVIEW_REQUIRED = "ABSTAINED_UNKNOWN_REVIEW_REQUIRED"
UNKNOWN = "UNKNOWN"

ALL_REASON_CODES = (
    NO_MODEL_REGISTERED, MODEL_NOT_PROMOTED, ARTIFACT_MISSING, ARTIFACT_INTEGRITY_FAILED,
    MODEL_LOAD_FAILED, NO_IMAGE_BYTES, ABSTAINED_INSUFFICIENT_IMAGE_QUALITY,
    ABSTAINED_LOW_CONFIDENCE, ABSTAINED_UNKNOWN_REVIEW_REQUIRED, UNKNOWN,
)

# Adapter health state -> reason code (app.services.ml.live_inference_adapter).
_HEALTH_TO_CODE = {
    "not_promoted": MODEL_NOT_PROMOTED,
    "artifact_missing": ARTIFACT_MISSING,
    "checksum_failed": ARTIFACT_INTEGRITY_FAILED,
    "incompatible_preprocessing": MODEL_LOAD_FAILED,
    "incompatible_label_map": MODEL_LOAD_FAILED,
    "initialization_failed": MODEL_LOAD_FAILED,
}

_ABSTENTION_TO_CODE = {
    "insufficient_image_quality": ABSTAINED_INSUFFICIENT_IMAGE_QUALITY,
    "confidence_below_threshold": ABSTAINED_LOW_CONFIDENCE,
    "unknown_review_required": ABSTAINED_UNKNOWN_REVIEW_REQUIRED,
}

# code -> (category, clinician/operator message, administrator action)
_TEXT: dict[str, tuple[str, str, str]] = {
    NO_MODEL_REGISTERED: (
        "model",
        "No trained vision model is registered for this organization, so no image was evaluated by AI.",
        "No validated model exists for this deployment. Model development, validation and clinical "
        "governance must be completed before AI inspection can be enabled.",
    ),
    MODEL_NOT_PROMOTED: (
        "model",
        "A trained model exists but has not been promoted for live use, so no image was evaluated by AI.",
        "The registered model is below the minimum promotion stage for live inference (for example, an "
        "experimental model trained on synthetic data). Promotion requires real-data validation and "
        "governance approval.",
    ),
    ARTIFACT_MISSING: (
        "model",
        "The promoted model could not be loaded, so no image was evaluated by AI.",
        "The registered model artifact is not present on this server. Check that the model artifact "
        "storage is persistent across deploys.",
    ),
    ARTIFACT_INTEGRITY_FAILED: (
        "model",
        "The promoted model failed its integrity check and was not used, so no image was evaluated by AI.",
        "The model artifact's checksum does not match its registry record. Treat as a possible "
        "tampering or corruption event; restore the registered artifact before re-enabling.",
    ),
    MODEL_LOAD_FAILED: (
        "model",
        "The promoted model could not be initialized, so no image was evaluated by AI.",
        "The model artifact is incompatible with this server's preprocessing or label map, or could "
        "not be parsed. Re-export the artifact for this release.",
    ),
    NO_IMAGE_BYTES: (
        "image",
        "An eligible model exists, but the uploaded image was not available to it, so no image was "
        "evaluated by AI.",
        "Image bytes were not retained or could not be verified for this submission (retention, "
        "consent or image-hash mismatch). Re-upload with image consent if policy allows.",
    ),
    ABSTAINED_INSUFFICIENT_IMAGE_QUALITY: (
        "abstention",
        "The model abstained because the image quality was insufficient, so no AI observation is reported.",
        "Recapture the image with adequate focus, lighting and framing.",
    ),
    ABSTAINED_LOW_CONFIDENCE: (
        "abstention",
        "The model abstained because its confidence was below the calibrated threshold, so no AI "
        "observation is reported.",
        "Expected behavior for uncertain images; manual inspection decides.",
    ),
    ABSTAINED_UNKNOWN_REVIEW_REQUIRED: (
        "abstention",
        "The model could not assign a supported category, so no AI observation is reported.",
        "Expected behavior for out-of-scope images; manual inspection decides.",
    ),
    UNKNOWN: (
        "model",
        "AI analysis did not produce an observation for this image.",
        "The AI outcome could not be classified; review server logs for this inspection.",
    ),
}


def classify_ai_unavailable(live_result: dict[str, Any] | None) -> dict[str, Any]:
    """Return ``{"code", "category", "message", "admin_action"}`` for a live
    adapter result that did NOT yield a usable AI observation.

    ``code`` is always one of :data:`ALL_REASON_CODES`. The function is pure:
    it reads only the adapter's contract and never touches the database.
    """
    live = live_result or {}
    model = live.get("model") or {}
    observation = live.get("observation") or {}
    explicit = live.get("unavailable_reason_code")

    if explicit in _TEXT:
        code = explicit
    elif live.get("analysis_status") == "completed" and observation.get("abstained"):
        code = _ABSTENTION_TO_CODE.get(observation.get("abstention_reason") or "", UNKNOWN)
    elif live.get("analysis_status") == "ai_unavailable":
        status = model.get("status") or ""
        if status in _HEALTH_TO_CODE:
            code = _HEALTH_TO_CODE[status]
        elif model.get("model_version"):
            # A served model with no evaluation => the bytes were missing.
            code = NO_IMAGE_BYTES
        elif status == "unavailable":
            code = NO_MODEL_REGISTERED
        else:
            code = UNKNOWN
    else:
        code = UNKNOWN

    category, message, admin_action = _TEXT[code]
    return {"code": code, "category": category, "message": message, "admin_action": admin_action}
