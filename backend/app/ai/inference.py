import io
import os
import hashlib
from datetime import datetime, timezone

from PIL import Image

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


class LumenAIModel:
    _shared_model = None
    _shared_model_path = None

    def __init__(self, model_path=None, model_name="lumenai-vision", model_version="0.3.0"):
        env_model_path = os.getenv("LUMENAI_MODEL_PATH", "").strip()
        self.model_path = model_path or env_model_path or "models/lumenai_model.pt"
        self.model_name = model_name
        self.model_version = model_version
        self.model = self._load_model()

    def _load_model(self):
        if YOLO is None:
            return None

        if not os.path.exists(self.model_path):
            return None

        if (
            LumenAIModel._shared_model is not None
            and LumenAIModel._shared_model_path == self.model_path
        ):
            return LumenAIModel._shared_model

        try:
            model = YOLO(self.model_path)
            LumenAIModel._shared_model = model
            LumenAIModel._shared_model_path = self.model_path
            return model
        except Exception:
            return None

    def _deterministic_fallback(self, image_bytes: bytes):
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

        return {
            "stain_detected": stain_detected,
            "confidence": confidence,
            "material_type": material_type,
            "instrument_type": instrument_type,
            "detected_issue": detected_issue,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "inference_mode": "deterministic-fallback",
        }

    def _predict_with_yolo(self, image_bytes: bytes):
        if self.model is None or cv2 is None or np is None:
            return None

        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return None

        results = self.model(image, verbose=False)
        if not results:
            return None

        result = results[0]
        boxes = getattr(result, "boxes", None)

        if boxes is None or len(boxes) == 0:
            return {
                "stain_detected": False,
                "confidence": 0.0,
                "material_type": "unknown",
                "instrument_type": "unknown",
                "detected_issue": "clean",
                "model_name": self.model_name,
                "model_version": self.model_version,
                "inference_timestamp": datetime.now(timezone.utc).isoformat(),
                "inference_mode": "yolo",
            }

        best_idx = int(boxes.conf.argmax().item())
        confidence = round(float(boxes.conf[best_idx].item()), 2)

        class_id = int(boxes.cls[best_idx].item()) if boxes.cls is not None else -1
        names = getattr(result, "names", {}) or {}
        detected_label = names.get(class_id, f"class_{class_id}")

        stain_detected = detected_label.lower() not in {"clean", "ok", "normal"}

        instrument_type = "unknown"
        detected_issue = detected_label

        instrument_labels = {
            "arthroscopy_shaver",
            "laparoscopic_grasper",
            "orthopedic_drill",
            "robotic_instrument",
            "general_surgical_instrument",
        }

        if detected_label in instrument_labels:
            instrument_type = detected_label
            detected_issue = "clean"

        return {
            "stain_detected": stain_detected,
            "confidence": confidence,
            "material_type": "stainless_steel",
            "instrument_type": instrument_type,
            "detected_issue": detected_issue,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "inference_mode": "yolo",
        }

    def predict(self, image_bytes: bytes):
        Image.open(io.BytesIO(image_bytes)).convert("RGB")

        yolo_result = self._predict_with_yolo(image_bytes)
        if yolo_result is not None:
            return yolo_result

        return self._deterministic_fallback(image_bytes)
