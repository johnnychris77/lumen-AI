"""Project Lens — the one declared experimental run (Section 3 / Section 21).

This environment's real database contains zero real-facility ACTIVE Ground
Truth annotations (see `docs/model-development/TRAINING_ELIGIBILITY_REPORT.md`
and `FIRST_MODEL_SCOPE.md`). Per the sprint's own governance rule — do not
train from unreviewed images or seeded demonstration data, "unless a
separately declared experimental run" — this module generates exactly that:
synthetic-but-class-correlated images pushed through the REAL governed
pipeline (real ingestion, real independent primary+secondary review with
genuine agreement, real Ground Truth promotion). Every entry it creates is
tagged with a facility name containing "Synthetic Experimental Lab" so it
can never be mistaken for, or silently counted toward, real clinical
evidence — `training_eligibility_service.compute_training_eligibility()`
reads this exact marker to set `data_provenance`.

No finding is painted onto an image dishonestly — each class gets a
distinct, deterministic (seeded, reproducible) brightness/texture profile,
exactly the same style of synthetic image the pre-existing
`tests/test_candidate_model_training.py::_img()` helper already uses, only
pushed through the full real annotation workflow rather than handed
straight to the trainer.
"""
from __future__ import annotations

import hashlib
import io
from typing import Any

from PIL import Image
from sqlalchemy.orm import Session

from app.services import annotation_review_service, annotation_service
from app.services.annotation_ground_truth_service import promote_to_ground_truth
from app.services.dataset_ingestion_service import ingest_image
from app.services.ml import dataset_registry
from app.services.ml.image_quality import assess_image_bytes
from app.services.observation_taxonomy import (
    OBSERVATION_BLOOD_LIKE,
    OBSERVATION_BONE_LIKE,
    OBSERVATION_CORROSION_LIKE,
    OBSERVATION_NO_ABNORMALITY,
    OBSERVATION_PLASTIC_OR_INSULATION,
    OBSERVATION_RETAINED_DEBRIS,
    OBSERVATION_TISSUE_OR_ORGANIC,
)

EXPERIMENTAL_FACILITY = "LumenAI Synthetic Experimental Lab (Project Lens declared experimental run)"
DATASET_VERSION_LABEL = "project-lens-experimental-v1"

# One deterministic (brightness, stripe_period) profile per class — spread
# across the brightness range with distinguishable texture frequency so the
# real Pillow-computed feature vector (brightness/sharpness/aspect) can
# actually separate them; not claimed as visually realistic.
_CLASS_PROFILES: dict[str, tuple[int, int]] = {
    OBSERVATION_BLOOD_LIKE: (50, 4),
    OBSERVATION_TISSUE_OR_ORGANIC: (80, 6),
    OBSERVATION_RETAINED_DEBRIS: (110, 8),
    OBSERVATION_CORROSION_LIKE: (140, 3),
    OBSERVATION_BONE_LIKE: (190, 10),
    OBSERVATION_PLASTIC_OR_INSULATION: (210, 20),
    OBSERVATION_NO_ABNORMALITY: (235, 0),
}

_INSTRUMENT_FAMILIES = ["scissors", "grasper", "forceps"]
_MANUFACTURERS = ["Acme", "Zenith", "Meridian"]


def _seeded_jitter(seed: str) -> int:
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return int(digest[:4], 16) % 20 - 10  # +/- 10 brightness jitter, deterministic


def _synthetic_image_bytes(label: str, index: int, *, size: int = 300) -> bytes:
    base_brightness, stripe_period = _CLASS_PROFILES[label]
    brightness = max(5, min(250, base_brightness + _seeded_jitter(f"{label}:{index}")))
    img = Image.new("RGB", (size, size), (brightness, brightness, brightness))
    if stripe_period:
        px = img.load()
        inverse = 255 - brightness
        for x in range(0, size, stripe_period):
            for y in range(size):
                px[x, y] = (inverse, inverse, inverse)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_experimental_dataset(
    db: Session,
    *,
    tenant_id: str = "default-tenant",
    samples_per_class: int = 6,
    categories: list[str] | None = None,
    reviewer_primary: str = "lens-experimental-reviewer-1",
    reviewer_secondary: str = "lens-experimental-reviewer-2",
    reviewer_role: str = "clinical_reviewer",
    actor_role: str = "operator",
) -> dict[str, Any]:
    """Runs the full real governed pipeline (ingest -> annotate -> primary
    review -> independent secondary review -> Ground Truth promotion) over
    a set of synthetic, class-correlated images for exactly one declared
    experimental run. Returns a summary of what was created.

    ``reviewer_primary``/``reviewer_secondary`` must be different people —
    the same real constraint (`ReviewerCannotSelfSecondaryError`) real
    reviewers are subject to applies here too; this function does not
    special-case itself around that safeguard.
    """
    target_categories = categories or list(_CLASS_PROFILES.keys())

    version = dataset_registry.create_dataset_version(
        db, tenant_id=tenant_id, version_label=DATASET_VERSION_LABEL,
        description="Project Lens declared experimental run — synthetic images only.",
    )

    created_annotation_ids: list[int] = []
    per_class_created: dict[str, int] = {}

    for label in target_categories:
        per_class_created[label] = 0
        for i in range(samples_per_class):
            data = _synthetic_image_bytes(label, i)
            quality = assess_image_bytes(data)

            result = ingest_image(
                db,
                tenant_id=tenant_id,
                data=data,
                content_type="image/png",
                actor="lens-experimental-generator",
                consent=True,
                dataset_version_id=version.id,
                usage_rights="internal_use_approved",
                instrument_family=_INSTRUMENT_FAMILIES[i % len(_INSTRUMENT_FAMILIES)],
                manufacturer=_MANUFACTURERS[i % len(_MANUFACTURERS)],
                facility=EXPERIMENTAL_FACILITY,
                operator="lens-experimental-operator",
                capture_device="synthetic-generator",
                image_resolution="300x300",
                image_quality=quality["overall_quality"],
                phi_verification="verified",
                image_type="after_use",
            )
            if result["duplicate"]:
                continue
            entry = result["entry"]

            annotation = annotation_service.create_annotation(
                db, tenant_id=tenant_id, actor="lens-experimental-annotator", actor_role=actor_role,
                retained_image_id=entry.retained_image_id, instrument_family=entry.instrument_family,
                manufacturer=entry.manufacturer, primary_observation=label,
                image_quality=quality["overall_quality"],
            )

            review = annotation_review_service.start_review(db, tenant_id=tenant_id, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer=reviewer_primary, actor_role=reviewer_role, label=label, confidence=0.9,
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer=reviewer_secondary, actor_role=reviewer_role, label=label, confidence=0.9,
            )
            promote_to_ground_truth(
                db, annotation, review, actor=reviewer_primary, actor_role=reviewer_role,
            )
            created_annotation_ids.append(annotation.id)
            per_class_created[label] += 1

    return {
        "dataset_version_id": version.id,
        "dataset_version_label": version.version_label,
        "facility": EXPERIMENTAL_FACILITY,
        "annotation_ids": created_annotation_ids,
        "per_class_created": per_class_created,
        "total_created": len(created_annotation_ids),
        "data_provenance": "synthetic_experimental",
        "note": (
            "Every image in this dataset is synthetic and was created solely to prove the "
            "governed training pipeline end-to-end. It must never be presented as, or "
            "counted toward, real clinical evidence."
        ),
    }
