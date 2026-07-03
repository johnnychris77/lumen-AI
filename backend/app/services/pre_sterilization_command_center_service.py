"""Pre-Sterilization Command Center — readiness scoring, queues, and the
executive risk rollup.

Answers, from real Inspection/SupervisorReview/BaselineLibraryEntry/
PilotValidationCase rows — never fabricated: "are these instruments
clinically ready to move forward to packaging and sterilization, and if
not, why not, where, and what should SPD do next?"

Terminology discipline (see docs/architecture/pre-sterilization-boundary.md):
this module reports pre-sterilization/packaging *readiness*, never
sterilization validation or biological-indicator monitoring — LumenAI
operates before packaging and sterilization, not inside them.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.baseline_library import BaselineLibraryEntry
from app.models.supervisor_review import SupervisorReview
from app.services.inspection_coverage import compute_coverage

# ---------------------------------------------------------------------------
# Readiness states — sub-classifications of the frozen five-value decision
# engine (see docs/architecture/lumenai-clinical-intelligence-architecture.md
# Layer 7). REQUIRES_REPAIR / REMOVED_FROM_SERVICE are a sub-field on top of
# the existing "REMOVE FROM SERVICE" outcome, not a new engine value.
# ---------------------------------------------------------------------------
READY_FOR_PACKAGING = "READY_FOR_PACKAGING"
REQUIRES_RECLEANING = "REQUIRES_RECLEANING"
REQUIRES_SUPERVISOR_REVIEW = "REQUIRES_SUPERVISOR_REVIEW"
REQUIRES_REPAIR = "REQUIRES_REPAIR"
REMOVED_FROM_SERVICE = "REMOVED_FROM_SERVICE"
PENDING_ANALYSIS = "PENDING_ANALYSIS"

# Higher = more blocking. Used to pick the weakest link for a tray.
_STATE_SEVERITY = {
    READY_FOR_PACKAGING: 0,
    PENDING_ANALYSIS: 1,
    REQUIRES_SUPERVISOR_REVIEW: 2,
    REQUIRES_RECLEANING: 3,
    REQUIRES_REPAIR: 4,
    REMOVED_FROM_SERVICE: 5,
}

# Structural defects a repair shop can plausibly fix — everything else that
# reaches "remove from service" (contamination that escalated, or an
# unrepairable structural failure) is retired rather than queued for repair.
_REPAIRABLE_ISSUES = {"crack", "corrosion", "insulation_damage"}
_CONTAMINATION_ISSUES = {"blood", "bone", "tissue", "debris", "other"}
# High-risk findings per the Inspection.detected_issue taxonomy (narrower than
# Phase 18's ground-truth taxonomy, which also tracks organic_residue /
# missing_component as PilotValidationCase.finding_type values).
CRITICAL_ISSUES = {"blood", "tissue", "bone", "crack", "insulation_damage"}


def classify_readiness(insp) -> dict:
    """Derive the pre-sterilization readiness state for one inspection.

    Prefers the deterministic `recommended_action` sentence persisted by the
    scoring engine (starts with "Pass —" / "Monitor —" / "Supervisor review
    ... —" / "Reprocess —" / "Remove from service —"). Falls back to
    detected_issue + risk signal for manual/no-image entries that never ran
    through the scoring engine.
    """
    action_text = (insp.recommended_action or "").strip().lower()
    detected_issue = (insp.detected_issue or "").strip().lower()
    repair_candidate = False

    if insp.score_status != "scored":
        state = PENDING_ANALYSIS
    elif action_text.startswith("remove from service"):
        repair_candidate = detected_issue in _REPAIRABLE_ISSUES
        state = REQUIRES_REPAIR if repair_candidate else REMOVED_FROM_SERVICE
    elif action_text.startswith("reprocess"):
        state = REQUIRES_RECLEANING
    elif action_text.startswith("supervisor review"):
        state = REQUIRES_SUPERVISOR_REVIEW
    elif action_text.startswith("monitor") or action_text.startswith("pass"):
        state = READY_FOR_PACKAGING
    elif action_text:
        state = REQUIRES_SUPERVISOR_REVIEW  # unrecognized text — fail safe to human review
    elif insp.supervisor_review_required:
        state = REQUIRES_SUPERVISOR_REVIEW
    elif detected_issue in ("", "none", "unknown") and not insp.stain_detected:
        state = READY_FOR_PACKAGING
    elif detected_issue in _REPAIRABLE_ISSUES:
        repair_candidate = True
        state = REQUIRES_REPAIR if (insp.risk_score or 0) >= 70 else REQUIRES_SUPERVISOR_REVIEW
    elif detected_issue in _CONTAMINATION_ISSUES or insp.stain_detected:
        state = REQUIRES_RECLEANING
    else:
        state = REQUIRES_SUPERVISOR_REVIEW

    readiness_score = (100 - insp.risk_score) if insp.score_status == "scored" and insp.risk_score is not None else None

    return {
        "readiness_state": state,
        "readiness_score": readiness_score,
        "repair_candidate": repair_candidate,
        "is_critical_finding": detected_issue in CRITICAL_ISSUES,
    }


def _is_confirmed(insp, reviewed_inspection_ids: set[int]) -> bool:
    return (
        insp.qa_review_status in ("approved", "overridden")
        or insp.status in ("reviewed", "closed")
        or insp.id in reviewed_inspection_ids
    )


def _instrument_identity(insp) -> str:
    """Group key for a physical instrument. Falls back to a per-inspection key
    when no barcode/UDI was captured — we can't claim re-identification we
    didn't actually perform."""
    if insp.instrument_barcode:
        return f"barcode:{insp.instrument_barcode}"
    if insp.instrument_udi:
        return f"udi:{insp.instrument_udi}"
    return f"untracked:{insp.instrument_type}:{insp.id}"


def _reviewed_ids(db: Session, tenant_id: str) -> set[int]:
    rows = db.query(SupervisorReview.inspection_id).filter(SupervisorReview.tenant_id == tenant_id).all()
    return {r[0] for r in rows}


def _annotate(cases: list, reviewed_ids: set[int]) -> list[dict]:
    """One classified record per inspection, newest first."""
    annotated = []
    for insp in cases:
        c = classify_readiness(insp)
        c["inspection"] = insp
        c["confirmed"] = _is_confirmed(insp, reviewed_ids)
        annotated.append(c)
    return annotated


# ---------------------------------------------------------------------------
# Module 1 — Clinical Inspection Readiness Score
# ---------------------------------------------------------------------------

def clinical_inspection_readiness(annotated: list[dict]) -> dict:
    total = len(annotated)
    by_state = {state: 0 for state in _STATE_SEVERITY}
    scores = []
    for a in annotated:
        by_state[a["readiness_state"]] += 1
        if a["readiness_score"] is not None:
            scores.append(a["readiness_score"])

    ready = by_state[READY_FOR_PACKAGING]
    return {
        "total_inspections": total,
        "ready_for_packaging": ready,
        "readiness_rate": round(ready / total, 4) if total else None,
        "mean_readiness_score": round(sum(scores) / len(scores), 2) if scores else None,
        "by_state": by_state,
        "human_review_required": True,
    }


# ---------------------------------------------------------------------------
# Module 2 — Tray Readiness Score
# ---------------------------------------------------------------------------

def tray_readiness(annotated: list[dict]) -> list[dict]:
    by_tray: dict[str, dict[str, dict]] = defaultdict(dict)
    for a in annotated:
        insp = a["inspection"]
        tray_id = (insp.tray_id or "").strip()
        if not tray_id:
            continue
        identity = _instrument_identity(insp)
        existing = by_tray[tray_id].get(identity)
        if existing is None or insp.created_at > existing["inspection"].created_at:
            by_tray[tray_id][identity] = a

    results = []
    for tray_id, instruments in by_tray.items():
        states = [a["readiness_state"] for a in instruments.values()]
        worst = max(states, key=lambda s: _STATE_SEVERITY[s])
        blocking = [
            {"instrument_type": a["inspection"].instrument_type, "readiness_state": a["readiness_state"]}
            for a in instruments.values() if a["readiness_state"] == worst
        ] if worst != READY_FOR_PACKAGING else []
        results.append({
            "tray_id": tray_id,
            "instrument_count": len(instruments),
            "tray_readiness_state": worst,
            "ready_for_packaging": worst == READY_FOR_PACKAGING,
            "blocking_instruments": blocking,
        })
    return sorted(results, key=lambda r: _STATE_SEVERITY[r["tray_readiness_state"]], reverse=True)


# ---------------------------------------------------------------------------
# Module 3 — Instrument Readiness Score
# ---------------------------------------------------------------------------

def instrument_readiness(annotated: list[dict]) -> list[dict]:
    by_instrument: dict[str, dict] = {}
    for a in annotated:
        insp = a["inspection"]
        identity = _instrument_identity(insp)
        existing = by_instrument.get(identity)
        if existing is None or insp.created_at > existing["inspection"].created_at:
            by_instrument[identity] = a

    results = []
    for identity, a in by_instrument.items():
        insp = a["inspection"]
        results.append({
            "instrument_identity": identity,
            "instrument_type": insp.instrument_type,
            "tray_id": insp.tray_id,
            "readiness_state": a["readiness_state"],
            "readiness_score": a["readiness_score"],
            "confirmed": a["confirmed"],
            "last_inspected_at": insp.created_at.isoformat() if insp.created_at else None,
        })
    return sorted(results, key=lambda r: _STATE_SEVERITY[r["readiness_state"]], reverse=True)


# ---------------------------------------------------------------------------
# Module 4 — Facility Readiness Score
# ---------------------------------------------------------------------------

def facility_readiness(annotated: list[dict]) -> list[dict]:
    by_facility: dict[str, list[dict]] = defaultdict(list)
    for a in annotated:
        insp = a["inspection"]
        facility = (insp.facility_name or insp.site_name or "unspecified").strip() or "unspecified"
        by_facility[facility].append(a)

    results = []
    for facility, items in by_facility.items():
        ordered = sorted(items, key=lambda a: a["inspection"].created_at or datetime.min.replace(tzinfo=timezone.utc))
        mid = len(ordered) // 2
        older, newer = ordered[:mid], ordered[mid:]

        def _rate(bucket):
            if not bucket:
                return None
            ready = sum(1 for a in bucket if a["readiness_state"] == READY_FOR_PACKAGING)
            return round(ready / len(bucket), 4)

        older_rate, newer_rate = _rate(older), _rate(newer)
        if older_rate is None or newer_rate is None:
            trend = "insufficient_data"
        elif newer_rate > older_rate:
            trend = "improving"
        elif newer_rate < older_rate:
            trend = "declining"
        else:
            trend = "stable"

        by_state = {state: 0 for state in _STATE_SEVERITY}
        for a in items:
            by_state[a["readiness_state"]] += 1

        results.append({
            "facility": facility,
            "total_inspections": len(items),
            "readiness_rate": _rate(items),
            "trend": trend,
            "by_state": by_state,
        })
    return sorted(results, key=lambda r: r["readiness_rate"] if r["readiness_rate"] is not None else 0)


# ---------------------------------------------------------------------------
# Module 5 — High-Risk Findings Queue
# ---------------------------------------------------------------------------

def high_risk_findings_queue(annotated: list[dict]) -> list[dict]:
    items = [
        a for a in annotated
        if a["is_critical_finding"] and not a["confirmed"]
        and a["readiness_state"] != READY_FOR_PACKAGING
    ]
    items.sort(key=lambda a: a["inspection"].risk_score or 0, reverse=True)
    return [
        {
            "inspection_id": a["inspection"].id,
            "instrument_type": a["inspection"].instrument_type,
            "detected_issue": a["inspection"].detected_issue,
            "readiness_state": a["readiness_state"],
            "risk_score": a["inspection"].risk_score,
            "facility": a["inspection"].facility_name or a["inspection"].site_name,
            "tray_id": a["inspection"].tray_id,
            "created_at": a["inspection"].created_at.isoformat() if a["inspection"].created_at else None,
        }
        for a in items
    ]


# ---------------------------------------------------------------------------
# Module 6 — Supervisor Review Queue
# ---------------------------------------------------------------------------

def supervisor_review_queue(annotated: list[dict]) -> list[dict]:
    items = [
        a for a in annotated
        if (a["readiness_state"] == REQUIRES_SUPERVISOR_REVIEW or a["inspection"].supervisor_review_required)
        and not a["confirmed"]
    ]
    return [
        {
            "inspection_id": a["inspection"].id,
            "instrument_type": a["inspection"].instrument_type,
            "detected_issue": a["inspection"].detected_issue,
            "recommended_action": a["inspection"].recommended_action,
            "risk_score": a["inspection"].risk_score,
            "created_at": a["inspection"].created_at.isoformat() if a["inspection"].created_at else None,
        }
        for a in items
    ]


# ---------------------------------------------------------------------------
# Module 7 — Missing Anatomy Zone Coverage
# ---------------------------------------------------------------------------

def missing_zone_coverage_queue(cases: list) -> list[dict]:
    items = []
    for insp in cases:
        if not insp.has_image:
            continue
        try:
            inspected = json.loads(insp.inspected_zones_json or "null")
        except (TypeError, ValueError):
            inspected = None
        coverage = compute_coverage(insp.instrument_type, inspected)
        if coverage["quality"] in ("not_assessed", "incomplete", "insufficient"):
            items.append({
                "inspection_id": insp.id,
                "instrument_type": insp.instrument_type,
                "coverage_quality": coverage["quality"],
                "overall_coverage": coverage["overall_coverage"],
                "missing_required_zones": coverage["missing"],
                "created_at": insp.created_at.isoformat() if insp.created_at else None,
            })
    return items


# ---------------------------------------------------------------------------
# Module 8 — Baseline Coverage
# ---------------------------------------------------------------------------

def baseline_coverage(db: Session, tenant_id: str, cases: list) -> dict:
    imaged = [c for c in cases if c.has_image]
    total = len(imaged)
    with_baseline = sum(1 for c in imaged if c.baseline_status == "approved_baseline_found")

    gaps: dict[str, int] = defaultdict(int)
    for c in imaged:
        if c.baseline_status != "approved_baseline_found":
            gaps[c.instrument_type] += 1

    approved_categories = {
        row[0] for row in db.query(BaselineLibraryEntry.instrument_category)
        .filter(BaselineLibraryEntry.approval_status == "approved").distinct().all()
    }

    return {
        "total_imaged_inspections": total,
        "with_approved_baseline": with_baseline,
        "baseline_coverage_rate": round(with_baseline / total, 4) if total else None,
        "instrument_types_missing_baseline": [
            {"instrument_type": t, "inspection_count": n} for t, n in sorted(gaps.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "instrument_categories_with_approved_baseline": sorted(approved_categories),
        "human_review_required": True,
    }


# ---------------------------------------------------------------------------
# Module 9 — Repair / Remove From Service Queue
# ---------------------------------------------------------------------------

def repair_remove_queue(annotated: list[dict]) -> dict:
    def _card(a):
        insp = a["inspection"]
        return {
            "inspection_id": insp.id,
            "instrument_type": insp.instrument_type,
            "detected_issue": insp.detected_issue,
            "risk_score": insp.risk_score,
            "facility": insp.facility_name or insp.site_name,
            "created_at": insp.created_at.isoformat() if insp.created_at else None,
        }

    repair = [a for a in annotated if a["readiness_state"] == REQUIRES_REPAIR]
    removed = [a for a in annotated if a["readiness_state"] == REMOVED_FROM_SERVICE]
    return {
        "repair_candidates": {"count": len(repair), "cases": [_card(a) for a in repair]},
        "removed_from_service": {"count": len(removed), "cases": [_card(a) for a in removed]},
    }


# ---------------------------------------------------------------------------
# Module 10 — Executive Risk Dashboard
# ---------------------------------------------------------------------------

def executive_risk_dashboard(db: Session, tenant_id: str, cases: list, annotated: list[dict]) -> dict:
    from app.services.pilot_validation_service import compute_zone_performance, list_cases as list_pilot_cases

    readiness = clinical_inspection_readiness(annotated)
    repair_remove = repair_remove_queue(annotated)
    facilities = facility_readiness(annotated)
    baseline = baseline_coverage(db, tenant_id, cases)

    pilot_cases = list_pilot_cases(db, tenant_id, limit=5000)
    zone_performance = compute_zone_performance(pilot_cases)
    worst_zones = sorted(
        [z for z in zone_performance if z["case_count"] > 0], key=lambda z: z["missed_count"], reverse=True
    )[:5]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "readiness_summary": readiness,
        "high_risk_findings_count": len(high_risk_findings_queue(annotated)),
        "supervisor_review_backlog": len(supervisor_review_queue(annotated)),
        "repair_candidates_count": repair_remove["repair_candidates"]["count"],
        "removed_from_service_count": repair_remove["removed_from_service"]["count"],
        "baseline_coverage_rate": baseline["baseline_coverage_rate"],
        "instrument_types_missing_baseline": len(baseline["instrument_types_missing_baseline"]),
        "facility_rollup": facilities,
        "anatomy_zone_failure_trend": worst_zones,
        "human_review_required": True,
        "disclaimers": [
            "These figures are pre-sterilization quality indicators, not sterilization validation.",
            "All escalations require SPD supervisor review before disposition.",
            "Association does not imply causation.",
        ],
    }
