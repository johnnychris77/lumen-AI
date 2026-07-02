"""Phase 18 §4–§9 — Clinical performance metrics, zone/family performance,
safety review queue, go/no-go criteria, and the validation report.

Everything is computed from real supervisor reviews (ground-truth labels). No
projected or fabricated numbers: when there is no data, metrics are null and the
go/no-go decision is NO-GO/insufficient rather than an optimistic default.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.services.ml.ground_truth import (
    FALSE_NEGATIVE, FALSE_POSITIVE, INCONCLUSIVE, TRUE_NEGATIVE, TRUE_POSITIVE,
)
from app.services.ml.model_tasks import SAFETY_CRITICAL_FINDINGS

# High-retention zones surfaced in zone-performance (Phase 18 §5).
TRACKED_ZONES = [
    "serrations", "grooves", "drill-bit flute", "threaded region", "o-ring area",
    "rigid scope port", "lumen opening", "inner channel", "box lock", "hinge",
    "ratchet", "insulation edge", "biopsy channel", "suction channel",
]

# Go/No-Go thresholds (§9). Conservative defaults; documented in the report.
_MAX_SAFETY_FNR = 0.05          # critical-finding false-negative ceiling
_MIN_AGREEMENT_RATE = 0.80      # supervisor agreement floor
_MIN_REVIEWS = 30               # minimum reviewed inspections for a decision


def _safe_div(n: float, d: float) -> float | None:
    return round(n / d, 4) if d else None


def _zone_of(r) -> str:
    return (getattr(r, "corrected_zone", "") or getattr(r, "ai_zone", "") or "unspecified").lower()


def clinical_metrics(rows: list) -> dict[str, Any]:
    """§4 — accuracy/precision/recall/F1, FP/FN rates, agreement, override,
    confidence calibration, and safety-critical false-negative rates."""
    total = len(rows)
    counts = {TRUE_POSITIVE: 0, TRUE_NEGATIVE: 0, FALSE_POSITIVE: 0, FALSE_NEGATIVE: 0, INCONCLUSIVE: 0}
    for r in rows:
        counts[r.ground_truth if r.ground_truth in counts else INCONCLUSIVE] += 1

    tp, tn, fp, fn = counts[TRUE_POSITIVE], counts[TRUE_NEGATIVE], counts[FALSE_POSITIVE], counts[FALSE_NEGATIVE]
    agreed = sum(1 for r in rows if r.agreement == "agree")
    overrides = sum(1 for r in rows if (r.override_action or "").strip())

    return {
        "total_reviews": total,
        "counts": counts,
        "accuracy": _safe_div(tp + tn, tp + tn + fp + fn),
        "precision": _safe_div(tp, tp + fp),
        "recall": _safe_div(tp, tp + fn),
        "f1": _f1(_safe_div(tp, tp + fp), _safe_div(tp, tp + fn)),
        "false_positive_rate": _safe_div(fp, fp + tn),
        "false_negative_rate": _safe_div(fn, fn + tp),
        "supervisor_agreement_rate": _safe_div(agreed, total),
        "override_rate": _safe_div(overrides, total),
        "confidence_calibration": confidence_calibration(rows),
        "safety_metrics": safety_metrics(rows),
    }


def _f1(precision, recall):
    if precision is None or recall is None or (precision + recall) == 0:
        return None
    return round(2 * precision * recall / (precision + recall), 4)


def confidence_calibration(rows: list) -> dict[str, Any]:
    """Reliability by confidence band: predicted confidence vs realized accuracy.
    Only rows with a recorded ai_confidence and a decisive ground truth count."""
    bands = {"0.0-0.5": [], "0.5-0.7": [], "0.7-0.9": [], "0.9-1.0": []}
    decisive = {TRUE_POSITIVE, TRUE_NEGATIVE, FALSE_POSITIVE, FALSE_NEGATIVE}
    for r in rows:
        c = r.ai_confidence
        if c is None or r.ground_truth not in decisive:
            continue
        correct = r.ground_truth in (TRUE_POSITIVE, TRUE_NEGATIVE)
        key = "0.9-1.0" if c >= 0.9 else "0.7-0.9" if c >= 0.7 else "0.5-0.7" if c >= 0.5 else "0.0-0.5"
        bands[key].append(correct)
    return {
        band: {"n": len(hits), "accuracy": _safe_div(sum(hits), len(hits))}
        for band, hits in bands.items()
    }


def safety_metrics(rows: list) -> dict[str, Any]:
    """§4 critical safety metrics: false-negative rate per critical finding.
    FNR = missed / actually-present, computed from reviews of that finding."""
    out: dict[str, Any] = {}
    worst = None
    for finding in SAFETY_CRITICAL_FINDINGS:
        present = [r for r in rows if r.finding_type == finding and r.supervisor_finding_present]
        missed = sum(1 for r in present if r.ground_truth == FALSE_NEGATIVE)
        fnr = _safe_div(missed, len(present))
        out[f"{finding.replace(' ', '_')}_false_negative_rate"] = fnr
        if fnr is not None:
            worst = fnr if worst is None else max(worst, fnr)
    out["worst_safety_false_negative_rate"] = worst
    return out


def zone_performance(rows: list) -> dict[str, Any]:
    """§5 — per-zone counts + missed/override/confidence, plus the ranked views."""
    z: dict[str, dict] = defaultdict(lambda: {"n": 0, "missed": 0, "overrides": 0,
                                              "disagreements": 0, "conf_sum": 0.0, "conf_n": 0})
    for r in rows:
        zone = _zone_of(r)
        d = z[zone]
        d["n"] += 1
        if r.ground_truth == FALSE_NEGATIVE:
            d["missed"] += 1
        if (r.override_action or "").strip():
            d["overrides"] += 1
        if r.agreement and r.agreement != "agree":
            d["disagreements"] += 1
        if r.ai_confidence is not None:
            d["conf_sum"] += r.ai_confidence
            d["conf_n"] += 1

    zones = {
        zone: {
            "n": d["n"],
            "missed": d["missed"],
            "overrides": d["overrides"],
            "disagreements": d["disagreements"],
            "avg_confidence": _safe_div(d["conf_sum"], d["conf_n"]),
            "miss_rate": _safe_div(d["missed"], d["n"]),
        }
        for zone, d in z.items()
    }
    ranked = lambda key: [  # noqa: E731
        {"zone": zn, **v} for zn, v in sorted(zones.items(), key=lambda kv: kv[1][key], reverse=True)
        if v[key]
    ]
    lowest_conf = [
        {"zone": zn, **v} for zn, v in sorted(
            (kv for kv in zones.items() if kv[1]["avg_confidence"] is not None),
            key=lambda kv: kv[1]["avg_confidence"],
        )
    ]
    return {
        "by_zone": zones,
        "most_common_missed_zones": ranked("missed")[:10],
        "highest_override_zones": ranked("overrides")[:10],
        "highest_risk_zones": ranked("miss_rate")[:10],
        "lowest_confidence_zones": lowest_conf[:10],
    }


def family_performance(rows: list) -> dict[str, Any]:
    fam: dict[str, dict] = defaultdict(lambda: {"n": 0, "agreed": 0, "correct": 0})
    for r in rows:
        f = (r.instrument_family or "unknown").lower()
        fam[f]["n"] += 1
        if r.agreement == "agree":
            fam[f]["agreed"] += 1
        if r.ground_truth in (TRUE_POSITIVE, TRUE_NEGATIVE):
            fam[f]["correct"] += 1
    return {
        f: {
            "n": d["n"],
            "agreement_rate": _safe_div(d["agreed"], d["n"]),
            "accuracy": _safe_div(d["correct"], d["n"]),
        }
        for f, d in fam.items()
    }


def safety_review_queue(rows: list) -> list[dict]:
    """§7 — inspections that need a human safety look: false negatives,
    high-confidence AI/supervisor disagreements, and low-confidence critical
    findings."""
    queue = []
    for r in rows:
        reasons = []
        if r.ground_truth == FALSE_NEGATIVE:
            reasons.append("false_negative")
        if r.agreement and r.agreement != "agree" and (r.ai_confidence or 0) >= 0.8:
            reasons.append("high_confidence_disagreement")
        if r.finding_type in SAFETY_CRITICAL_FINDINGS and (r.ai_confidence is not None and r.ai_confidence < 0.6):
            reasons.append("low_confidence_critical_finding")
        if reasons:
            queue.append({
                "review_id": r.id,
                "inspection_id": r.inspection_id,
                "finding_type": r.finding_type,
                "zone": _zone_of(r),
                "instrument_family": r.instrument_family,
                "ground_truth": r.ground_truth,
                "ai_confidence": r.ai_confidence,
                "reasons": reasons,
            })
    # Most concerning first: false negatives, then disagreements.
    queue.sort(key=lambda q: (FALSE_NEGATIVE not in q["reasons"], -(q["ai_confidence"] or 0)))
    return queue


def go_no_go(rows: list) -> dict[str, Any]:
    """§9 — readiness gate from the current pilot evidence."""
    metrics = clinical_metrics(rows)
    total = metrics["total_reviews"]
    agreement = metrics["supervisor_agreement_rate"]
    worst_fnr = metrics["safety_metrics"]["worst_safety_false_negative_rate"]

    blocking: list[str] = []
    if total < _MIN_REVIEWS:
        blocking.append(f"Insufficient reviews ({total} < {_MIN_REVIEWS}).")
    if agreement is not None and agreement < _MIN_AGREEMENT_RATE:
        blocking.append(f"Supervisor agreement {agreement} below {_MIN_AGREEMENT_RATE}.")
    if worst_fnr is not None and worst_fnr > _MAX_SAFETY_FNR:
        blocking.append(f"Safety false-negative rate {worst_fnr} exceeds {_MAX_SAFETY_FNR}.")

    decision = "GO" if not blocking and total >= _MIN_REVIEWS else "NO-GO"
    return {
        "decision": decision,
        "blocking_issues": blocking,
        "thresholds": {
            "max_safety_false_negative_rate": _MAX_SAFETY_FNR,
            "min_supervisor_agreement_rate": _MIN_AGREEMENT_RATE,
            "min_reviews": _MIN_REVIEWS,
        },
        "measured": {
            "total_reviews": total,
            "supervisor_agreement_rate": agreement,
            "worst_safety_false_negative_rate": worst_fnr,
        },
        "human_review_required": True,
        "note": "Advisory readiness gate from real pilot reviews; a human owns the final decision.",
    }


def dashboard(rows: list) -> dict[str, Any]:
    """§6 — the pilot performance dashboard payload."""
    metrics = clinical_metrics(rows)
    counts = metrics["counts"]
    high_risk_detected = sum(
        1 for r in rows
        if r.finding_type in SAFETY_CRITICAL_FINDINGS and r.ground_truth == TRUE_POSITIVE
    )
    return {
        "total_inspections_reviewed": metrics["total_reviews"],
        "ai_supervisor_agreement_rate": metrics["supervisor_agreement_rate"],
        "false_positives": counts[FALSE_POSITIVE],
        "false_negatives": counts[FALSE_NEGATIVE],
        "high_risk_findings_detected": high_risk_detected,
        "inconclusive_cases": counts[INCONCLUSIVE],
        "override_rate": metrics["override_rate"],
        "confidence_calibration": metrics["confidence_calibration"],
        "safety_metrics": metrics["safety_metrics"],
        "zone_performance": zone_performance(rows),
        "instrument_family_performance": family_performance(rows),
        "clinical_metrics": metrics,
        "human_review_required": True,
    }


def validation_report(rows: list, *, dataset_version: str, model_version: str,
                      model_id: str = "") -> dict[str, Any]:
    """§8 — structured Pilot Validation Report including dataset/model version."""
    metrics = clinical_metrics(rows)
    gng = go_no_go(rows)
    families = sorted({(r.instrument_family or "unknown") for r in rows})
    return {
        "report_type": "pilot_validation",
        "study_scope": "Real-world SPD pilot: AI-assisted inspection vs trained supervisor ground truth.",
        "instruments_reviewed": metrics["total_reviews"],
        "instrument_families": families,
        "dataset_version": dataset_version,
        "model_id": model_id,
        "model_version": model_version,
        "results": metrics,
        "zone_performance": zone_performance(rows),
        "safety_findings": {
            "safety_metrics": metrics["safety_metrics"],
            "safety_queue_size": len(safety_review_queue(rows)),
        },
        "go_no_go": gng,
        "limitations": [
            "Pilot-scale sample; not a validated production model.",
            "Zone assignment is pilot logic (not CV segmentation).",
            "Ground truth is single-supervisor per review unless adjudicated.",
        ],
        "recommendations": _recommendations(gng, metrics),
        "next_training_priorities": _next_priorities(rows),
        "human_review_required": True,
        "regulatory_note": "No claim of FDA clearance or regulatory approval.",
    }


def _recommendations(gng: dict, metrics: dict) -> list[str]:
    if gng["decision"] == "GO":
        return ["Evidence supports expanding the pilot; continue shadow validation on new sites."]
    recs = ["Do not expand until blocking issues are resolved:"]
    recs.extend(gng["blocking_issues"])
    return recs


def _next_priorities(rows: list) -> list[str]:
    """Rank the safety-critical findings by measured false-negative rate."""
    sm = safety_metrics(rows)
    scored = [
        (k.replace("_false_negative_rate", "").replace("_", " "), v)
        for k, v in sm.items() if k.endswith("_false_negative_rate") and v
    ]
    scored.sort(key=lambda kv: kv[1], reverse=True)
    return [f"Improve {name} detection (FNR {rate})." for name, rate in scored[:5]] or [
        "Collect more labeled examples across all critical findings and high-retention zones."
    ]
