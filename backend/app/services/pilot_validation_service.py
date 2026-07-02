"""Phase 18 — Real-World Pilot Validation & Clinical Performance Study.

Computes clinical performance metrics, zone performance, the safety review
queue, the validation report, and the go/no-go gate from the
``pilot_validation_cases`` ground-truth table. Every number here is derived
from real rows in that table — nothing is fabricated. With zero cases, rates
are returned as ``None`` rather than a misleading 0.0.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.pilot_validation import PilotValidationCase

CRITICAL_FINDING_TYPES: list[str] = [
    "blood", "tissue", "organic_residue", "crack", "missing_component",
]

ZONE_TAXONOMY: list[str] = [
    "serrations", "grooves", "drill-bit flutes", "threaded regions",
    "o-ring areas", "rigid scope ports", "lumens", "box locks",
    "hinges", "ratchets", "insulation edges",
]

HIGH_RISK_ZONES: set[str] = set(ZONE_TAXONOMY)

# Readiness thresholds (Section 9 — Go/No-Go criteria).
CRITICAL_FN_RATE_THRESHOLD = 0.05
SUPERVISOR_AGREEMENT_THRESHOLD = 0.85

# High-confidence disagreement / low-confidence critical thresholds for the
# safety review queue (Section 7).
HIGH_CONFIDENCE_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.50


def derive_ground_truth_label(ai_prediction: bool | None, supervisor_finding: bool | None) -> str:
    """Confusion-matrix label from AI prediction vs. supervisor-confirmed finding.

    Always computed server-side — never accepted from the client — so the
    label can't be gamed by a caller submitting a pre-set value.
    """
    if ai_prediction is None or supervisor_finding is None:
        return "inconclusive"
    if ai_prediction and supervisor_finding:
        return "tp"
    if ai_prediction and not supervisor_finding:
        return "fp"
    if not ai_prediction and supervisor_finding:
        return "fn"
    return "tn"


def create_case(db: Session, tenant_id: str, payload) -> PilotValidationCase:
    label = derive_ground_truth_label(payload.ai_prediction, payload.supervisor_finding)
    is_critical = payload.finding_type in CRITICAL_FINDING_TYPES

    case = PilotValidationCase(
        tenant_id=tenant_id,
        inspection_id=payload.inspection_id,
        instrument_family=payload.instrument_family,
        manufacturer=payload.manufacturer,
        model=payload.model,
        anatomy_zone=payload.anatomy_zone,
        baseline_source=payload.baseline_source,
        has_baseline=payload.has_baseline,
        finding_type=payload.finding_type,
        severity=payload.severity,
        disposition=payload.final_disposition,
        ai_prediction=payload.ai_prediction,
        ai_confidence=payload.ai_confidence,
        ai_recommended_disposition=payload.ai_recommended_disposition,
        supervisor_finding=payload.supervisor_finding,
        supervisor_zone_correction=payload.supervisor_zone_correction,
        reviewer_name=payload.reviewer_name,
        reviewer_rationale=payload.reviewer_rationale,
        ground_truth_label=label,
        is_critical_finding=is_critical,
        dataset_version=payload.dataset_version,
        model_version=payload.model_version,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def list_cases(db: Session, tenant_id: str, limit: int = 500) -> list[PilotValidationCase]:
    return (
        db.query(PilotValidationCase)
        .filter(PilotValidationCase.tenant_id == tenant_id)
        .order_by(PilotValidationCase.created_at.desc())
        .limit(limit)
        .all()
    )


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def compute_confusion_counts(cases: list[PilotValidationCase]) -> dict:
    tp = sum(1 for c in cases if c.ground_truth_label == "tp")
    tn = sum(1 for c in cases if c.ground_truth_label == "tn")
    fp = sum(1 for c in cases if c.ground_truth_label == "fp")
    fn = sum(1 for c in cases if c.ground_truth_label == "fn")
    inconclusive = sum(1 for c in cases if c.ground_truth_label == "inconclusive")
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "inconclusive": inconclusive}


def compute_clinical_metrics(cases: list[PilotValidationCase]) -> dict:
    """Accuracy/precision/recall/F1/FPR/FNR/agreement/override/calibration."""
    counts = compute_confusion_counts(cases)
    tp, tn, fp, fn = counts["tp"], counts["tn"], counts["fp"], counts["fn"]
    adjudicated = tp + tn + fp + fn

    accuracy = _rate(tp + tn, adjudicated)
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = round(2 * precision * recall / (precision + recall), 4)
    false_positive_rate = _rate(fp, fp + tn)
    false_negative_rate = _rate(fn, fn + tp)

    # Supervisor agreement: fraction of adjudicated cases where the AI
    # prediction matched the supervisor's confirmed finding (TP + TN).
    supervisor_agreement_rate = _rate(tp + tn, adjudicated)

    overridden = sum(
        1 for c in cases
        if c.disposition and c.ai_recommended_disposition
        and c.disposition != c.ai_recommended_disposition
    )
    dispositioned = sum(1 for c in cases if c.disposition)
    override_rate = _rate(overridden, dispositioned)

    # Confidence calibration: bucket AI confidence into deciles and compare
    # the bucket's mean confidence to its observed accuracy (TP+TN rate).
    calibration = []
    scored = [c for c in cases if c.ground_truth_label in ("tp", "tn", "fp", "fn")]
    for lo in range(0, 100, 20):
        hi = lo + 20
        bucket = [c for c in scored if lo <= (c.ai_confidence or 0.0) * 100 < hi]
        if not bucket:
            continue
        correct = sum(1 for c in bucket if c.ground_truth_label in ("tp", "tn"))
        calibration.append({
            "confidence_range": f"{lo}-{hi}%",
            "case_count": len(bucket),
            "mean_confidence": round(sum(c.ai_confidence or 0.0 for c in bucket) / len(bucket), 4),
            "observed_accuracy": _rate(correct, len(bucket)),
        })

    return {
        "case_count": len(cases),
        "adjudicated_count": adjudicated,
        "inconclusive_count": counts["inconclusive"],
        "confusion_matrix": counts,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": false_positive_rate,
        "false_negative_rate": false_negative_rate,
        "supervisor_agreement_rate": supervisor_agreement_rate,
        "override_rate": override_rate,
        "confidence_calibration": calibration,
        "human_review_required": True,
    }


def compute_critical_safety_metrics(cases: list[PilotValidationCase]) -> dict:
    """False-negative rate per critical finding type — the safety headline metric."""
    by_type = {}
    for finding_type in CRITICAL_FINDING_TYPES:
        subset = [c for c in cases if c.finding_type == finding_type and c.ground_truth_label in ("tp", "fn")]
        fn = sum(1 for c in subset if c.ground_truth_label == "fn")
        tp = sum(1 for c in subset if c.ground_truth_label == "tp")
        by_type[finding_type] = {
            "false_negative_rate": _rate(fn, fn + tp),
            "false_negative_count": fn,
            "true_positive_count": tp,
            "sample_size": len(subset),
            "meets_safety_threshold": (
                _rate(fn, fn + tp) is None or _rate(fn, fn + tp) <= CRITICAL_FN_RATE_THRESHOLD
            ),
        }

    overall_critical = [c for c in cases if c.is_critical_finding and c.ground_truth_label in ("tp", "fn")]
    overall_fn = sum(1 for c in overall_critical if c.ground_truth_label == "fn")
    overall_tp = sum(1 for c in overall_critical if c.ground_truth_label == "tp")

    return {
        "by_finding_type": by_type,
        "overall_critical_false_negative_rate": _rate(overall_fn, overall_fn + overall_tp),
        "safety_threshold": CRITICAL_FN_RATE_THRESHOLD,
        "human_review_required": True,
        "note": (
            "Critical findings (blood, tissue, organic residue, crack, missing component) "
            "carry the highest patient-safety weight. False negatives here require quality "
            "review — possible association with reprocessing failure, not a clinical diagnosis."
        ),
    }


def compute_zone_performance(cases: list[PilotValidationCase]) -> list[dict]:
    """Per-zone performance: total, missed (FN), lowest-confidence, override rate."""
    zones = sorted({c.anatomy_zone for c in cases if c.anatomy_zone} | set())
    results = []
    for zone in zones:
        subset = [c for c in cases if c.anatomy_zone == zone]
        fn = sum(1 for c in subset if c.ground_truth_label == "fn")
        fp = sum(1 for c in subset if c.ground_truth_label == "fp")
        adjudicated = sum(1 for c in subset if c.ground_truth_label in ("tp", "tn", "fp", "fn"))
        correct = sum(1 for c in subset if c.ground_truth_label in ("tp", "tn"))
        overridden = sum(1 for c in subset if c.supervisor_zone_correction)
        confidences = [c.ai_confidence or 0.0 for c in subset]
        results.append({
            "zone": zone,
            "is_high_risk_zone": zone in HIGH_RISK_ZONES,
            "case_count": len(subset),
            "missed_count": fn,
            "false_positive_count": fp,
            "miss_rate": _rate(fn, adjudicated),
            "accuracy": _rate(correct, adjudicated),
            "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
            "override_count": overridden,
            "override_rate": _rate(overridden, len(subset)),
        })

    return sorted(results, key=lambda r: (r["missed_count"], -(r["mean_confidence"] or 0)), reverse=True)


def summarize_zone_extremes(zone_performance: list[dict]) -> dict:
    scored = [z for z in zone_performance if z["case_count"] > 0]
    return {
        "most_missed_zones": sorted(scored, key=lambda z: z["missed_count"], reverse=True)[:5],
        "highest_risk_zones": [z for z in scored if z["is_high_risk_zone"]][:11],
        "lowest_confidence_zones": sorted(
            [z for z in scored if z["mean_confidence"] is not None],
            key=lambda z: z["mean_confidence"],
        )[:5],
        "highest_override_zones": sorted(scored, key=lambda z: z["override_count"], reverse=True)[:5],
    }


def compute_dashboard(cases: list[PilotValidationCase]) -> dict:
    metrics = compute_clinical_metrics(cases)
    zone_perf = compute_zone_performance(cases)
    zone_extremes = summarize_zone_extremes(zone_perf)

    high_risk_findings = sum(1 for c in cases if c.is_critical_finding and c.ground_truth_label in ("tp", "fn"))
    inconclusive = sum(1 for c in cases if c.ground_truth_label == "inconclusive")

    family_perf: dict[str, dict] = {}
    for c in cases:
        fam = c.instrument_family or "unspecified"
        entry = family_perf.setdefault(fam, {"case_count": 0, "missed_count": 0, "correct_count": 0})
        entry["case_count"] += 1
        if c.ground_truth_label == "fn":
            entry["missed_count"] += 1
        if c.ground_truth_label in ("tp", "tn"):
            entry["correct_count"] += 1
    instrument_family_performance = [
        {
            "instrument_family": fam,
            "case_count": v["case_count"],
            "missed_count": v["missed_count"],
            "accuracy": _rate(v["correct_count"], v["case_count"]),
        }
        for fam, v in sorted(family_perf.items(), key=lambda kv: kv[1]["case_count"], reverse=True)
    ]

    # Confidence trend over time (oldest → newest), bucketed by insertion order.
    ordered = sorted(cases, key=lambda c: c.created_at or datetime.min.replace(tzinfo=timezone.utc))
    confidence_trend = [
        {"created_at": c.created_at.isoformat() if c.created_at else None, "ai_confidence": c.ai_confidence}
        for c in ordered
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_inspections_reviewed": len(cases),
        "ai_supervisor_agreement_rate": metrics["supervisor_agreement_rate"],
        "false_positives": metrics["confusion_matrix"]["fp"],
        "false_negatives": metrics["confusion_matrix"]["fn"],
        "high_risk_findings_detected": high_risk_findings,
        "inconclusive_cases": inconclusive,
        "model_confidence_trend": confidence_trend,
        "zone_performance": zone_perf,
        "zone_performance_summary": zone_extremes,
        "instrument_family_performance": instrument_family_performance,
        "clinical_metrics": metrics,
        "human_review_required": True,
    }


def build_safety_queue(cases: list[PilotValidationCase]) -> dict:
    """Section 7 — review queue for the highest-risk unresolved cases."""
    false_negatives = [c for c in cases if c.ground_truth_label == "fn"]
    high_confidence_disagreement = [
        c for c in cases
        if c.ground_truth_label in ("fp", "fn") and (c.ai_confidence or 0.0) >= HIGH_CONFIDENCE_THRESHOLD
    ]
    low_confidence_critical = [
        c for c in cases
        if c.is_critical_finding and (c.ai_confidence or 0.0) < LOW_CONFIDENCE_THRESHOLD
    ]
    missing_baseline = [c for c in cases if not c.has_baseline]
    missing_required_zones = [c for c in cases if not c.anatomy_zone or c.anatomy_zone not in ZONE_TAXONOMY]

    def _card(c: PilotValidationCase) -> dict:
        return {
            "id": c.id,
            "inspection_id": c.inspection_id,
            "instrument_family": c.instrument_family,
            "anatomy_zone": c.anatomy_zone,
            "finding_type": c.finding_type,
            "severity": c.severity,
            "ai_prediction": c.ai_prediction,
            "ai_confidence": c.ai_confidence,
            "supervisor_finding": c.supervisor_finding,
            "ground_truth_label": c.ground_truth_label,
            "is_critical_finding": c.is_critical_finding,
            "has_baseline": c.has_baseline,
            "reviewer_rationale": c.reviewer_rationale,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "false_negatives": {"count": len(false_negatives), "cases": [_card(c) for c in false_negatives]},
        "high_confidence_disagreement": {
            "count": len(high_confidence_disagreement),
            "cases": [_card(c) for c in high_confidence_disagreement],
        },
        "low_confidence_critical_findings": {
            "count": len(low_confidence_critical),
            "cases": [_card(c) for c in low_confidence_critical],
        },
        "missing_baseline_cases": {"count": len(missing_baseline), "cases": [_card(c) for c in missing_baseline]},
        "missing_required_zones": {
            "count": len(missing_required_zones),
            "cases": [_card(c) for c in missing_required_zones],
        },
        "critical_missed_findings": {
            "count": sum(1 for c in false_negatives if c.is_critical_finding),
            "cases": [_card(c) for c in false_negatives if c.is_critical_finding],
        },
        "human_review_required": True,
    }


def evaluate_go_no_go(cases: list[PilotValidationCase]) -> dict:
    """Section 9 — readiness gate for broader pilot expansion."""
    metrics = compute_clinical_metrics(cases)
    safety = compute_critical_safety_metrics(cases)

    critical_fn_rates = [
        v["false_negative_rate"] for v in safety["by_finding_type"].values()
        if v["false_negative_rate"] is not None
    ]
    critical_fn_ok = all(r <= CRITICAL_FN_RATE_THRESHOLD for r in critical_fn_rates)

    agreement = metrics["supervisor_agreement_rate"]
    agreement_ok = agreement is not None and agreement >= SUPERVISOR_AGREEMENT_THRESHOLD

    unresolved_critical = sum(
        1 for c in cases if c.is_critical_finding and c.ground_truth_label == "fn" and not c.disposition
    )

    reasons = []
    if not critical_fn_ok:
        reasons.append("Critical finding false-negative rate exceeds the safety threshold.")
    if not agreement_ok:
        reasons.append("Supervisor agreement rate is below the readiness threshold.")
    if unresolved_critical > 0:
        reasons.append(f"{unresolved_critical} critical missed finding(s) remain undispositioned.")
    if metrics["case_count"] < 1:
        reasons.append("No pilot cases have been reviewed yet.")

    decision = "GO" if not reasons else "NO-GO"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "reasons": reasons,
        "criteria": {
            "critical_false_negative_rate_ok": critical_fn_ok,
            "critical_false_negative_threshold": CRITICAL_FN_RATE_THRESHOLD,
            "supervisor_agreement_rate": agreement,
            "supervisor_agreement_threshold": SUPERVISOR_AGREEMENT_THRESHOLD,
            "supervisor_agreement_ok": agreement_ok,
            "unresolved_critical_safety_issues": unresolved_critical,
        },
        "human_review_required": True,
        "note": "Go/No-Go is a readiness signal for pilot expansion, not a regulatory or clinical determination.",
    }


def generate_validation_report(cases: list[PilotValidationCase]) -> dict:
    """Section 8 — Pilot Validation Report generator."""
    metrics = compute_clinical_metrics(cases)
    safety = compute_critical_safety_metrics(cases)
    zone_perf = compute_zone_performance(cases)
    go_no_go = evaluate_go_no_go(cases)

    instrument_families = sorted({c.instrument_family for c in cases if c.instrument_family})
    dataset_versions = sorted({c.dataset_version for c in cases if c.dataset_version})
    model_versions = sorted({c.model_version for c in cases if c.model_version})

    worst_zones = sorted(
        [z for z in zone_perf if z["case_count"] > 0],
        key=lambda z: z["missed_count"], reverse=True,
    )[:5]
    next_training_priorities = [
        f"Additional labeled examples for the '{z['zone']}' zone (missed {z['missed_count']} of {z['case_count']} cases)."
        for z in worst_zones if z["missed_count"] > 0
    ] or ["No zone currently exceeds the miss-rate threshold; continue routine data collection."]

    limitations = [
        "Sample size may be below the statistical threshold needed for tight confidence intervals.",
        "Zone assignment is instrument-type-derived, not pixel-level image localization.",
        "Findings are quality indicators requiring human review — not clinical diagnoses.",
        "Association between AI findings and reprocessing outcomes does not imply causation.",
    ]

    recommendations = []
    if go_no_go["decision"] == "GO":
        recommendations.append("Proceed to broader pilot expansion with continued safety-queue monitoring.")
    else:
        recommendations.append("Address the listed Go/No-Go blockers before expanding the pilot.")
    if next_training_priorities:
        recommendations.append("Prioritize model retraining on the zones listed in next_training_priorities.")

    return {
        "report_type": "pilot_validation_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "study_scope": {
            "total_cases_reviewed": len(cases),
            "instrument_families_reviewed": instrument_families,
            "zones_covered": sorted({c.anatomy_zone for c in cases if c.anatomy_zone}),
            "target_cases": 100,
        },
        "dataset_version": dataset_versions[-1] if dataset_versions else "pilot-v1",
        "model_version": model_versions[-1] if model_versions else "unknown",
        "results": {
            "clinical_performance_metrics": metrics,
            "critical_safety_metrics": safety,
            "zone_performance": zone_perf,
        },
        "safety_findings": build_safety_queue(cases),
        "limitations": limitations,
        "recommendations": recommendations,
        "next_training_priorities": next_training_priorities,
        "go_no_go": go_no_go,
        "human_review_required": True,
        "disclaimers": [
            "This report does not constitute FDA clearance or regulatory approval of any kind.",
            "All findings require sterile processing quality review before action.",
            "LumenAI never claims causation — findings are potential associations only.",
        ],
    }
