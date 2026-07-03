"""Phase 23 §1 — Clinical Intelligence Orchestrator.

The single coordination point for the Clinical Intelligence Operating
System. No module communicates directly with another — everything flows
through here. This wraps (does not duplicate) the Phase 22 multi-agent
pipeline (app/agents/orchestrator.py::run_pipeline) and adds the CIOS
layer on top of it: the unified immutable Clinical Context, the pipeline
monitor, the inspection state, the explainable timeline, real event
emission, and a Decision Ledger entry for the AI's recommendation.

Failure handling: if the underlying agent pipeline raises, this function
lets the exception propagate (a 500 at the API layer) rather than
returning a partial or fabricated result — the same "fail loudly, never
fabricate" rule documented in docs/agents/agent-orchestrator.md.
"""
from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_pipeline
from app.cios import event_bus
from app.cios.context import ClinicalContext
from app.cios.decision_ledger import record_decision
from app.cios.governance import governance_snapshot
from app.cios.state_machine import derive_state
from app.models.clinical_decision_ledger import ClinicalDecisionLedgerEntry
from app.models.supervisor_review import SupervisorReview

# Phase 22 pipeline order, relabeled to the Section 3 Pipeline Monitor's
# short display names.
_MONITOR_STEPS = [
    ("Instrument Agent", "instrument_context"),
    ("Anatomy Agent", "anatomy_context"),
    ("Coverage Agent", "coverage_context"),
    ("Contamination Agent", "contamination_context"),
    ("Damage Agent", "damage_context"),
    ("Clinical Reasoning Agent", "clinical_reasoning_context"),
    ("Recommendation Agent", "recommendation_context"),
    ("Supervisor Agent", "supervisor_context"),
    ("Learning Agent", "learning_context"),
    ("Enterprise Agent", "enterprise_context"),
]


def _pipeline_monitor(result: dict) -> list[dict]:
    """Section 3 — Complete / Pending / Queued per agent.

    Every deterministic agent (Instrument .. Recommendation) is Complete
    once it has run. Supervisor is Complete only if a real human review
    exists, else Pending. Learning/Enterprise are Queued while Supervisor
    is still Pending — this inspection hasn't contributed its learning
    signal yet, even though the aggregate confidence numbers they report
    are already computed from *other* reviewed inspections.
    """
    supervisor_done = result["supervisor_context"]["review_exists"]
    monitor = []
    for label, key in _MONITOR_STEPS:
        if label == "Supervisor Agent":
            status = "Complete" if supervisor_done else "Pending"
        elif label in ("Learning Agent", "Enterprise Agent"):
            status = "Complete" if supervisor_done else "Queued"
        else:
            status = "Complete"
        monitor.append({"agent": label, "status": status})
    return monitor


def _build_clinical_context(inspection, tenant_id: str, result: dict) -> ClinicalContext:
    return ClinicalContext(
        inspection_id=inspection.id,
        tenant_id=tenant_id,
        instrument_type=result["instrument_context"]["instrument_type"],
        manufacturer=result["instrument_context"]["manufacturer"],
        model=result["instrument_context"]["model"],
        instrument_family=result["instrument_context"]["instrument_family"],
        anatomy_profile=result["anatomy_context"],
        inspection_zones=result["anatomy_context"]["anatomy_zones"],
        coverage=result["coverage_context"],
        baseline={"baseline_status": inspection.baseline_status, "baseline_source": inspection.baseline_source},
        findings=result["contamination_context"]["findings"] + result["damage_context"]["findings"],
        severity=(result["contamination_context"]["findings"] or result["damage_context"]["findings"] or [{}])[0].get("severity"),
        risk={"risk_level": result["clinical_reasoning_context"]["risk_level"], "risk_score": result["clinical_reasoning_context"]["risk_score"]},
        recommendation=result["recommendation_context"],
        supervisor_review=result["supervisor_context"],
        digital_twin={"available": result["instrument_context"]["digital_twin_available"]},
        knowledge_graph_links={"reasoning_chain": result["clinical_reasoning_context"]["reasoning_chain"]},
        audit={"governance": governance_snapshot()},
    )


def _emit_events(db: Session, tenant_id: str, inspection, result: dict) -> list[dict]:
    emitted = []

    def _emit(event_type: str, payload: dict | None = None):
        row = event_bus.emit(db, tenant_id, event_type, inspection.id, payload)
        emitted.append({"event_type": row.event_type, "id": row.id})

    _emit("InspectionStarted", {"instrument_type": inspection.instrument_type})
    if inspection.baseline_status == "approved_baseline_found":
        _emit("BaselineLoaded", {"baseline_source": inspection.baseline_source})
    if result["coverage_context"]["coverage_quality"] in ("incomplete", "insufficient", "not_assessed"):
        _emit("CoverageIncomplete", {"coverage_quality": result["coverage_context"]["coverage_quality"]})
    for f in result["contamination_context"]["findings"]:
        if f["finding_type"] == "blood":
            _emit("BloodDetected", {"zone": f["zone"], "severity": f["severity"]})
    for f in result["damage_context"]["findings"]:
        if f["finding_type"] == "corrosion":
            _emit("CorrosionDetected", {"severity": f["severity"]})
    _emit("RecommendationGenerated", {"readiness_state": result["recommendation_context"]["readiness_state"]})

    supervisor = result["supervisor_context"]
    if supervisor["review_exists"] and supervisor["agreement"] in ("agree", "partially_agree") and not supervisor["override_action"]:
        _emit("SupervisorApproved", {"agreement": supervisor["agreement"]})
    if result["recommendation_context"]["readiness_state"] == "REMOVED_FROM_SERVICE":
        _emit("InstrumentRemovedFromService", {"instrument_type": inspection.instrument_type})
    if supervisor["training_label_created"]:
        _emit("ModelFeedbackCaptured", {"ground_truth_label": supervisor["ground_truth_label"]})

    return emitted


def _timeline(inspection, result: dict, review) -> list[dict]:
    """Section 7 — real timestamps only. Steps that happen synchronously
    inside one scoring call (image capture through recommendation) are
    reported at the trace entries' real (very close together) execution
    times; the supervisor step uses the real SupervisorReview timestamp,
    which can be genuinely minutes or hours after the AI steps."""
    events = [{
        "timestamp": inspection.created_at.isoformat() if inspection.created_at else None,
        "label": f"Inspection created — {inspection.instrument_type} image captured.",
    }]
    for entry in result["trace"]:
        events.append({"timestamp": entry["timestamp"], "label": f"{entry['agent']} completed."})
    if review is not None:
        events.append({
            "timestamp": review.created_at.astimezone(timezone.utc).isoformat() if review.created_at else None,
            "label": f"Supervisor {review.agreement}" + (f" (override: {review.override_action})" if review.override_action else ""),
        })
    return events


def run_cios_pipeline(db: Session, inspection, tenant_id: str) -> dict:
    """Section 1 — the single entry point every consumer (API, dashboard,
    certificate generator) should call. Runs the full Phase 22 agent
    pipeline, then assembles the CIOS layer on top of it."""
    result = run_pipeline(db, inspection, tenant_id)

    review = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.inspection_id == inspection.id)
        .order_by(SupervisorReview.id.desc())
        .first()
    )

    clinical_context = _build_clinical_context(inspection, tenant_id, result)
    monitor = _pipeline_monitor(result)
    state = derive_state(inspection, review)
    timeline = _timeline(inspection, result, review)

    # This is called from GET/read endpoints (dashboard refresh, certificate
    # download) as well as the initial run — event emission and the decision
    # ledger are permanent audit stores with no dedup, so only emit/record the
    # AI's recommendation once per inspection. Subsequent calls return the
    # already-recorded events/ledger entry rather than appending duplicates.
    existing_decision = (
        db.query(ClinicalDecisionLedgerEntry)
        .filter(
            ClinicalDecisionLedgerEntry.tenant_id == tenant_id,
            ClinicalDecisionLedgerEntry.inspection_id == inspection.id,
            ClinicalDecisionLedgerEntry.decision_type == "ai_recommendation",
        )
        .order_by(ClinicalDecisionLedgerEntry.id.asc())
        .first()
    )
    if existing_decision is None:
        events = _emit_events(db, tenant_id, inspection, result)
        ledger_entry = record_decision(
            db, tenant_id, inspection.id,
            decision_type="ai_recommendation",
            made_by="ai",
            rationale=result["recommendation_context"]["explanation"],
            evidence={"reasoning_chain": result["clinical_reasoning_context"]["reasoning_chain"]},
            confidence=inspection.confidence,
        )
    else:
        events = event_bus.list_events(db, tenant_id, inspection.id, limit=500)
        ledger_entry = existing_decision

    return {
        "inspection_id": inspection.id,
        "clinical_context": clinical_context.model_dump(),
        "pipeline_monitor": monitor,
        "inspection_state": state,
        "timeline": timeline,
        "events_emitted": events,
        "decision_ledger_entry_id": ledger_entry.id,
        "governance": governance_snapshot(),
        "agent_result": result,
        "human_review_required": True,
    }
