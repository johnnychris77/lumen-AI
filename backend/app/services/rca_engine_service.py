"""v2.9 — LumenAI Quality (Project Guardian), Section 5: AI-Assisted RCA.

Generates a *draft* Root Cause Analysis — evidence, contributing factors,
historical recurrence, similar events, and investigation questions — for a
supervisor to edit before approval. Approval calls the existing, deliberately
human-only `root_cause_service.assign_root_cause` to create the real
`RootCauseAssignment`; this module never writes one itself, preserving the
"never infer causation automatically" principle that assignment already
enforces.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.quality_guardian import DISCLAIMER, QualityEvent, RCADraft
from app.models.root_cause import ROOT_CAUSES
from app.services import event_correlation_service
from app.services.quality_event_service import _get_event
from app.services.readiness_engine import has_repair_history
from app.services.root_cause_service import assign_root_cause

_PROCESS_STAGE_BY_CATEGORY = {
    "organic_residue": "Manual Cleaning",
    "instrument_condition": "Inspection / Storage",
    "assembly": "Assembly / Tray Packing",
    "packaging": "Packaging",
    "sterilization_indicators": "Sterilization",
    "unknown": "Unclassified — Requires Supervisor Review",
}

_INVESTIGATION_QUESTIONS = {
    "organic_residue": [
        "Was the manual cleaning/brushing step for this zone completed and verified?",
        "Was the brush size/type appropriate for this instrument's lumen or serration?",
        "Was pre-soak or enzymatic detergent contact time followed per IFU?",
    ],
    "instrument_condition": [
        "Is this instrument's condition consistent with normal wear, or does it suggest a process issue?",
        "Does this instrument have a prior repair or remove-from-service history?",
        "Is the finding consistent with a manufacturer-attributable material issue?",
    ],
    "assembly": [
        "Was the tray assembled against a current, correct count sheet?",
        "Was a double-check/verification step performed before tray closure?",
    ],
    "packaging": [
        "Was the sterilizer cycle's drying phase completed and verified?",
        "Was the wrap inspected for integrity immediately before use?",
    ],
    "sterilization_indicators": [
        "Was the sterilizer's mechanical/chemical/biological indicator reviewed before release?",
        "Was this load's parameters (time/temp/pressure) within validated range?",
    ],
    "unknown": [
        "What additional information would allow this event to be classified?",
    ],
}

_RECURRENCE_WINDOW_DAYS = 90


class RCADraftNotFoundError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def generate_rca_draft(db: Session, tenant_id: str, event_id: int) -> dict:
    event = _get_event(db, tenant_id, event_id)
    correlations = event_correlation_service.list_correlations(db, tenant_id, event_id)
    if not correlations:
        correlations = event_correlation_service.correlate_event(db, tenant_id, event_id)

    inspection_corr = next((c for c in correlations if c["target_type"] == "inspection" and c["target_id"]), None)
    inspection = None
    if inspection_corr is not None:
        inspection = db.query(models.Inspection).filter(models.Inspection.id == int(inspection_corr["target_id"])).first()

    category = event.spd_category or "unknown"
    process_stage = _PROCESS_STAGE_BY_CATEGORY.get(category, _PROCESS_STAGE_BY_CATEGORY["unknown"])

    evidence = [
        f"Original narrative: \"{event.narrative}\"",
        f"Classified as {event.finding_type or 'unclassified'} ({category}) with "
        f"{round((event.classification_confidence or 0) * 100)}% classifier confidence.",
    ]
    for c in correlations:
        if c["tracked"] and c["target_id"]:
            evidence.append(f"Correlated {c['target_type']}: {c['target_id']} (confidence {round(c['confidence'] * 100)}%).")

    contributing_factors = []
    if inspection is not None:
        if inspection.coverage_pct is not None and inspection.coverage_pct < 100:
            contributing_factors.append(f"Inspection coverage was only {inspection.coverage_pct}%.")
        if inspection.baseline_status != "approved":
            contributing_factors.append(
                f"No approved baseline was in place at inspection time (status: {inspection.baseline_status or 'not_checked'}).",
            )
        if has_repair_history(db, tenant_id, inspection):
            contributing_factors.append("This physical instrument has a prior remove-from-service/repair history.")
    if event.severity in ("high", "critical"):
        contributing_factors.append(f"Event reported at {event.severity} severity.")
    if not contributing_factors:
        contributing_factors.append("No specific contributing factor identified from available correlated data.")

    since = event.event_date - timedelta(days=_RECURRENCE_WINDOW_DAYS)
    historical_recurrence_count = (
        db.query(QualityEvent)
        .filter(
            QualityEvent.tenant_id == tenant_id, QualityEvent.finding_type == event.finding_type,
            QualityEvent.id != event.id, QualityEvent.event_date >= since, QualityEvent.event_date <= event.event_date,
        )
        .count()
    ) if event.finding_type else 0

    similar_events: list[dict] = []
    if inspection is not None and event.finding_type:
        from app.services.similar_case_finder_service import find_similar_cases

        similar_events = find_similar_cases(
            db, tenant_id, instrument_type=inspection.instrument_type, finding_type=event.finding_type,
            exclude_inspection_id=inspection.id, limit=5,
        )
    elif event.finding_type:
        rows = (
            db.query(QualityEvent)
            .filter(QualityEvent.tenant_id == tenant_id, QualityEvent.finding_type == event.finding_type, QualityEvent.id != event.id)
            .order_by(QualityEvent.id.desc())
            .limit(5)
            .all()
        )
        similar_events = [{"event_ref": r.event_ref, "event_date": r.event_date.isoformat(), "narrative": r.narrative} for r in rows]

    investigation_questions = _INVESTIGATION_QUESTIONS.get(category, _INVESTIGATION_QUESTIONS["unknown"])

    draft = RCADraft(
        tenant_id=tenant_id, event_id=event_id, inspection_id=inspection.id if inspection else None,
        likely_process_stage=process_stage, evidence_json=json.dumps(evidence),
        contributing_factors_json=json.dumps(contributing_factors),
        historical_recurrence_count=historical_recurrence_count, similar_events_json=json.dumps(similar_events),
        investigation_questions_json=json.dumps(investigation_questions),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    result = _row_to_dict(draft)
    result["evidence"] = evidence
    result["contributing_factors"] = contributing_factors
    result["similar_events"] = similar_events
    result["investigation_questions"] = investigation_questions
    return result


def _get_draft(db: Session, tenant_id: str, draft_id: int) -> RCADraft:
    draft = db.query(RCADraft).filter(RCADraft.id == draft_id, RCADraft.tenant_id == tenant_id).first()
    if draft is None:
        raise RCADraftNotFoundError(f"RCA draft {draft_id} not found for tenant {tenant_id}.")
    return draft


def update_draft(db: Session, tenant_id: str, draft_id: int, *, supervisor_edits: str) -> dict:
    draft = _get_draft(db, tenant_id, draft_id)
    draft.supervisor_edits = supervisor_edits
    db.commit()
    db.refresh(draft)
    return _row_to_dict(draft)


def approve_draft(db: Session, tenant_id: str, draft_id: int, *, root_cause: str, approved_by: str) -> dict:
    draft = _get_draft(db, tenant_id, draft_id)
    if draft.status != "draft":
        raise ValueError(f"RCA draft {draft_id} is already {draft.status}.")
    if root_cause not in ROOT_CAUSES:
        raise ValueError(f"root_cause must be one of {ROOT_CAUSES}")
    if draft.inspection_id is None:
        raise ValueError(
            "This draft has no correlated inspection — a root cause assignment requires a real "
            "inspection to attach to. Correlate the event to an inspection before approving.",
        )

    event = db.query(QualityEvent).filter(QualityEvent.id == draft.event_id).first()
    assignment = assign_root_cause(
        db, tenant_id=tenant_id, inspection_id=draft.inspection_id,
        finding_type=(event.finding_type if event else "") or "unknown", root_cause=root_cause, assigned_by=approved_by,
    )
    db.commit()
    db.refresh(assignment)

    draft.status = "approved"
    draft.approved_root_cause = root_cause
    draft.root_cause_assignment_id = assignment.id
    draft.reviewed_by = approved_by
    draft.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)
    return _row_to_dict(draft)


def reject_draft(db: Session, tenant_id: str, draft_id: int, *, rejected_by: str, reason: str = "") -> dict:
    draft = _get_draft(db, tenant_id, draft_id)
    if draft.status != "draft":
        raise ValueError(f"RCA draft {draft_id} is already {draft.status}.")
    draft.status = "rejected"
    draft.supervisor_edits = reason or draft.supervisor_edits
    draft.reviewed_by = rejected_by
    draft.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)
    return _row_to_dict(draft)


def get_draft(db: Session, tenant_id: str, draft_id: int) -> dict:
    result = _row_to_dict(_get_draft(db, tenant_id, draft_id))
    result["disclaimer"] = DISCLAIMER
    return result
