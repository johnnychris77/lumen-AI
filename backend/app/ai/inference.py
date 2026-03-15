import io
import os
import json
import hashlib
from datetime import datetime, timezone

from PIL import Image
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


class LumenAIModel:
    _shared_model = None
    _shared_model_path = None
    _shared_label_map = None
    _shared_label_map_path = None

    def __init__(self, model_path=None, model_name="lumenai-vision", model_version="0.4.0"):
        env_model_path = os.getenv("LUMENAI_MODEL_PATH", "").strip()
        env_label_map = os.getenv("LUMENAI_LABEL_MAP", "").strip()

        self.model_path = model_path or env_model_path or "models/lumenai_model.pt"
        self.label_map_path = env_label_map or "backend/config/label_map.example.json"
        self.model_name = model_name
        self.model_version = model_version
        self.model = self._load_model()
        self.label_map = self._load_label_map()

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

        risk_score = calculate_risk(detected_issue, confidence)
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
            "risk_score": risk_score,
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
                "inference_mode": "trained-yolo",
            }

        best_idx = int(boxes.conf.argmax().item())
        confidence = round(float(boxes.conf[best_idx].item()), 2)
        class_id = int(boxes.cls[best_idx].item()) if boxes.cls is not None else -1
        names = getattr(result, "names", {}) or {}
        detected_label = names.get(class_id, f"class_{class_id}")

        mapped = self._map_label(detected_label)
        detected_issue = mapped["detected_issue"]
        instrument_type = mapped["instrument_type"]
        material_type = mapped["material_type"]

        stain_detected = str(detected_issue).lower() not in {"clean", "ok", "normal"}

        risk_score = calculate_risk(detected_issue, confidence)
        return {
            "stain_detected": stain_detected,
            "confidence": confidence,
            "material_type": material_type,
            "instrument_type": instrument_type,
            "detected_issue": detected_issue,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "inference_mode": "trained-yolo",
            "risk_score": risk_score,
        }

    def predict(self, image_bytes: bytes):
        Image.open(io.BytesIO(image_bytes)).convert("RGB")

        yolo_result = self._predict_with_yolo(image_bytes)
        if yolo_result is not None:
            return yolo_result

        return self._deterministic_fallback(image_bytes)
