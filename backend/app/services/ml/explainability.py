"""Genesis — Section 8: per-prediction explainability contract.

Every prediction this pipeline produces carries exactly the fields this
program requires — nothing more is asserted. In particular: no saliency
map, class-activation map, or other visual explanation is generated,
because no real trained vision model (with real gradients to visualize)
exists in this codebase — see ``app.ai.inference.SUPPORTED_MODEL_CATEGORIES``
and the Core Inspection Workflow Closure sprint. Fabricating a heatmap over
a logistic-regression-on-pixel-statistics model would misrepresent it as
something it is not. ``visual_explanation.available`` is honestly ``False``
until a real model with real gradients exists; when one does, any such
visualization must be labeled an explanatory aid, never proof of causation
(per this section's explicit instruction).
"""
from __future__ import annotations

from typing import Any

KNOWN_LIMITATIONS = (
    "Foundation-scale logistic-regression baseline over Pillow-computed image "
    "features (brightness, sharpness, aspect ratio) — not a trained "
    "computer-vision model. No causal or diagnostic claim is made. "
    "human_review_required is always true regardless of confidence."
)


def explain_prediction(
    *, predicted_class: str, confidence: float, model_version: str,
    image_quality: str, supported_classes: list[str],
) -> dict[str, Any]:
    """The required explainability record for one prediction (Section 8)."""
    return {
        "supported_class": predicted_class if predicted_class in supported_classes else None,
        "predicted_class": predicted_class,
        "confidence": confidence,
        "model_version": model_version,
        "image_quality": image_quality,
        "known_limitations": KNOWN_LIMITATIONS,
        "supported_classes": list(supported_classes),
        "human_review_required": True,
        "visual_explanation": {
            "available": False,
            "note": (
                "No saliency map / class-activation map is generated. This model has no "
                "real gradients to visualize; a fabricated heatmap would misrepresent it as "
                "a trained vision model. If a future model provides one, it must be labeled "
                "an explanatory aid, not proof of causation."
            ),
        },
    }
