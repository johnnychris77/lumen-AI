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
# RGI-07: the three authorization fields (institutional_authorization_ref, data_rights,
# retention_status) are DELIBERATELY NOT listed here — they belong to the
# ``verified_authorization`` dimension only. Listing them in both sets made a single
# missing authorization field fail BOTH ``metadata_completeness`` and
# ``verified_authorization``, obscuring which independent gate actually failed.
_REQUIRED_FIELDS = (
    "image_id", "image_sha256", "instrument_id", "specimen_id",
    "modality", "anatomy_zone", "imaging_session_id", "imaging_device",
    "data_provenance_class", "study_batch_id", "split",
    "ground_truth_status",
)

# Authorization-specific fields (dimension: verified_authorization).
_AUTHORIZATION_FIELDS = ("institutional_authorization_ref", "data_rights", "retention_status")

# RGI-01: fail-closed VALUE validation for authorization fields — a non-empty value is
# not enough; only an explicitly granted/active value authorizes research use. These
# vocabularies are conservative defaults; the canonical institutional vocabulary and the
# resolution of ``institutional_authorization_ref`` against a verified authorization
# registry are GOVERNANCE decisions (see P4_3 doc) — this validator only rejects values
# that can never authorize use (e.g. "denied", "purged", "expired", unknown strings).
_DATA_RIGHTS_GRANTED = frozenset({
    "research", "research_use", "research_use_granted", "granted", "cleared",
    "approved_research_use",
})
_RETENTION_ACTIVE = frozenset({"active", "retained", "retention_authorized"})

# Default minimum per-split cohort sizes PER MODALITY. These are placeholders that a
# statistical reviewer must confirm/replace; meeting them is necessary but NOT
# sufficient (sign-off is also required).
_DEFAULT_MIN_SIZES = {"fit": 20, "calibration": 20, "validation": 20, "sealed_test": 30}


def valid_statistical_signoff(signoff: dict | None) -> bool:
    """RGI-02: a statistical-reviewer sign-off is valid ONLY when it is an explicit,
    affirmative approval by an identified reviewer — never mere dict truthiness.

    Fail-closed: requires ``approved is True`` AND a non-empty ``reviewer_id``, and rejects
    any negative/revocation signal (``rejected`` / ``revoked`` / ``withdrawn`` truthy). A
    bare approver id, ``{"approved": false}``, or ``{"rejected": true}`` do NOT approve.

    NOTE (governance): binding the sign-off to the correct tenant / dataset / checkpoint /
    intended use, and authenticating the reviewer against an authorized-reviewer registry,
    is enforced by the scientific-authorization layer where those identities are known; this
    structural check is the fail-closed floor, not the whole control.
    """
    if not isinstance(signoff, dict):
        return False
    if signoff.get("approved") is not True:
        return False
    if signoff.get("rejected") or signoff.get("revoked") or signoff.get("withdrawn"):
        return False
    return bool(str(signoff.get("reviewer_id") or "").strip())


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
    # RGI-05: link an ORIGINAL capture to the repeats that reference it. A repeat carries
    # ``repeat:<original_image_id>``; giving every image ``repeat:<own_image_id>`` makes the
    # referenced original share that exact token, so an original in one split and its repeat
    # in another are detected as the same physical group (previously only the repeat got the
    # token, so the original/repeat pair could straddle splits undetected).
    own = img.get("image_id")
    if own not in (None, ""):
        toks.add(f"repeat:{own}")
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
    # RGI-01: present-but-INVALID authorization values do not authorize research use.
    dr = str(img.get("data_rights") or "").strip().lower()
    if dr and dr not in _DATA_RIGHTS_GRANTED:
        authz.append(f"data_rights_not_granted:{dr}")
    rs = str(img.get("retention_status") or "").strip().lower()
    if rs and rs not in _RETENTION_ACTIVE:
        authz.append(f"retention_not_active:{rs}")

    # Ground-truth readiness.
    gt = str(img.get("ground_truth_status") or "").strip()
    if gt in {GT_VERIFIED_NORMAL, GT_ABNORMAL} and not str(img.get("label_reviewer_id") or "").strip():
        gtr.append("label_missing_independent_reviewer")
    # RGI-06: ground-truth eligibility is determined by the evaluation SPLIT, not by an
    # optional ``intended_use`` field (which a manifest could omit to slip unlabeled images
    # through). Fit and calibration require an independently-reviewed verified_normal label;
    # validation and sealed_test require a reviewed label (verified_normal OR abnormal).
    if split in ("fit", "calibration") and gt != GT_VERIFIED_NORMAL:
        gtr.append(f"{split}_requires_verified_normal:{gt or 'unlabeled'}")
    if split in ("validation", "sealed_test") and gt not in {GT_VERIFIED_NORMAL, GT_ABNORMAL}:
        gtr.append(f"{split}_requires_reviewed_label:{gt or 'unlabeled'}")
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
    signoff_ok = valid_statistical_signoff(statistical_reviewer_signoff)
    if not signoff_ok:
        stat_blockers.append("statistical_reviewer_signoff_absent_or_invalid")
    # Adequacy requires a fully-sized modality + a VALID affirmative sign-off; a present-
    # but-undersized modality alongside a complete one does not negate adequacy.
    stat_ready = any_modality_sized and signoff_ok

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
