"""Scientific image-annotation linkage (Stage 5C).

Reuses the existing Project Canvas annotation model (``Annotation`` /
``AnnotationVersion``) — it introduces NO second annotation database and NO new
clinical taxonomy. It verifies that a pixel mask or bounding region matches its
original image's dimensions/orientation/coordinate space and annotation version,
and — crucially — preserves an INDETERMINATE relationship when laboratory evidence
cannot be reliably connected to a visible region.
"""
from __future__ import annotations

from research.lens_vision.artifact_store import MalformedMaskError, validate_mask
from research.lens_vision.scientific_evidence import REL_INDETERMINATE, REL_SUPPORTED


class AnnotationAlignmentError(ValueError):
    """A spatial annotation does not align with its image dimensions/version."""


def verify_mask_alignment(mask, *, image_width: int, image_height: int, annotation_version: int | None) -> dict:
    """Verify a pixel mask matches the image dimensions and carries a version.
    Raises ``AnnotationAlignmentError`` on mismatch/malformation."""
    try:
        validate_mask(mask, width=image_width, height=image_height)
    except MalformedMaskError as exc:
        raise AnnotationAlignmentError(str(exc)) from exc
    if annotation_version is None or not isinstance(annotation_version, int) or annotation_version < 1:
        raise AnnotationAlignmentError("Annotation must carry a positive integer version.")
    return {"aligned": True, "image_width": image_width, "image_height": image_height,
            "annotation_version": annotation_version}


def verify_bbox(bbox: dict, *, image_width: int, image_height: int) -> dict:
    """Verify a bounding region lies within image bounds (absolute pixel coords).
    Raises on an out-of-bounds or inverted box."""
    x, y, w, h = (bbox.get(k) for k in ("x", "y", "width", "height"))
    if None in (x, y, w, h):
        raise AnnotationAlignmentError("Bounding region missing x/y/width/height.")
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > image_width or y + h > image_height:
        raise AnnotationAlignmentError("Bounding region is inverted or outside the image bounds.")
    return {"x": x, "y": y, "width": w, "height": h, "within_bounds": True}


def _mask_iou(a, b) -> float:
    inter = ua = ub = 0
    for ra, rb in zip(a, b):
        for va, vb in zip(ra, rb):
            va, vb = int(bool(va)), int(bool(vb))
            ua += va
            ub += vb
            if va and vb:
                inter += 1
    union = ua + ub - inter
    return inter / union if union else 0.0


def relate_region_to_reference(
    predicted_mask, reference_mask, *, image_width: int, image_height: int, iou_threshold: float = 0.1,
) -> str:
    """Relationship between an AI/region mask and a VERIFIED reference (lab) mask.

    Returns ``supported_by_reviewer`` only when both masks are valid and overlap at
    or above ``iou_threshold``; otherwise ``indeterminate``. When no reference mask
    exists, the relationship is INDETERMINATE — never assumed.
    """
    if reference_mask is None or predicted_mask is None:
        return REL_INDETERMINATE
    try:
        validate_mask(predicted_mask, width=image_width, height=image_height)
        validate_mask(reference_mask, width=image_width, height=image_height)
    except MalformedMaskError:
        return REL_INDETERMINATE
    return REL_SUPPORTED if _mask_iou(predicted_mask, reference_mask) >= iou_threshold else REL_INDETERMINATE
