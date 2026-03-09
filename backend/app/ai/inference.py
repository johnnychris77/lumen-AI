import io
import random
from datetime import datetime, timezone

from PIL import Image


class LumenAIModel:
    def __init__(self, model_path=None, model_name="lumenai-baseline", model_version="0.1.0"):
        self.model_path = model_path
        self.model_name = model_name
        self.model_version = model_version

    def predict(self, image_bytes: bytes):
        Image.open(io.BytesIO(image_bytes)).convert("RGB")
        conf = round(random.random(), 2)

        return {
            "stain_detected": conf > 0.5,
            "confidence": conf,
            "material_type": "stainless_steel" if conf > 0.5 else "polymer",
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
        }
