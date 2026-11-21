"""Legacy single-image inference (``/api/stream/frame``) — fail-closed (P4.7.1).

No trained model weights ship in this codebase. Before P4.7.1,
``LumenAIModel.predict()`` silently fell back to ``_deterministic_fallback()``
— a SHA-256-seeded pseudo-random result — in every environment, including
production, and stamped it with a real-looking model name and version.

The contract is now:

* **A model loads only after SHA-256 pin verification.** ``LUMENAI_MODEL_PATH``
  must point at a local file whose digest equals ``LUMENAI_MODEL_SHA256``
  (``app.ai.local_inference_policy.verify_local_weights``). A missing file,
  missing pin or mismatch means no model — nothing is downloaded.
* **No model ⇒ explicit ``ai_unavailable``.** No finding, confidence, risk
  score, instrument type or material is invented.
* **A loaded model that fails ⇒ explicit ``failed``.** A loading or execution
  error is never read as a clean instrument and never triggers the fallback.
* **The deterministic fallback is a dev/test simulation only**, gated by
  ``app.ai.inference_gate.simulation_permitted()`` and stamped
  ``simulated=True``.

A passing integrity check proves the bytes are the pinned bytes; it does not
show that the model detects defects.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from PIL import Image

from app.ai.inference_gate import (
    MODE_AI_UNAVAILABLE,
    MODE_INFERENCE_FAILED,
    MODE_SIMULATED,
    MODE_TRAINED,
    NOT_EVALUATED,
    STATUS_AI_UNAVAILABLE,
    STATUS_FAILED,
    simulation_permitted,
)
from app.ai.local_inference_policy import LocalInferenceUnavailable, verify_local_weights
from app.analytics.risk_engine import calculate_risk

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

logger = logging.getLogger(__name__)

# What this module does by default as shipped: with no pinned, verified model
# artifact it evaluates nothing. For a live, runtime-checked answer call
# app.ai.inference_status.get_inference_status().
PRODUCTION_INFERENCE_MODE = "unavailable"

# The finding categories a deployed model would cover ("clean" is an absence
# label, not a defect category, so it is excluded here). Any category outside
# this tuple must be reported as not evaluated / unsupported — never scored as
# if it had been checked. Single source of truth: other services (e.g.
# app.services.baseline_comparison_scoring_service) import this rather than
# redeclaring their own list.
SUPPORTED_MODEL_CATEGORIES = ("debris", "corrosion")

DEFAULT_MODEL_PATH = "models/lumenai_model.pt"

_LOAD_OK = "loaded"
_LOAD_UNAVAILABLE = "unavailable"
_LOAD_FAILED = "failed"


def resolve_model_path(model_path: str | None = None) -> str:
    return model_path or os.getenv("LUMENAI_MODEL_PATH", "").strip() or DEFAULT_MODEL_PATH


class LumenAIModel:
    _shared_model = None
    _shared_model_key: tuple[str, str] | None = None
    _shared_label_map = None
    _shared_label_map_path = None

    def __init__(self, model_path=None, model_name="lumenai-vision", model_version="0.4.0"):
        env_label_map = os.getenv("LUMENAI_LABEL_MAP", "").strip()

        self.model_path = resolve_model_path(model_path)
        self.label_map_path = env_label_map or "backend/config/label_map.example.json"
        self.model_name = model_name
        self.model_version = model_version
        self.load_state = _LOAD_UNAVAILABLE
        self.load_reason = "No approved model artifact is configured."
        self.model_integrity: dict[str, Any] = {"verified": False}
        self.model = self._load_model()
        self.label_map = self._load_label_map()

    # ── loading (integrity first, fail-closed) ────────────────────────────────

    def _load_model(self):
        if YOLO is None:
            self.load_reason = "The model runtime is not installed."
            return None

        # Verify the SHA-256 pin BEFORE the artifact is opened by the runtime.
        try:
            check = verify_local_weights(self.model_path, os.getenv("LUMENAI_MODEL_SHA256", ""))
        except LocalInferenceUnavailable as exc:
            self.load_reason = str(exc)
            return None

        key = (check["model_path"], check["sha256"])
        self.model_integrity = {"verified": True, "sha256": check["sha256"]}
        if LumenAIModel._shared_model is not None and LumenAIModel._shared_model_key == key:
            self.load_state = _LOAD_OK
            self.load_reason = ""
            return LumenAIModel._shared_model

        try:
            model = YOLO(self.model_path)
        except Exception as exc:
            # A verified artifact that will not load is a FAILURE, not "no model".
            logger.warning("Verified model artifact failed to load (%s)", type(exc).__name__)
            self.load_state = _LOAD_FAILED
            self.load_reason = "The verified model artifact could not be loaded."
            return None

        LumenAIModel._shared_model = model
        LumenAIModel._shared_model_key = key
        self.load_state = _LOAD_OK
        self.load_reason = ""
        return model

    def _load_label_map(self):
        if not os.path.exists(self.label_map_path):
            return {}

        if (
            LumenAIModel._shared_label_map is not None
            and LumenAIModel._shared_label_map_path == self.label_map_path
        ):
            return LumenAIModel._shared_label_map

        try:
            with open(self.label_map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            LumenAIModel._shared_label_map = data
            LumenAIModel._shared_label_map_path = self.label_map_path
            return data
        except Exception:
            return {}

    def _map_label(self, detected_label: str):
        mapped = self.label_map.get(detected_label, {})
        return {
            "instrument_type": mapped.get("instrument_type", "unknown"),
            "detected_issue": mapped.get("detected_issue", detected_label or "unknown"),
            "material_type": mapped.get("material_type", "unknown"),
        }

    # ── explicit non-detection results ────────────────────────────────────────

    def _not_evaluated(self, status: str, reason: str) -> dict[str, Any]:
        """Nothing was evaluated. Every value that could be read as a finding,
        a confidence or a risk is None / ``not_evaluated`` — never a default
        that looks clean."""
        return {
            "analysis_status": status,
            "stain_detected": None,
            "confidence": None,
            "material_type": "unknown",
            "instrument_type": "unknown",
            "detected_issue": NOT_EVALUATED,
            "model_name": "none",
            "model_version": "none",
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "inference_mode": MODE_INFERENCE_FAILED if status == STATUS_FAILED else MODE_AI_UNAVAILABLE,
            "risk_score": None,
            "simulated": False,
            "human_review_required": True,
            "unavailable_reason": reason,
            "model_integrity": dict(self.model_integrity),
        }

    def _deterministic_fallback(self, image_bytes: bytes):
        """DEV/TEST SIMULATION ONLY — callers must check ``simulation_permitted()``.

        The output is derived from a hash of the bytes, not from the image
        content, and is stamped ``simulated=True``."""
        logger.info("INFERENCE MODE: simulated deterministic placeholder (dev/test only) — not a CV model")
        digest = hashlib.sha256(image_bytes).hexdigest()
        seed_value = int(digest[:8], 16)

        confidence = round(((seed_value % 51) + 40) / 100, 2)
        material_options = ["stainless_steel", "polymer", "titanium"]
        instrument_options = [
            "arthroscopy_shaver",
            "laparoscopic_grasper",
            "orthopedic_drill",
            "general_surgical_instrument",
        ]
        issue_options = ["stain", "debris", "clean", "corrosion"]

        material_type = material_options[seed_value % len(material_options)]
        instrument_type = instrument_options[seed_value % len(instrument_options)]
        detected_issue = issue_options[seed_value % len(issue_options)]
        stain_detected = detected_issue in {"stain", "debris", "corrosion"}

        risk_score = calculate_risk(detected_issue, confidence)
        return {
            "analysis_status": "simulated",
            "stain_detected": stain_detected,
            "confidence": confidence,
            "material_type": material_type,
            "instrument_type": instrument_type,
            "detected_issue": detected_issue,
            "model_name": "simulated-placeholder",
            "model_version": "simulation",
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "inference_mode": MODE_SIMULATED,
            "risk_score": risk_score,
            "simulated": True,
            "human_review_required": True,
            "model_integrity": {"verified": False, "reason": "simulation — no model artifact"},
        }

    # ── real model execution ──────────────────────────────────────────────────

    def _predict_with_yolo(self, image_bytes: bytes) -> dict[str, Any]:
        """Run the loaded, integrity-verified model. Raises on ANY failure —
        the caller converts that into an explicit ``failed`` result."""
        if cv2 is None or np is None:
            raise RuntimeError("image runtime (opencv / numpy) is not installed")

        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError("image could not be decoded for inference")

        results = self.model(image, verbose=False)
        if not results:
            raise RuntimeError("model returned no result object")

        result = results[0]
        boxes = getattr(result, "boxes", None)
        base = {
            "analysis_status": "completed",
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "inference_mode": MODE_TRAINED,
            "simulated": False,
            "human_review_required": True,
            "model_integrity": dict(self.model_integrity),
        }

        if boxes is None or len(boxes) == 0:
            # A real model ran and reported no detection. This is a model output
            # (not a default), and it still requires human review.
            return {
                **base,
                "stain_detected": False,
                "confidence": 0.0,
                "material_type": "unknown",
                "instrument_type": "unknown",
                "detected_issue": "clean",
                "risk_score": 0,
            }

        best_idx = int(boxes.conf.argmax().item())
        confidence = round(float(boxes.conf[best_idx].item()), 2)
        class_id = int(boxes.cls[best_idx].item()) if boxes.cls is not None else -1
        names = getattr(result, "names", {}) or {}
        detected_label = names.get(class_id, f"class_{class_id}")

        mapped = self._map_label(detected_label)
        detected_issue = mapped["detected_issue"]

        return {
            **base,
            "stain_detected": str(detected_issue).lower() not in {"clean", "ok", "normal"},
            "confidence": confidence,
            "material_type": mapped["material_type"],
            "instrument_type": mapped["instrument_type"],
            "detected_issue": detected_issue,
            "risk_score": calculate_risk(detected_issue, confidence),
        }

    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        # Reject bytes that are not an image at all (unchanged behaviour: raises).
        Image.open(io.BytesIO(image_bytes)).convert("RGB")

        if self.model is not None:
            try:
                return self._predict_with_yolo(image_bytes)
            except Exception as exc:
                # Never fall through to the simulation, never report "clean".
                logger.warning("Model execution failed (%s)", type(exc).__name__)
                return self._not_evaluated(STATUS_FAILED, "Model execution failed.")

        if self.load_state == _LOAD_FAILED:
            return self._not_evaluated(STATUS_FAILED, self.load_reason)

        if simulation_permitted():
            return self._deterministic_fallback(image_bytes)

        return self._not_evaluated(STATUS_AI_UNAVAILABLE, self.load_reason)
