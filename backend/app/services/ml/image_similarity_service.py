"""Project Lens — Section 18: honest, feature-based baseline comparator.

Confirmed via repo-wide trace (``LIVE_INFERENCE_TRACE.md`` Section 7): no
real image-comparison method (perceptual hash, SSIM, embedding cosine
similarity) exists anywhere in this codebase before this module — every
prior "similarity"/"match" number was SHA-256-seeded pseudo-random
arithmetic that never looked at pixels. This is a real, first-stage
perceptual-hash comparator: pure Python + Pillow only (no numpy/scipy), a
64-bit average hash (aHash) compared by Hamming distance. It distinguishes
the exact same image, a near-duplicate, and a clearly different image —
nothing more sophisticated is claimed.
"""
from __future__ import annotations

import hashlib
import io
from typing import Any

from PIL import Image

COMPARATOR_VERSION = "lens-average-hash-v1"
HASH_SIZE = 8  # 8x8 -> 64-bit hash

# Hamming-distance threshold (out of 64 bits) below which two images are
# reported "comparable" — a conservative, disclosed cutoff, not fit to any
# dataset (none exists to fit against yet).
_COMPARABLE_MAX_DISTANCE = 20      # ~69% bit agreement

STATUS_EXACT_MATCH = "exact_match"
STATUS_COMPARABLE = "comparable"
STATUS_MATERIALLY_DIFFERENT = "materially_different"
STATUS_INCOMPATIBLE_VIEW = "incompatible_view"
STATUS_INSUFFICIENT_QUALITY = "insufficient_quality"
STATUS_NO_APPROVED_BASELINE = "no_approved_baseline"


def compute_average_hash(image_bytes: bytes, *, hash_size: int = HASH_SIZE) -> str | None:
    """Real aHash: downscale to hash_size x hash_size, grayscale, threshold
    against the mean pixel value. Returns a hex string, or None if the
    bytes are not a decodable image."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            small = img.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
            pixels = list(small.getdata())
    except Exception:
        return None
    mean = sum(pixels) / len(pixels)
    bits = "".join("1" if p >= mean else "0" for p in pixels)
    return f"{int(bits, 2):0{(hash_size * hash_size + 3) // 4}x}"


def hamming_distance(hash_a: str, hash_b: str) -> int:
    a, b = int(hash_a, 16), int(hash_b, 16)
    return bin(a ^ b).count("1")


def similarity_from_distance(distance: int, *, total_bits: int = HASH_SIZE * HASH_SIZE) -> float:
    return round(1.0 - (distance / total_bits), 4)


def compare_image_bytes(image_a: bytes, image_b: bytes) -> dict[str, Any]:
    """Pixel-level comparison only — never checks instrument/anatomy
    compatibility (that is the caller's job, before this is even called;
    see ``compare_against_baseline`` below for the compatibility-first
    flow Section 18 requires)."""
    sha_a, sha_b = hashlib.sha256(image_a).hexdigest(), hashlib.sha256(image_b).hexdigest()
    if sha_a == sha_b:
        return {
            "status": STATUS_EXACT_MATCH, "similarity": 1.0, "hamming_distance": 0,
            "method": "sha256_exact", "comparator_version": COMPARATOR_VERSION,
        }

    hash_a, hash_b = compute_average_hash(image_a), compute_average_hash(image_b)
    if hash_a is None or hash_b is None:
        return {
            "status": STATUS_INSUFFICIENT_QUALITY, "similarity": None, "hamming_distance": None,
            "method": "average_hash_hamming", "comparator_version": COMPARATOR_VERSION,
            "reason": "One or both images could not be decoded for comparison.",
        }

    distance = hamming_distance(hash_a, hash_b)
    similarity = similarity_from_distance(distance)
    # Section 18's required vocabulary has no separate "near duplicate"
    # status — both a near-identical and a loosely-similar image are
    # "comparable"; only a distance beyond _COMPARABLE_MAX_DISTANCE is
    # reported as materially different.
    status = STATUS_COMPARABLE if distance <= _COMPARABLE_MAX_DISTANCE else STATUS_MATERIALLY_DIFFERENT
    return {
        "status": status, "similarity": similarity, "hamming_distance": distance,
        "method": "average_hash_hamming", "comparator_version": COMPARATOR_VERSION,
    }


def compare_against_baseline(
    *,
    image_bytes: bytes | None,
    baseline_image_bytes: bytes | None,
    candidate_instrument_family: str,
    baseline_instrument_family: str,
    candidate_manufacturer: str = "",
    baseline_manufacturer: str = "",
    baseline_available: bool,
    baseline_id: int | str | None = None,
    baseline_version: str | None = None,
) -> dict[str, Any]:
    """Section 18's full flow: validate compatibility FIRST, only then
    produce a numeric similarity. Never returns a similarity score for an
    incompatible or unavailable comparison."""
    if not baseline_available:
        return {
            "status": STATUS_NO_APPROVED_BASELINE, "similarity": None,
            "method": "average_hash_hamming", "comparator_version": COMPARATOR_VERSION,
            "baseline_id": baseline_id, "baseline_version": baseline_version,
        }

    if (
        candidate_instrument_family
        and baseline_instrument_family
        and candidate_instrument_family != baseline_instrument_family
    ) or (
        candidate_manufacturer and baseline_manufacturer and candidate_manufacturer != baseline_manufacturer
    ):
        return {
            "status": STATUS_INCOMPATIBLE_VIEW, "similarity": None,
            "method": "average_hash_hamming", "comparator_version": COMPARATOR_VERSION,
            "baseline_id": baseline_id, "baseline_version": baseline_version,
            "reason": "Candidate and baseline instrument family/manufacturer do not match.",
        }

    if image_bytes is None or baseline_image_bytes is None:
        return {
            "status": STATUS_INSUFFICIENT_QUALITY, "similarity": None,
            "method": "average_hash_hamming", "comparator_version": COMPARATOR_VERSION,
            "baseline_id": baseline_id, "baseline_version": baseline_version,
            "reason": "Real image bytes were not available for one or both images (retention/consent not enabled).",
        }

    result = compare_image_bytes(image_bytes, baseline_image_bytes)
    result["baseline_id"] = baseline_id
    result["baseline_version"] = baseline_version
    return result
