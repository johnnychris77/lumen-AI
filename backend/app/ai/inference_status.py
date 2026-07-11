"""Runtime introspection for the inspection-scoring inference pipeline.

Whether an actual trained computer-vision model is being used for a given
deployment is not visible from the API surface today -- callers only ever see
a finished inspection result, whether it came from a real model or from the
SHA-256 deterministic placeholder documented in app.ai.inference and
app.services.baseline_comparison_scoring_service. get_inference_status()
answers that question directly, by checking at call time whether the
optional CV dependencies are importable and whether a model weights file is
actually present on disk -- not by trusting a static label.
"""
from __future__ import annotations

import os


def get_inference_status() -> dict:
    """Return the current, live inference-mode status.

    Fields:
      mode                   -- "trained_model" when a YOLO model file exists
                                 at the resolved model path and the
                                 ``ultralytics`` package is importable, else
                                 "deterministic_placeholder".
      model_path              -- the resolved model path (LUMENAI_MODEL_PATH
                                 env var, or the "models/lumenai_model.pt"
                                 default used by app.ai.inference.LumenAIModel).
      onnx_available          -- whether the ``onnxruntime`` package can be
                                 imported in this environment.
      yolo_available           -- whether the ``ultralytics`` package can be
                                 imported in this environment.
      model_weights_present   -- whether a file exists at model_path.
      ready_for_production     -- True only when mode == "trained_model" AND
                                 model_weights_present is True.
    """
    model_path = os.getenv("LUMENAI_MODEL_PATH", "").strip() or "models/lumenai_model.pt"
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

    mode = (
        "trained_model"
        if (yolo_available and model_weights_present)
        else "deterministic_placeholder"
    )

    return {
        "mode": mode,
        "model_path": model_path,
        "onnx_available": onnx_available,
        "yolo_available": yolo_available,
        "model_weights_present": model_weights_present,
        "ready_for_production": mode == "trained_model" and model_weights_present,
    }
