"""Safe, deterministic image decoding for the research pipeline.

Decoding is defensive: bad/empty bytes raise ``InvalidImageError`` rather than
crashing the pipeline, and resizing is deterministic so feature extraction is
reproducible.
"""
from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError


class InvalidImageError(ValueError):
    """Image bytes were missing or could not be decoded."""


def decode_rgb(image_bytes: bytes | None, *, size: tuple[int, int] = (98, 98)) -> Image.Image:
    """Decode ``image_bytes`` to a deterministic, fixed-size RGB image.

    Raises ``InvalidImageError`` for ``None``, empty, or undecodable input.
    """
    if not image_bytes:
        raise InvalidImageError("No image bytes provided.")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError(f"Could not decode image bytes: {exc}") from exc
    # Deterministic resize (BILINEAR) so embeddings are reproducible.
    return img.resize(size, Image.BILINEAR)
