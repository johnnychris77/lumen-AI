"""Stage 5D — baseline-independent anomaly capability (research-only).

A manufacturer baseline image must NOT be required for standalone anomaly
detection. The Stage 5B/5C localizers fit on VERIFIED-NORMAL images and score a
single image, so they are inherently baseline-independent. A compatible, approved
manufacturer baseline may ENRICH the evidence (an extra comparison signal), but it
may never:

* overwrite or suppress an observed anomaly, or
* authorize instrument release.

This module makes that contract explicit and testable. It performs no clinical
inference and produces no disposition.
"""
from __future__ import annotations


class BaselineMisuseError(RuntimeError):
    """A manufacturer baseline was used to overwrite an anomaly or authorize release."""


def standalone_capable(localizer) -> bool:
    """True when a localizer can detect anomalies from a single image with no
    manufacturer baseline (it fits on verified-normal images and scores one image)."""
    return callable(getattr(localizer, "fit", None)) and callable(getattr(localizer, "score", None))


def combine_with_baseline(
    anomaly_result: dict, *, baseline_available: bool = False, baseline_comparison: dict | None = None,
) -> dict:
    """Return the anomaly result annotated with (optional) baseline ENRICHMENT.

    The image-only anomaly is authoritative. A baseline, when present and approved,
    is recorded as advisory enrichment only; it never changes the anomaly's
    presence/score and never authorizes release. Research-only invariants are
    preserved.
    """
    out = dict(anomaly_result)
    out["baseline_independent"] = True
    used = bool(baseline_available and baseline_comparison is not None)
    out["manufacturer_baseline_used"] = used
    if used:
        # Advisory enrichment — carried alongside, never overwriting the anomaly.
        out["baseline_enrichment"] = {
            "role": "advisory_enrichment_only",
            "comparison": dict(baseline_comparison),
            "may_overwrite_anomaly": False,
            "may_authorize_release": False,
        }
    # Hard invariants: a baseline can never suppress the anomaly or release the item.
    out["anomaly_overwritten_by_baseline"] = False
    out["authorizes_release"] = False
    out.setdefault("research_only", True)
    out.setdefault("human_review_required", True)
    out.setdefault("clinical_promotion_eligible", False)
    return out


def assert_baseline_not_authoritative(combined: dict) -> None:
    """Fail-closed check that a baseline did not overwrite the anomaly or authorize
    release. Raises :class:`BaselineMisuseError` if either invariant is violated."""
    if combined.get("anomaly_overwritten_by_baseline"):
        raise BaselineMisuseError("A manufacturer baseline overwrote an observed anomaly.")
    if combined.get("authorizes_release"):
        raise BaselineMisuseError("A manufacturer baseline/anomaly result authorized instrument release.")
