"""Runtime introspection for the inspection-scoring inference pipeline.

Whether an actual trained computer-vision model is being used for a given
deployment is not visible from the API surface -- callers only ever see a
finished inspection result. get_inference_status() answers that question
directly, by checking at call time whether the optional CV dependencies are
importable, whether a model weights file is present on disk, and (P4.7.1)
whether that file passes SHA-256 pin verification -- not by trusting a static
label, and not by treating file PRESENCE as proof of a model.
"""
from __future__ import annotations

import os


def get_inference_status() -> dict:
    """Return the current, live inference-mode status.

    Fields:
      mode                   -- "trained_model" only when the ``ultralytics``
                                 package is importable AND the weights file
                                 passes SHA-256 pin verification;
                                 "deterministic_placeholder" when no verified
                                 model exists and the dev/test SIMULATION is
                                 explicitly permitted; otherwise "unavailable"
                                 (nothing is evaluated, nothing is fabricated).
      model_path              -- the resolved model path (LUMENAI_MODEL_PATH
                                 env var, or the "models/lumenai_model.pt"
                                 default used by app.ai.inference.LumenAIModel).
      onnx_available          -- whether ``onnxruntime`` can be imported.
      yolo_available          -- whether ``ultralytics`` can be imported.
      model_weights_present   -- whether a file exists at model_path.
      weights_verified        -- whether that file matches LUMENAI_MODEL_SHA256.
      integrity_reason        -- why verification failed ("" when verified).
      simulation_permitted    -- whether the dev/test simulation gate is open.
      ready_for_production    -- True only when mode == "trained_model" AND the
                                 weights are present and verified. This is a
                                 TECHNICAL loader state, not a validation or
                                 release approval (see governance_note).
    """
    from app.ai.inference import resolve_model_path
    from app.ai.inference_gate import simulation_permitted
    from app.ai.local_inference_policy import LocalInferenceUnavailable, verify_local_weights

    model_path = resolve_model_path()
    model_weights_present = os.path.exists(model_path)

    try:
        from ultralytics import YOLO  # noqa: F401
        yolo_available = True
    except Exception:
        yolo_available = False

    try:
        import onnxruntime  # noqa: F401
        onnx_available = True
    except Exception:
        onnx_available = False

    weights_verified = False
    integrity_reason = ""
    try:
        verify_local_weights(model_path, os.getenv("LUMENAI_MODEL_SHA256", ""))
        weights_verified = True
    except LocalInferenceUnavailable as exc:
        integrity_reason = str(exc)

    sim = simulation_permitted()
    if yolo_available and weights_verified:
        mode = "trained_model"
    elif sim:
        mode = "deterministic_placeholder"
    else:
        mode = "unavailable"

    return {
        "mode": mode,
        "model_path": model_path,
        "onnx_available": onnx_available,
        "yolo_available": yolo_available,
        "model_weights_present": model_weights_present,
        "weights_verified": weights_verified,
        "integrity_reason": integrity_reason,
        "simulation_permitted": sim,
        "ready_for_production": mode == "trained_model" and model_weights_present and weights_verified,
        "governance_note": (
            "Technical loader state only. A verified artifact is not evidence of "
            "defect-detection performance and is not a release authorization."
        ),
    }
