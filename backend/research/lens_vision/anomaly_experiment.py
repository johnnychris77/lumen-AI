"""Governed, research-only anomaly-localization experiment (Stage 5B + 5C).

Protocol (predefined, in order): supplied-dataset governance → research-provenance
gate → verified-normal-only fit → **calibration on a DEDICATED normal set with a
FROZEN threshold** → leakage-checked held-out evaluation with validated metrics +
confidence intervals. Thresholds are never selected per test image. Severity is
never inferred from scores; synthetic fixtures are flagged as a technical test and
never reported as clinical accuracy. All outputs are research-only and finite.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Callable

from research.lens_vision.anomaly_contract import build_anomaly_result
from research.lens_vision.anomaly_localization import AnomalyLocalizer, propose_regions
from research.lens_vision.artifact_store import (
    MalformedMaskError,
    sanitize_score,
    validate_heatmap,
    validate_mask,
)
from research.lens_vision.calibration import (
    auroc,
    average_precision,
    bootstrap_auroc_ci,
    classification_metrics,
    dice_iou,
    fit_frozen_threshold,
)
from research.lens_vision.checkpoint import (
    CheckpointError,
    CheckpointScientificUseError,
    assert_scientific_checkpoint,
    get_record,
)
from research.lens_vision.governance import GT_VERIFIED_NORMAL, enforce_supplied_dataset_governance
from research.lens_vision.provenance import assert_research_authorized


class NormalOnlyViolation(ValueError):
    """A non-verified-normal image was supplied to fit a normal-only model."""


class LeakageError(ValueError):
    """Train/calibration and held-out sets share a physical-instrument / specimen /
    session / image / laboratory-batch identity — independent evaluation would be invalid."""


class InvalidLabelError(ValueError):
    """RGI-09: an anomaly label was not binary (0/1) where a binary label is required."""


class LocalizerConfigMismatchError(ValueError):
    """RGI-08: the supplied localizer's backbone checkpoint does not match the run config's
    ``checkpoint_id`` — results would misattribute metrics to the wrong weights."""


def _effective_sha(s: dict) -> str:
    """RGI-05: the trusted image identity is the SHA-256 of the actual bytes when present;
    the caller-supplied ``image_sha256`` is used only as a fallback when no bytes are
    available. Two records with identical bytes therefore always share an ``img:`` token —
    even if their declared hashes are empty, stale, or disagree — so byte-level duplicates
    cannot straddle splits undetected."""
    b = s.get("image_bytes")
    if isinstance(b, (bytes, bytearray)) and len(b) > 0:
        return hashlib.sha256(bytes(b)).hexdigest()
    return str(s.get("image_sha256") or "")


def _binary_label(v) -> int:
    """RGI-09: coerce a label to a strict binary 0/1 or raise. Rejects out-of-domain values
    (e.g. 2), and undefined string/number mixes — never silently treats them as positive."""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int) and v in (0, 1):
        return v
    if isinstance(v, float) and v in (0.0, 1.0):
        return int(v)
    if isinstance(v, str) and v.strip() in ("0", "1"):
        return int(v.strip())
    raise InvalidLabelError(f"anomaly_label must be a binary 0/1 value; got {v!r}.")


def _identity_tokens(s: dict) -> set[str]:
    toks = set()
    for key, prefix in (("instrument_serial", "serial"), ("inspection_id", "insp"),
                        ("specimen_id", "spec"), ("session_id", "sess"),
                        ("laboratory_batch_id", "lab")):
        v = s.get(key)
        if v not in (None, ""):
            toks.add(f"{prefix}:{v}")
    sha = _effective_sha(s)  # RGI-05: byte-derived when bytes are present
    if sha:
        toks.add(f"img:{sha}")
    return toks


def _real_identity(s: dict) -> bool:
    return any(s.get(k) not in (None, "") for k in ("instrument_serial", "inspection_id", "specimen_id", "session_id"))


# Fine-grained physical identity that must never straddle the fit / calibration
# boundary: a single specimen / session / instrument / inspection / exact image
# belongs wholly to one split, so calibration is never contaminated by a fit-set
# specimen. (Laboratory BATCH is deliberately excluded here — fit and calibration
# may draw different specimens from the same batch — but batch still separates
# train from the held-out TEST set via the full identity tokens below.)
_GROUP_KEYS = ("specimen_id", "session_id", "instrument_serial", "inspection_id", "image_sha256")


def _group_key(s: dict) -> str:
    """The grouping identity of a sample (strongest available), or its image id
    when no physical grouping identity exists (each such image is its own group)."""
    for k in _GROUP_KEYS:
        v = s.get(k)
        if v not in (None, ""):
            return f"{k}:{v}"
    return f"id:{s.get('id')}"


def _split_fit_calibration(normal_samples: list[dict]) -> tuple[list[dict], list[dict]]:
    """Deterministically split verified-normal images into a FIT set and a
    dedicated CALIBRATION set (~30%), GROUPED so that a single specimen / session /
    batch / instrument is never split across the two (no calibration leakage)."""
    groups: dict[str, list[dict]] = {}
    for s in normal_samples:
        groups.setdefault(_group_key(s), []).append(s)
    ordered_groups = sorted(groups)  # deterministic
    n_groups = len(ordered_groups)
    # Take ~30% of GROUPS (at least one) into calibration; the rest fit.
    n_cal_groups = max(1, round(n_groups * 0.3)) if n_groups > 1 else 1
    if n_groups == 1:
        # Only one group: it cannot be both fit and calibration without leakage.
        # Fall back to a within-group image split only when the group is a set of
        # identity-less images (each its own group would normally prevent this).
        only = ordered_groups[0]
        imgs = sorted(groups[only], key=lambda s: str(s.get("id")))
        n_cal = max(1, round(len(imgs) * 0.3))
        return imgs[n_cal:], imgs[:n_cal]
    cal_group_set = set(ordered_groups[:n_cal_groups])
    fit, calibration = [], []
    for g in ordered_groups:
        (calibration if g in cal_group_set else fit).extend(groups[g])
    return fit, calibration


def _assert_split_group_separation(fit: list[dict], calib: list[dict], test: list[dict]) -> None:
    """Fail-closed separation across the three splits:

    * **fit vs calibration** — no shared fine-grained physical identity
      (specimen / session / instrument / inspection / exact image), so calibration
      is never contaminated by a fit-set specimen;
    * **(fit ∪ calibration) vs test** — no shared identity of ANY kind, INCLUDING
      laboratory batch, so a batch effect can't leak labels into the held-out set.
    """
    fit_g = {_group_key(s) for s in fit}
    cal_g = {_group_key(s) for s in calib}
    if fit_g & cal_g:
        raise LeakageError(
            "Fit and calibration sets share a specimen/session/instrument/image identity "
            f"({sorted(fit_g & cal_g)[:3]}) — calibration leakage."
        )
    train_tok: set[str] = set()
    for s in fit + calib:
        train_tok |= _identity_tokens(s)
    for s in test:
        shared = _identity_tokens(s) & train_tok
        if shared:
            raise LeakageError(
                f"Held-out image {s.get('id')} shares an identity {sorted(shared)[:3]} with the "
                "fit/calibration set (instrument/specimen/session/image/laboratory-batch)."
            )


def _pixel_scores(heatmap: list[list[float]]) -> list[float]:
    return [v for row in heatmap for v in row]


def run_anomaly_experiment(
    normal_samples: list[dict], test_samples: list[dict], *, config, localizer: AnomalyLocalizer,
    calibration_samples: list[dict] | None = None, target_fpr: float = 0.05,
    synthetic_technical_test: bool = False, allow_approved_clinical: bool = False,
    artifact_store=None, abstain_margin: float = 0.0,
    subgroup_keys: tuple[str, ...] = ("instrument_family", "lighting_condition", "anatomy_zone"),
    require_scientific: bool = False,
) -> dict[str, Any]:
    everything = normal_samples + (calibration_samples or []) + test_samples

    # 1) Research-provenance gate (ResearchProvenanceError) FIRST, then the full
    #    supplied-dataset governance (integrity + no cross-tenant mixing).
    assert_research_authorized(everything, allow_approved_clinical=allow_approved_clinical)

    # 2) Normal-only integrity BEFORE any split or governance size-checks.
    for s in normal_samples + (calibration_samples or []):
        if s.get("ground_truth_status") != GT_VERIFIED_NORMAL:
            raise NormalOnlyViolation(
                f"Image {s.get('id')} has ground_truth_status '{s.get('ground_truth_status')}' — "
                "only verified_normal may fit/calibrate a normal-only model."
            )

    enforce_supplied_dataset_governance(everything, allow_approved_clinical=allow_approved_clinical)

    # 3) Dedicated calibration set (frozen threshold) — explicit, or a deterministic split.
    if calibration_samples is not None:
        fit_normals, calib_normals = list(normal_samples), list(calibration_samples)
    else:
        if len(normal_samples) < 2:
            raise ValueError("At least 2 verified-normal images are required (fit + dedicated calibration).")
        fit_normals, calib_normals = _split_fit_calibration(normal_samples)

    # 4) Leakage: fit, calibration AND held-out test must each be disjoint by
    #    physical grouping identity (specimen/session/batch/instrument/image). This
    #    covers calibration leakage (a fit specimen reused for calibration), not
    #    only train-vs-test.
    _assert_split_group_separation(fit_normals, calib_normals, test_samples)

    all_have_identity = all(_real_identity(s) for s in everything)
    grouping_limitations = [] if all_have_identity else [
        "some samples lack a real grouping identity (instrument/inspection/specimen/session)"
    ]

    record = None
    try:
        record = get_record(config.checkpoint_id) if config.checkpoint_id else None
    except CheckpointError:
        record = None

    # RGI-08: the localizer actually fitted MUST be the one the config names. Otherwise the
    # result would record the config's checkpoint/digest while a different backbone produced
    # the scores — silently misattributing metrics and corrupting reproducibility evidence.
    loc_ckpt = str(getattr(localizer, "checkpoint_id", "") or "")
    cfg_ckpt = str(getattr(config, "checkpoint_id", "") or "")
    if loc_ckpt and cfg_ckpt and loc_ckpt != cfg_ckpt:
        raise LocalizerConfigMismatchError(
            f"Localizer backbone checkpoint '{loc_ckpt}' does not match config checkpoint "
            f"'{cfg_ckpt}'. Results would be attributed to the wrong weights."
        )

    # RGI-03: scientific eligibility is DERIVED from the checkpoint governance gate inside
    # this metric-producing path — never trusted from the caller's synthetic flag. A run
    # whose checkpoint is not approved for scientific use (e.g. a random-weight / execution-
    # only / stub backbone) is authoritatively a technical test: its metrics are labelled
    # non-scientific and are never publishable as performance. With require_scientific=True a
    # publisher additionally REFUSES (raises) an ineligible checkpoint.
    scientifically_eligible = False
    if record is not None:
        try:
            assert_scientific_checkpoint(record)
            scientifically_eligible = True
        except CheckpointScientificUseError:
            scientifically_eligible = False
    if require_scientific and not scientifically_eligible:
        raise CheckpointScientificUseError(
            f"Scientific metric publication requires a scientifically-approved checkpoint; "
            f"'{cfg_ckpt or '(none)'}' is not eligible."
        )
    technical_test = synthetic_technical_test or not scientifically_eligible

    # 5) Fit on verified-normal FIT images only.
    localizer.fit([s["image_bytes"] for s in fit_normals])

    # 6) Calibrate + FREEZE thresholds on the dedicated calibration normals.
    cal_image_scores: list[float] = []
    cal_pixel_scores: list[float] = []
    for s in calib_normals:
        heatmap, score = localizer.score(s["image_bytes"])
        validate_heatmap(heatmap)
        cal_image_scores.append(sanitize_score(score))
        cal_pixel_scores.extend(_pixel_scores(heatmap))
    frozen = fit_frozen_threshold(cal_image_scores, cal_pixel_scores, target_fpr=target_fpr)

    # 7) Held-out evaluation with the FROZEN thresholds.
    results: list[dict] = []
    image_scores: list[float] = []
    image_labels: list[int] = []
    dices: list[float] = []
    ious: list[float] = []
    latencies_ms: list[float] = []
    n_abstained = 0
    subgroup_scores: dict[str, dict[str, list]] = {k: {} for k in subgroup_keys}

    for s in test_samples:
        t0 = time.perf_counter()
        heatmap, image_score = localizer.score(s["image_bytes"])
        latencies_ms.append(round((time.perf_counter() - t0) * 1000.0, 3))
        h, w = validate_heatmap(heatmap)
        image_score = sanitize_score(image_score)

        regions = propose_regions(heatmap, threshold=frozen.pixel_threshold, max_regions=5)
        heatmap_ref = ""
        if artifact_store is not None:
            heatmap_ref = artifact_store.store_heatmap(
                tenant_id=s.get("tenant_id", ""), run_id=config.run_id, image_id=s.get("id"), heatmap=heatmap,
            ) or ""

        res = build_anomaly_result(
            sample=s, image_score=image_score, heatmap_shape=(h, w), heatmap_ref=heatmap_ref, regions=regions,
            config=config, record=record, grouping_reliable=all_have_identity,
            validation_limitations=grouping_limitations,
        )
        results.append(res.to_dict())

        # Abstention band around the frozen image threshold.
        if abstain_margin > 0 and abs(image_score - frozen.image_threshold) <= abstain_margin * max(1e-9, frozen.image_threshold):
            n_abstained += 1
            continue

        image_scores.append(image_score)
        if "anomaly_label" in s:
            label = _binary_label(s["anomaly_label"])  # RGI-09: reject non-binary labels
            image_labels.append(label)
            for k in subgroup_keys:
                gv = s.get(k)
                if gv:
                    g = subgroup_scores[k].setdefault(gv, {"scores": [], "labels": []})
                    g["scores"].append(image_score)
                    g["labels"].append(label)

        gt_mask = s.get("anomaly_mask")
        if gt_mask is not None:
            try:
                validate_mask(gt_mask, width=w, height=h)
            except MalformedMaskError:
                continue  # malformed reference mask -> excluded from pixel metrics
            pred_mask = [[1 if v >= frozen.pixel_threshold else 0 for v in row] for row in heatmap]
            d, i = dice_iou(pred_mask, gt_mask)
            dices.append(d)
            ious.append(i)

    have_labels = len(image_labels) == len(image_scores) and len(set(image_labels)) > 1
    img_auroc = auroc(image_scores, image_labels) if have_labels else None
    img_ap = average_precision(image_scores, image_labels) if have_labels else None
    auroc_ci = bootstrap_auroc_ci(image_scores, image_labels) if have_labels else None
    cls = classification_metrics(image_scores, image_labels, frozen.image_threshold) if have_labels else None

    subgroups_out = {}
    for k, groups in subgroup_scores.items():
        for gv, g in groups.items():
            if len(g["labels"]) >= 3 and len(set(g["labels"])) > 1:
                subgroups_out.setdefault(k, {})[gv] = {"n": len(g["labels"]), "auroc": auroc(g["scores"], g["labels"])}

    pixel_metrics = {"measured": False, "note": "not measured (no valid reference masks)"}
    if dices:
        pixel_metrics = {"measured": True, "mean_dice": round(sum(dices) / len(dices), 4),
                         "mean_iou": round(sum(ious) / len(ious), 4), "n_masked_images": len(dices)}

    return {
        "research_only": True,
        "clinical_promotion_eligible": False,
        "localizer": localizer.name,
        "backbone": getattr(localizer, "backbone", ""),
        "checkpoint_id": config.checkpoint_id,
        "synthetic_technical_test": synthetic_technical_test,
        # RGI-03: authoritative, checkpoint-derived scientific status.
        "scientifically_eligible": scientifically_eligible,
        "scientific_metrics_published": scientifically_eligible,
        "technical_test": technical_test,
        "n_fit_normal": len(fit_normals),
        "n_calibration_normal": len(calib_normals),
        "n_test": len(test_samples),
        "grouping_reliable": all_have_identity,
        "grouping_limitations": grouping_limitations,
        "frozen_threshold": frozen.to_dict(),
        "abstention": {"n_abstained": n_abstained, "rate": round(n_abstained / len(test_samples), 4) if test_samples else 0.0,
                       "margin": abstain_margin},
        "image_level_metrics": {
            "auroc": img_auroc, "auroc_ci95": auroc_ci, "average_precision": img_ap,
            "at_frozen_threshold": cls, "measured": have_labels,
            # RGI-03: metrics from a technical/non-scientific checkpoint are labelled as
            # such regardless of the caller's synthetic flag — never as model performance.
            "scientific": scientifically_eligible,
            "note": ("TECHNICAL test (non-scientific checkpoint or synthetic fixture) — "
                     "NOT model performance." if technical_test
                     else ("measured on provided labels" if have_labels else "not measured (no valid labels)")),
        },
        "pixel_level_metrics": pixel_metrics,
        "subgroup_metrics": subgroups_out or {"note": "not reported (insufficient per-subgroup samples)"},
        "latency_ms": {"per_image_mean": round(sum(latencies_ms) / len(latencies_ms), 3) if latencies_ms else None,
                       "n": len(latencies_ms)},
        "results": results,
        "config_fingerprint": config.fingerprint(),
        "note": "RESEARCH ONLY — uncalibrated spatial anomaly signals; not clinical performance; severity NOT inferred from scores.",
    }


def _outcome(exc: Exception, *, status: str, category: str) -> dict[str, Any]:
    return {
        "status": status, "category": category, "reason": f"{type(exc).__name__}: {exc}",
        "note": "No performance reported.",
    }


def compare_localizers(
    normal_samples: list[dict], test_samples: list[dict], *, config_factory: Callable[[str], Any],
    localizer_factories: dict[str, Callable[[], AnomalyLocalizer]], **kw,
) -> dict[str, Any]:
    """Run several localizers on identical authorized data.

    RGI-12: a failure is CLASSIFIED by its cause rather than all being mislabelled as a
    dependency ``blocked`` result — a missing dependency / unapproved checkpoint, a scientific-
    eligibility denial, data leakage, denied authorization, and invalid input / metric errors
    are distinct. Truly UNEXPECTED exceptions (bugs) are NOT suppressed — they propagate.
    """
    from research.lens_vision.provenance import ResearchProvenanceError  # noqa: PLC0415

    out: dict[str, Any] = {"research_only": True, "comparisons": {}}
    for name, factory in localizer_factories.items():
        try:
            localizer = factory()
            out["comparisons"][name] = run_anomaly_experiment(
                normal_samples, test_samples, config=config_factory(name), localizer=localizer, **kw,
            )
        except CheckpointScientificUseError as exc:
            out["comparisons"][name] = _outcome(exc, status="failed", category="scientific_eligibility_denied")
        except (CheckpointError, ImportError, ModuleNotFoundError) as exc:
            out["comparisons"][name] = _outcome(exc, status="blocked", category="dependency_or_checkpoint_unavailable")
        except LeakageError as exc:
            out["comparisons"][name] = _outcome(exc, status="failed", category="data_leakage")
        except ResearchProvenanceError as exc:
            out["comparisons"][name] = _outcome(exc, status="failed", category="authorization_denied")
        except (NormalOnlyViolation, InvalidLabelError, LocalizerConfigMismatchError) as exc:
            out["comparisons"][name] = _outcome(exc, status="failed", category="invalid_input")
        except ValueError as exc:  # remaining input/metric value errors (a known category)
            out["comparisons"][name] = _outcome(exc, status="failed", category="invalid_input_or_metric")
        # Any other exception type is a genuine, unexpected failure and is left to propagate.
    return out


def write_anomaly_model_card(path: str, config, report: dict) -> dict:
    import json  # noqa: PLC0415
    record = None
    try:
        record = get_record(config.checkpoint_id) if config.checkpoint_id else None
    except Exception:
        record = None
    card = {
        "banner": "RESEARCH ONLY — Stage 5B/5C anomaly localization. Uncalibrated spatial signals, not "
                  "clinically validated, not servable, not promotable. No clinical accuracy claimed.",
        "research_only": True,
        "clinical_promotion_eligible": False,
        "run": config.to_dict(),
        "config_fingerprint": config.fingerprint(),
        "checkpoint": {
            "id": config.checkpoint_id,
            "architecture": getattr(record, "architecture", "") if record else "",
            "digest_sha256": getattr(record, "expected_sha256", "") if record else "",
            "license": getattr(record, "license", "") if record else "",
            "status": ("approved" if (record and record.approved and record.rights_cleared)
                       else ("blocked" if record else "none")),
        },
        "report": report,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2, sort_keys=True, default=str)
    return card
