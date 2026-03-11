import io
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from PIL import Image, ImageStat


@dataclass
class InferenceConfig:
    model_path: str | None = None
    model_name: str = "lumenai-baseline"
    model_version: str = "0.2.0"


class LumenAIModel:
    """
    Structured inference pipeline for LumenAI.

    Current behavior:
    - deterministic fallback classifier based on image statistics
    - stable output schema for API/worker consumers
    - explicit hooks for future trained-model integration

    Future behavior:
    - load real model from model_path
    - replace _predict_with_fallback with real inference backend
    """

    def __init__(
        self,
        model_path: str | None = None,
        model_name: str = "lumenai-baseline",
        model_version: str = "0.2.0",
    ):
        self.config = InferenceConfig(
            model_path=model_path or os.getenv("LUMENAI_MODEL_PATH"),
            model_name=model_name,
            model_version=model_version,
        )
        self._model: Any = None
        self._load_model()

    def _load_model(self) -> None:
        """
        Placeholder model loader.
        Keeps structure ready for Torch/ONNX/TensorFlow integration later.
        """
        if self.config.model_path and os.path.exists(self.config.model_path):
            # Future:
            # self._model = load_your_model(self.config.model_path)
            self._model = "configured-model-placeholder"
        else:
            self._model = None

    def _preprocess(self, image_bytes: bytes) -> Image.Image:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return image

    def _predict_with_fallback(self, image: Image.Image) -> dict[str, Any]:
        """
        Deterministic fallback classifier based on image statistics.

        This is intentionally simple but stable:
        - brightness drives confidence
        - low channel variance leans metallic/stainless
        - higher variance leans polymer/mixed surface
        """
        stat = ImageStat.Stat(image)
        mean_rgb = stat.mean[:3]
        std_rgb = stat.stddev[:3]

        brightness = sum(mean_rgb) / 3.0
        variance_score = sum(std_rgb) / 3.0

        # Normalize to 0..1 range
        brightness_norm = max(0.0, min(1.0, brightness / 255.0))
        variance_norm = max(0.0, min(1.0, variance_score / 128.0))

        # Deterministic confidence formula
        confidence = round((0.65 * brightness_norm) + (0.35 * (1.0 - variance_norm)), 2)

        # Deterministic material heuristic
        material_type = "stainless_steel" if variance_norm < 0.32 else "polymer"

        # Deterministic stain heuristic
        stain_detected = confidence >= 0.58

        return {
            "stain_detected": stain_detected,
            "confidence": confidence,
            "material_type": material_type,
        }

    def _predict(self, image: Image.Image) -> dict[str, Any]:
        """
        Uses real model if available; otherwise uses deterministic fallback.
        """
        if self._model is not None:
            # Future real inference path goes here.
            # Keep output schema identical.
            return self._predict_with_fallback(image)

        return self._predict_with_fallback(image)

    def _postprocess(self, prediction: dict[str, Any]) -> dict[str, Any]:
        return {
            "stain_detected": bool(prediction.get("stain_detected", False)),
            "confidence": float(prediction.get("confidence", 0.0)),
            "material_type": str(prediction.get("material_type", "unknown")),
            "model_name": self.config.model_name,
            "model_version": self.config.model_version,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        image = self._preprocess(image_bytes)
        prediction = self._predict(image)
        return self._postprocess(prediction)
