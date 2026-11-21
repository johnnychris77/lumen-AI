"""R6: Real SSIM-based baseline comparison.

Uses scikit-image when installed. P4.7.1: when a real comparison is not
possible the result is an explicit ``backend="unavailable"`` — the deterministic
mock similarity survives only as an opted-in dev/test simulation and is never a
production fallback.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field


@dataclass
class SSIMResult:
    structural_similarity: float = 0.0
    match_pct: float = 0.0
    color_delta: float = 0.0
    diff_regions: list[tuple[float, float, float, float]] = field(default_factory=list)
    backend: str = "unavailable"   # "scikit-image" | "mock" (dev/test simulation) | "unavailable"


def _mock_ssim(url_a: str, url_b: str) -> SSIMResult:
    """Deterministic fallback — same URL pair always gives same result."""
    seed = int(hashlib.md5((url_a + url_b).encode()).hexdigest()[:8], 16)  # noqa: S324
    rng = random.Random(seed)
    same_host = url_a.split("/")[2] == url_b.split("/")[2] if "//" in url_a and "//" in url_b else False
    match = round(rng.uniform(85, 97) if same_host else rng.uniform(42, 78), 1)
    ssim = round(match / 100 * rng.uniform(0.95, 1.0), 3)
    delta = round(rng.uniform(1.5, 4.0) if match > 80 else rng.uniform(9.0, 22.0), 2)
    regions: list[tuple[float, float, float, float]] = []
    if match < 80:
        regions.append((
            round(rng.uniform(0.1, 0.5), 3),
            round(rng.uniform(0.1, 0.5), 3),
            round(rng.uniform(0.1, 0.35), 3),
            round(rng.uniform(0.1, 0.30), 3),
        ))
    return SSIMResult(structural_similarity=ssim, match_pct=match, color_delta=delta,
                      diff_regions=regions, backend="mock")


def _fetch_bytes(url: str) -> bytes | None:
    """P4.7.1 (SEC-R2-02): the only permitted route is the SSRF-safe,
    allow-listed fetcher. Returns None when the URL is prohibited, not
    allow-listed, or the fetch fails — never an unvalidated request."""
    from app.cv.safe_fetch import try_fetch_image_bytes

    return try_fetch_image_bytes(url)


def compare_image_bytes(raw_a: bytes, raw_b: bytes) -> SSIMResult | None:
    """REAL structural comparison of two decoded images.

    Returns ``None`` when a real comparison cannot be performed (scikit-image /
    numpy not installed, or an image cannot be decoded). It never substitutes a
    simulated similarity."""
    try:
        import io

        import numpy as np
        from PIL import Image
        from skimage.metrics import structural_similarity  # type: ignore[import-untyped]

        img_a = np.array(Image.open(io.BytesIO(raw_a)).convert("L").resize((512, 512)))
        img_b = np.array(Image.open(io.BytesIO(raw_b)).convert("L").resize((512, 512)))

        score, diff = structural_similarity(img_a, img_b, full=True)
        ssim = float(round(score, 4))
        match = round(ssim * 100, 1)

        # Colour delta — mean absolute diff in original colour space (approximated)
        img_a_rgb = np.array(Image.open(io.BytesIO(raw_a)).convert("RGB").resize((128, 128))).astype(float)
        img_b_rgb = np.array(Image.open(io.BytesIO(raw_b)).convert("RGB").resize((128, 128))).astype(float)
        color_delta = float(round(np.mean(np.abs(img_a_rgb - img_b_rgb)), 2))

        # Bounding boxes of high-difference regions from diff map
        diff_norm = (1.0 - diff)  # diff map: 0 = identical, 1 = totally different
        threshold = 0.35
        mask = (diff_norm > threshold).astype(np.uint8)
        regions: list[tuple[float, float, float, float]] = []
        try:
            from skimage import measure
            labels = measure.label(mask)
            for region in measure.regionprops(labels):
                r0, c0, r1, c1 = region.bbox
                h, w = img_a.shape
                regions.append((
                    round(c0 / w, 3), round(r0 / h, 3),
                    round((c1 - c0) / w, 3), round((r1 - r0) / h, 3),
                ))
        except Exception:
            pass

        return SSIMResult(structural_similarity=ssim, match_pct=match,
                          color_delta=color_delta, diff_regions=regions,
                          backend="scikit-image")
    except Exception:
        return None


def _unavailable() -> SSIMResult:
    return SSIMResult(structural_similarity=0.0, match_pct=0.0, color_delta=0.0, backend="unavailable")


def compare_images(url_a: str, url_b: str) -> SSIMResult:
    """Compare two images by structural similarity.

    A real comparison is used whenever both images can be obtained through the
    permitted route and scikit-image is installed. Otherwise the result is an
    explicit ``backend="unavailable"`` — except in an explicitly opted-in
    dev/test simulation, where the deterministic mock (``backend="mock"``) is
    returned for tests and demos. The mock is never a fallback in production.
    """
    from app.ai.inference_gate import simulation_permitted

    def _no_real_result() -> SSIMResult:
        return _mock_ssim(url_a, url_b) if simulation_permitted() else _unavailable()

    if not url_a or not url_b:
        if simulation_permitted():
            return SSIMResult(structural_similarity=0.0, match_pct=0.0, color_delta=99.0, backend="mock")
        return _unavailable()

    raw_a = _fetch_bytes(url_a)
    raw_b = _fetch_bytes(url_b)
    if raw_a is None or raw_b is None:
        return _no_real_result()

    real = compare_image_bytes(raw_a, raw_b)
    return real if real is not None else _no_real_result()
