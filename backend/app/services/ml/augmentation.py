"""Genesis — Section 3: real, deterministic image augmentation.

Every transform here operates on real pixel data (Pillow) and is seeded so
the exact same input + seed always produces the exact same augmented
output — required for the reproducibility this program demands. No
augmentation here fabricates a finding that isn't present (e.g. no synthetic
defect painting) — only geometric/photometric transforms of the real image.
"""
from __future__ import annotations

import hashlib
import io

from PIL import Image, ImageEnhance

SUPPORTED_AUGMENTATIONS = ("horizontal_flip", "brightness_jitter")


def _seeded_unit_interval(seed: str, sample_id: str, step: str) -> float:
    """Deterministic pseudo-random value in [0, 1) for one (seed, sample,
    step) combination — same approach as the rest of this codebase's
    deterministic scoring (SHA-256-derived, not Python's random module, so
    it is stable across processes/platforms)."""
    digest = hashlib.sha256(f"{seed}:{sample_id}:{step}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def augment_image_bytes(
    data: bytes, *, sample_id: str, seed: str, augmentations: tuple[str, ...] = SUPPORTED_AUGMENTATIONS,
) -> bytes:
    """Apply the configured augmentations to one image, deterministically.

    Unknown augmentation names are ignored rather than raising — this
    function is defensive against a config listing an augmentation this
    pure-Python pipeline doesn't (yet) implement, rather than crashing
    training over a documentation/config mismatch.
    """
    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")

        if "horizontal_flip" in augmentations:
            if _seeded_unit_interval(seed, sample_id, "flip") >= 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)

        if "brightness_jitter" in augmentations:
            # +/- 20% brightness, deterministic per sample.
            factor = 0.8 + 0.4 * _seeded_unit_interval(seed, sample_id, "brightness")
            img = ImageEnhance.Brightness(img).enhance(factor)

        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
