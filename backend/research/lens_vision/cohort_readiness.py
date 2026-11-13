"""Stage 6A/6B — real-image cohort-readiness validation (research-only).

Builds on `docs/model-development/stage5d/DATASET_ACQUISITION_SPEC.md` — it is a
VALIDATOR and machine-readable reporter over a cohort *manifest*, not a new dataset
registry.

Stage 6B corrections (from independent review):

* **Comprehensive grouping / leakage (6B-2a).** Leakage is detected over the FULL
  set of physical-identity tokens — instrument, specimen, acquisition session, study
  batch, image hash, and repeat-imaging relationship — across ALL splits
  (fit/calibration/validation/sealed-test) and ACROSS imaging modalities. (Stage 6A
  used first-identity-only grouping scoped per modality, which could miss leakage.)
* **Readiness integrity (6B-2c).** Readiness is decomposed into five independent
  dimensions — metadata completeness, verified authorization, ground-truth
  readiness, model-execution readiness, and statistical adequacy. A filled-in
  manifest, or a single image per split, never implies a scientifically valid
  benchmark is ready: statistical adequacy requires minimum cohort sizes AND a
  statistical-reviewer sign-off, neither assumed.

Hard rules (unchanged): an image is usable as a verified-normal training example
only with an independently-reviewed `verified_normal` label; abnormal classes require
laboratory evidence (+ approved mask when spatial); nothing is ingested here.
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
SPLITS = ("fit", "calibration", "validation", "sealed_test")

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

# Authorization-specific fields (dimension: verified_authorization).
_AUTHORIZATION_FIELDS = ("institutional_authorization_ref", "data_rights", "retention_status")

# Default minimum per-split cohort sizes PER MODALITY. These are placeholders that a
# statistical reviewer must confirm/replace; meeting them is necessary but NOT
# sufficient (sign-off is also required).
_DEFAULT_MIN_SIZES = {"fit": 20, "calibration": 20, "validation": 20, "sealed_test": 30}


def image_identity_tokens(img: dict) -> set[str]:
    """ALL physical-identity tokens an image carries. Two images that share ANY token
    belong to the same group and must never straddle evaluation splits — regardless
    of imaging modality."""
    toks: set[str] = set()
    for key, prefix in (
        ("instrument_id", "instrument"), ("specimen_id", "specimen"),
        ("imaging_session_id", "session"), ("study_batch_id", "batch"),
        ("image_sha256", "sha"),
    ):
        v = img.get(key)
        if v not in (None, ""):
            toks.add(f"{prefix}:{v}")
    # Repeat-imaging relationship: re-images of the same physical item/region.
    for rep_key in ("repeat_imaging_group", "repeat_of"):
        rep = img.get(rep_key)
        if rep not in (None, ""):
            toks.add(f"repeat:{rep}")
    return toks


def validate_image_readiness(img: dict) -> dict:
    """Validate one cohort-manifest image across the readiness categories. Returns a
    per-image record whose blockers are tagged by dimension."""
    meta: list[str] = []
    authz: list[str] = []
    gtr: list[str] = []

    for f in _REQUIRED_FIELDS:
        if str(img.get(f) or "").strip() == "":
            meta.append(f"missing:{f}")

    modality = str(img.get("modality") or "").strip()
    if modality and modality not in MODALITIES:
        meta.append(f"invalid_modality:{modality}")
    split = str(img.get("split") or "").strip()
    if split and split not in SPLITS:
        meta.append(f"invalid_split:{split}")

    # Authorization: research-authorized provenance + authorization refs.
    cls = sample_provenance_class(img)
    if cls not in RESEARCH_AUTHORIZED_CLASSES:
        authz.append(f"provenance_not_research_authorized:{cls}")
    for f in _AUTHORIZATION_FIELDS:
        if str(img.get(f) or "").strip() == "":
            authz.append(f"missing_authorization:{f}")

    # Ground-truth readiness.
    gt = str(img.get("ground_truth_status") or "").strip()
    if gt in {GT_VERIFIED_NORMAL, GT_ABNORMAL} and not str(img.get("label_reviewer_id") or "").strip():
        gtr.append("label_missing_independent_reviewer")
    if str(img.get("intended_use") or "").strip() == "normal_training" and gt != GT_VERIFIED_NORMAL:
        gtr.append("unlabeled_or_nonnormal_used_as_verified_normal")
    category = str(img.get("evidence_category") or "").strip()
    if gt == GT_ABNORMAL:
        if category in _LAB_REQUIRED_CATEGORIES and not str(img.get("laboratory_evidence_ref") or "").strip():
            gtr.append(f"missing_laboratory_evidence_for:{category}")
        if str(img.get("has_spatial_region") or "").strip() in {"1", "true", "True", "yes"} \
                and not str(img.get("approved_mask_ref") or "").strip():
            gtr.append("missing_approved_mask_for_spatial_region")

    blockers = meta + authz + gtr
    return {
        "image_id": img.get("image_id"),
        "modality": modality or None,
        "split": split or None,
        "ground_truth_status": gt or None,
        "provenance_class": cls,
        "metadata_blockers": meta,
        "authorization_blockers": authz,
        "ground_truth_blockers": gtr,
        "ready": not blockers,
        "blockers": blockers,
    }


def _detect_leakage(manifest: list[dict], per_image: list[dict]) -> list[str]:
    """Any physical-identity token shared between two DIFFERENT splits is leakage —
    checked across all splits and across imaging modalities."""
    token_split_to_images: dict[tuple[str, str], list] = {}
    split_of_token: dict[str, set[str]] = {}
    for img, r in zip(manifest, per_image):
        split = r["split"]
        if not split:
            continue
        for tok in image_identity_tokens(img):
            split_of_token.setdefault(tok, set()).add(split)
            token_split_to_images.setdefault((tok, split), []).append(r["image_id"])
    leakage: list[str] = []
    for tok, splits in sorted(split_of_token.items()):
        if len(splits) > 1:
            leakage.append(f"{tok} spans splits {sorted(splits)}")
    return leakage


def generate_cohort_readiness_report(
    manifest: list[dict], *, min_cohort_sizes: dict | None = None,
    scientific_checkpoint_approved: bool = False,
    statistical_reviewer_signoff: dict | None = None,
) -> dict:
    """Produce a machine-readable readiness report with FIVE independent dimensions.

    ``ready_for_scientific_benchmark`` is True only when every dimension passes AND
    there is no cross-split leakage. It fabricates no performance numbers.

    * ``scientific_checkpoint_approved`` — set True only when a scientifically-usable,
      rights-cleared, digest-verified checkpoint exists (see checkpoint governance).
    * ``statistical_reviewer_signoff`` — a dict recording the reviewer's approval of
      cohort sizes/criteria; None (default) means statistical adequacy is NOT met.
    """
    min_sizes = {**_DEFAULT_MIN_SIZES, **(min_cohort_sizes or {})}
    per_image = [validate_image_readiness(img) for img in manifest]
    n_total = len(per_image)
    n_ready = sum(1 for r in per_image if r["ready"])

    reason_counts: dict[str, int] = {}
    for r in per_image:
        for b in r["blockers"]:
            key = b.split(":", 1)[0]
            reason_counts[key] = reason_counts.get(key, 0) + 1

    # Per-modality / per-split counts over READY images.
    by_modality: dict[str, dict] = {}
    for r in per_image:
        if not r["ready"]:
            continue
        by_modality.setdefault(r["modality"], {sp: 0 for sp in SPLITS})
        by_modality[r["modality"]][r["split"]] = by_modality[r["modality"]].get(r["split"], 0) + 1

    leakage = _detect_leakage(manifest, per_image)

    # ── Five independent readiness dimensions ──────────────────────────────────
    meta_blockers = sorted({b for r in per_image for b in r["metadata_blockers"]})
    authz_blockers = sorted({b for r in per_image for b in r["authorization_blockers"]})
    gt_blockers = sorted({b for r in per_image for b in r["ground_truth_blockers"]})

    # Statistical adequacy: at least one modality meets the minimum sizes across all
    # splits (external and borescope are evaluated separately, so a single-modality
    # cohort is allowed) AND a statistical reviewer has signed off. A PRESENT but
    # under-sized modality is reported, but an absent modality is not a blocker.
    stat_blockers: list[str] = []
    any_modality_sized = False
    for m in sorted(by_modality):  # only modalities that actually have ready images
        counts = by_modality[m]
        if all(counts.get(sp, 0) >= min_sizes[sp] for sp in SPLITS):
            any_modality_sized = True
        else:
            short = [f"{m}:{sp}({counts.get(sp, 0)}/{min_sizes[sp]})" for sp in SPLITS
                     if counts.get(sp, 0) < min_sizes[sp]]
            stat_blockers.append("under_min_cohort_size:" + ",".join(short))
    if not any_modality_sized:
        stat_blockers.append("no_modality_meets_minimum_cohort_sizes")
    if not statistical_reviewer_signoff:
        stat_blockers.append("statistical_reviewer_signoff_absent")
    # Adequacy requires a fully-sized modality + sign-off; a present-but-undersized
    # modality alongside a complete one does not negate adequacy.
    stat_ready = any_modality_sized and bool(statistical_reviewer_signoff)

    dimensions = {
        "metadata_completeness": {"ready": not meta_blockers, "blockers": meta_blockers},
        "verified_authorization": {"ready": not authz_blockers, "blockers": authz_blockers},
        "ground_truth_readiness": {"ready": not gt_blockers, "blockers": gt_blockers},
        "model_execution_readiness": {
            "ready": bool(scientific_checkpoint_approved),
            "blockers": [] if scientific_checkpoint_approved else ["no_scientifically_approved_checkpoint"],
        },
        "statistical_adequacy": {"ready": stat_ready, "blockers": stat_blockers},
    }
    leakage_free = not leakage
    ready_for_scientific_benchmark = (
        n_total > 0 and all(d["ready"] for d in dimensions.values()) and leakage_free
    )

    blockers: list[str] = []
    for name, d in dimensions.items():
        if not d["ready"]:
            blockers.append(f"{name}_not_ready")
    if leakage:
        blockers.append(f"{len(leakage)} physical group(s) straddle evaluation splits")

    return {
        "schema": "lumenai.stage6b.cohort_readiness.v2",
        "n_images": n_total,
        "n_ready": n_ready,
        "dimensions": dimensions,
        "cross_split_leakage": leakage,
        "leakage_free": leakage_free,
        "by_modality_ready_counts": by_modality,
        "min_cohort_sizes": min_sizes,
        "ready_for_scientific_benchmark": ready_for_scientific_benchmark,
        # Back-compat alias; now carries the corrected (stricter) semantics.
        "ready_for_benchmark": ready_for_scientific_benchmark,
        "missing_evidence": dict(sorted(reason_counts.items())),
        "blockers": blockers,
        "per_image": per_image,
        "note": (
            "Readiness only — no images ingested, no performance measured. A complete "
            "manifest or one image per split does NOT make a benchmark scientifically "
            "ready; statistical adequacy requires minimum cohort sizes AND a statistical "
            "reviewer sign-off, and an approved scientific checkpoint must exist."
        ),
    }
