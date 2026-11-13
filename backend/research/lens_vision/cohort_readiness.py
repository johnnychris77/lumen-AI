"""Stage 6A — real-image cohort-readiness validation (research-only).

Builds on `docs/model-development/stage5d/DATASET_ACQUISITION_SPEC.md` — it is a
VALIDATOR and machine-readable reporter over a cohort *manifest*, not a new dataset
registry. It checks that each authorized research image carries the metadata,
authorization, labels, and split/grouping identifiers required before a real
benchmark can run, and it emits a cohort-readiness report listing exactly what
evidence and approvals are still missing.

Hard rules:

* An image is usable as a **verified-normal training example only** when it carries
  an independently-reviewed `verified_normal` label — an unlabeled image is never
  treated as normal.
* Abnormal-class images (corrosion/pitting/blood-like/bone-tissue-like) require a
  **laboratory-evidence reference** and, where spatial, an **approved mask**.
* Nothing here ingests images or bypasses Project Canvas governance; it reports
  readiness only.
"""
from __future__ import annotations

from research.lens_vision.provenance import RESEARCH_AUTHORIZED_CLASSES, sample_provenance_class

# Imaging modalities evaluated as SEPARATE cohorts.
MODALITY_EXTERNAL = "external_camera"
MODALITY_BORESCOPE = "borescope"
MODALITIES = frozenset({MODALITY_EXTERNAL, MODALITY_BORESCOPE})

# Reviewed ground-truth label states (reused from Stage 5A governance semantics).
GT_VERIFIED_NORMAL = "verified_normal"
GT_ABNORMAL = "abnormal"
GT_UNKNOWN = "unknown"
GT_UNLABELED = "unlabeled"

# Evaluation split assignments.
SPLITS = frozenset({"fit", "calibration", "validation", "sealed_test"})

# Abnormal evidence categories that REQUIRE independent laboratory confirmation.
_LAB_REQUIRED_CATEGORIES = frozenset({
    "corrosion_like_surface", "localized_pitting", "blood_like_residue",
    "bone_or_tissue_like_particle",
})

# Always-required identity/metadata fields (DATASET_ACQUISITION_SPEC §3).
_REQUIRED_FIELDS = (
    "image_id", "image_sha256", "instrument_id", "specimen_id",
    "modality", "anatomy_zone", "imaging_session_id", "imaging_device",
    "data_provenance_class", "institutional_authorization_ref",
    "data_rights", "retention_status", "study_batch_id", "split",
    "ground_truth_status",
)


def _missing_fields(img: dict) -> list[str]:
    missing = []
    for f in _REQUIRED_FIELDS:
        if str(img.get(f) or "").strip() == "":
            missing.append(f)
    return missing


def validate_image_readiness(img: dict) -> dict:
    """Validate one cohort-manifest image. Returns a per-image readiness record
    with the list of missing/invalid items (empty `blockers` == ready)."""
    blockers: list[str] = []
    missing = _missing_fields(img)
    blockers += [f"missing:{m}" for m in missing]

    modality = str(img.get("modality") or "").strip()
    if modality and modality not in MODALITIES:
        blockers.append(f"invalid_modality:{modality}")

    split = str(img.get("split") or "").strip()
    if split and split not in SPLITS:
        blockers.append(f"invalid_split:{split}")

    # Provenance must be research-authorized (clinical needs explicit approval +
    # research-use scope, handled by the existing governance on ingestion).
    cls = sample_provenance_class(img)
    if cls not in RESEARCH_AUTHORIZED_CLASSES:
        blockers.append(f"provenance_not_research_authorized:{cls}")

    gt = str(img.get("ground_truth_status") or "").strip()
    # Reviewer attribution is required for any usable label.
    if gt in {GT_VERIFIED_NORMAL, GT_ABNORMAL} and not str(img.get("label_reviewer_id") or "").strip():
        blockers.append("label_missing_independent_reviewer")

    # NEVER treat an unlabeled/unknown image as a normal training example.
    intended_use = str(img.get("intended_use") or "").strip()
    if intended_use == "normal_training" and gt != GT_VERIFIED_NORMAL:
        blockers.append("unlabeled_or_nonnormal_used_as_verified_normal")

    # Abnormal classes require laboratory evidence (+ approved mask when spatial).
    category = str(img.get("evidence_category") or "").strip()
    if gt == GT_ABNORMAL:
        if category in _LAB_REQUIRED_CATEGORIES and not str(img.get("laboratory_evidence_ref") or "").strip():
            blockers.append(f"missing_laboratory_evidence_for:{category}")
        if str(img.get("has_spatial_region") or "").strip() in {"1", "true", "True", "yes"} \
                and not str(img.get("approved_mask_ref") or "").strip():
            blockers.append("missing_approved_mask_for_spatial_region")

    return {
        "image_id": img.get("image_id"),
        "modality": modality or None,
        "split": split or None,
        "ground_truth_status": gt or None,
        "provenance_class": cls,
        "ready": not blockers,
        "blockers": blockers,
    }


def _group_identity(img: dict) -> str:
    for k in ("specimen_id", "imaging_session_id", "instrument_id", "study_batch_id", "image_sha256"):
        v = img.get(k)
        if v not in (None, ""):
            return f"{k}:{v}"
    return f"image_id:{img.get('image_id')}"


def generate_cohort_readiness_report(manifest: list[dict]) -> dict:
    """Produce a machine-readable readiness report for a cohort manifest.

    The report states, per modality and per split, how many images are ready, what
    evidence/approvals are missing, whether cross-split grouping is leakage-safe, and
    an overall `ready_for_benchmark` flag with the list of blockers. It fabricates no
    performance numbers; it reports only readiness.
    """
    per_image = [validate_image_readiness(img) for img in manifest]
    n_total = len(per_image)
    n_ready = sum(1 for r in per_image if r["ready"])

    # Aggregate missing-evidence reasons.
    reason_counts: dict[str, int] = {}
    for r in per_image:
        for b in r["blockers"]:
            key = b.split(":", 1)[0]
            reason_counts[key] = reason_counts.get(key, 0) + 1

    # Per-modality / per-split breakdown over READY images only.
    by_modality: dict[str, dict] = {}
    for img, r in zip(manifest, per_image):
        if not r["ready"]:
            continue
        m = r["modality"]
        s = r["split"]
        by_modality.setdefault(m, {sp: 0 for sp in sorted(SPLITS)})
        by_modality[m][s] = by_modality[m].get(s, 0) + 1

    # Leakage check: a physical group must not straddle splits (within a modality).
    leakage: list[str] = []
    group_to_splits: dict[tuple, set] = {}
    for img, r in zip(manifest, per_image):
        if not r["ready"]:
            continue
        key = (r["modality"], _group_identity(img))
        group_to_splits.setdefault(key, set()).add(r["split"])
    for (modality, gid), splits in sorted(group_to_splits.items()):
        if len(splits) > 1:
            leakage.append(f"{modality}:{gid} spans splits {sorted(splits)}")

    # A modality is benchmark-ready only with a fit set, a calibration set, and a
    # sealed-test set, and no cross-split leakage.
    modality_ready: dict[str, bool] = {}
    for m in MODALITIES:
        counts = by_modality.get(m, {})
        has_sets = counts.get("fit", 0) >= 1 and counts.get("calibration", 0) >= 1 and counts.get("sealed_test", 0) >= 1
        modality_ready[m] = bool(has_sets) and not any(x.startswith(f"{m}:") for x in leakage)

    blockers: list[str] = []
    if n_ready < n_total:
        blockers.append(f"{n_total - n_ready}/{n_total} images are not ingestion-ready (see missing_evidence)")
    if leakage:
        blockers.append(f"{len(leakage)} physical group(s) straddle evaluation splits")
    if not any(modality_ready.values()):
        blockers.append("no modality has a complete fit+calibration+sealed_test cohort")

    return {
        "schema": "lumenai.stage6a.cohort_readiness.v1",
        "n_images": n_total,
        "n_ready": n_ready,
        "ready_for_benchmark": n_total > 0 and n_ready == n_total and not leakage and any(modality_ready.values()),
        "missing_evidence": dict(sorted(reason_counts.items())),
        "by_modality_ready_counts": by_modality,
        "modality_ready": modality_ready,
        "cross_split_leakage": leakage,
        "blockers": blockers,
        "per_image": per_image,
        "note": (
            "Readiness only — no images ingested, no performance measured. "
            "Real benchmarking requires every blocker cleared and authorized data present."
        ),
    }
