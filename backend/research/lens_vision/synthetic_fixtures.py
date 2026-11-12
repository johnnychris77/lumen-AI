"""Controlled synthetic fixtures for CPU pipeline smoke tests.

These are deterministically-generated, class-distinguishable images with
``synthetic_experimental`` provenance. They exist ONLY to exercise and test the
research pipeline end-to-end while real data rights are not yet cleared. They are
never clinical data and never a basis for any clinical claim.
"""
from __future__ import annotations

import hashlib
import io

from PIL import Image

from app.models.dataset_governance import PROVENANCE_SYNTHETIC_EXPERIMENTAL
from app.services.observation_taxonomy import (
    OBSERVATION_CORROSION_LIKE,
    OBSERVATION_NO_ABNORMALITY,
    OBSERVATION_RETAINED_DEBRIS,
)

DEFAULT_CLASSES = [OBSERVATION_NO_ABNORMALITY, OBSERVATION_CORROSION_LIKE, OBSERVATION_RETAINED_DEBRIS]


def _class_image(label: str, idx: int, size: int = 96) -> bytes:
    """A deterministic, class-dependent synthetic image (distinct per class so a
    classifier has real signal, with small per-sample variation)."""
    base = {
        OBSERVATION_NO_ABNORMALITY: (210, 210, 210),
        OBSERVATION_CORROSION_LIKE: (150, 90, 40),
        OBSERVATION_RETAINED_DEBRIS: (60, 60, 60),
    }.get(label, (128, 128, 128))
    jitter = (idx * 7) % 20
    color = tuple(min(255, max(0, c + jitter - 10)) for c in base)
    img = Image.new("RGB", (size, size), color)
    px = img.load()
    # Class-dependent texture so the grid-mean stub embedding separates classes.
    if label == OBSERVATION_CORROSION_LIKE:
        for x in range(0, size, 6):
            for y in range(size):
                px[x, y] = (200, 120, 40)
    elif label == OBSERVATION_RETAINED_DEBRIS:
        for x in range(0, size, 12):
            for y in range(0, size, 12):
                px[x, y] = (255, 255, 255)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def synthetic_research_dataset(
    *, n_per_class: int = 6, classes: list[str] | None = None, tenant_id: str = "research-tenant",
    reliable_grouping: bool = True,
) -> list[dict]:
    """Build a deterministic synthetic research cohort.

    Each sample carries ``synthetic_experimental`` provenance and real grouping
    identities (instrument/inspection/specimen), unless ``reliable_grouping`` is
    False (used to test that unreliable grouping is detected).
    """
    classes = classes or DEFAULT_CLASSES
    samples: list[dict] = []
    sid = 0
    for label in classes:
        for _ in range(n_per_class):
            data = _class_image(label, sid)
            sha = hashlib.sha256(data).hexdigest()
            samples.append({
                "id": f"syn-{sid}",
                "label": label,
                "image_bytes": data,
                "image_sha256": sha,
                "tenant_id": tenant_id,
                "data_provenance_class": PROVENANCE_SYNTHETIC_EXPERIMENTAL,
                "provenance_approval_status": "not_required",
                "instrument_family": "scissors",
                "manufacturer": "SYN",
                "anatomy_zone": "hinge",
                "image_quality": "Good",
                # Grouping identities (or none, to exercise the reliability gate).
                "inspection_id": sid if reliable_grouping else None,
                "specimen_id": f"SYN-SPEC-{sid}" if reliable_grouping else "",
                "instrument_serial": f"SYN-{sid}" if reliable_grouping else None,
            })
            sid += 1
    return samples
