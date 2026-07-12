"""Project Maestro, Section 2: Priority Engine.

Ranks the 9 named priority categories from real, already-computed
specialist signals -- Maestro never invents its own risk math. Each
category resolver is a thin read of one specialist's existing output;
Maestro's only original work is comparing across categories and ranking
them into one ordered leadership list.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import (
    PRIORITY_HIGHEST_PRIORITY_CAPA,
    PRIORITY_HIGHEST_PRIORITY_EXECUTIVE_ISSUE,
    PRIORITY_HIGHEST_PRIORITY_INSPECTION,
    PRIORITY_HIGHEST_PRIORITY_REPAIR,
    PRIORITY_HIGHEST_RISK_EQUIPMENT,
    PRIORITY_HIGHEST_RISK_FACILITY,
    PRIORITY_HIGHEST_RISK_INSTRUMENT,
    PRIORITY_HIGHEST_RISK_TECHNICIAN_EDUCATION_NEED,
    PRIORITY_HIGHEST_RISK_WORKFLOW,
    MaestroPriorityItem,
)
from app.models.or_connect import REPAIR_PENDING, RepairRequest
from app.models.patient_safety import ExecutiveRiskSignal
from app.models.vulcan_reliability import VulcanReliabilityAssessment
from app.services.capa_suggestion_service import generate_capa_suggestions
from app.services.sage_knowledge_gap_service import list_gaps
from app.services.sentinelx_dashboard_service import risk_dashboard_summary
from app.services.sentinelx_supervisor_workspace_service import supervisor_workspace_summary


def _cached_supervisor_workspace_summary(db: Session, tenant_id: str, cache: dict) -> dict:
    if "supervisor_workspace_summary" not in cache:
        cache["supervisor_workspace_summary"] = supervisor_workspace_summary(db, tenant_id, limit=1)
    return cache["supervisor_workspace_summary"]


def _cached_risk_dashboard_summary(db: Session, tenant_id: str, cache: dict) -> dict:
    if "risk_dashboard_summary" not in cache:
        cache["risk_dashboard_summary"] = risk_dashboard_summary(db, tenant_id)
    return cache["risk_dashboard_summary"]


def _cached_open_gaps(db: Session, tenant_id: str, cache: dict) -> list[dict]:
    if "open_gaps" not in cache:
        cache["open_gaps"] = list_gaps(db, tenant_id, status="open")
    return cache["open_gaps"]


def _highest_risk_instrument(db: Session, tenant_id: str, cache: dict) -> dict | None:
    top = _cached_supervisor_workspace_summary(db, tenant_id, cache)["highest_risk_instruments"][:1]
    if not top:
        return None
    item = top[0]
    return {
        "subject": item["instrument_identity"],
        "priority_score": item["average_risk_score"],
        "source_specialist": "sentinelx",
        "rationale": f"Highest average risk score ({item['average_risk_score']}) across {item['assessment_count']} Sentinel-X assessments.",
        "evidence": item,
    }


def _highest_risk_workflow(db: Session, tenant_id: str, cache: dict) -> dict | None:
    workflow = _cached_risk_dashboard_summary(db, tenant_id, cache)["workflow_risk"]
    count = workflow.get("process_variation_flagged_count") or 0
    if count <= 0:
        return None
    return {
        "subject": "process_variation",
        "priority_score": float(count),
        "source_specialist": "sentinelx",
        "rationale": f"{count} risk assessments flag technician process-variation as a contributing factor.",
        "evidence": workflow,
    }


def _highest_risk_facility(db: Session, tenant_id: str, cache: dict) -> dict | None:
    facilities = _cached_risk_dashboard_summary(db, tenant_id, cache)["facility_risk"]
    if not facilities:
        return None
    top = facilities[0]
    return {
        "subject": top["key"],
        "priority_score": top["average_risk_score"],
        "source_specialist": "sentinelx",
        "rationale": f"Highest average risk score ({top['average_risk_score']}) across {top['count']} assessments at this facility.",
        "evidence": top,
    }


def _highest_risk_technician_education_need(db: Session, tenant_id: str, cache: dict) -> dict | None:
    gaps = _cached_open_gaps(db, tenant_id, cache)
    if not gaps:
        return None
    top = max(gaps, key=lambda g: g["occurrence_count"])
    return {
        "subject": f"{top['competency_domain']} / {top['scope_value']}",
        "priority_score": float(top["occurrence_count"]),
        "source_specialist": "sage",
        "rationale": top["narrative"] or f"Recurring knowledge gap ({top['occurrence_count']} occurrences) in {top['competency_domain']}.",
        "evidence": top,
    }


def _highest_risk_equipment(db: Session, tenant_id: str, cache: dict) -> dict | None:
    rows = (
        db.query(VulcanReliabilityAssessment)
        .filter(VulcanReliabilityAssessment.tenant_id == tenant_id)
        .order_by(VulcanReliabilityAssessment.created_at.desc())
        .limit(200)
        .all()
    )
    if not rows:
        return None
    worst = min(rows, key=lambda r: r.reliability_score)
    return {
        "subject": worst.instrument_identity,
        "priority_score": round(100.0 - worst.reliability_score, 1),
        "source_specialist": "vulcan",
        "rationale": f"Lowest reliability score ({worst.reliability_score}) of any recently tracked instrument, category '{worst.reliability_category}'.",
        "evidence": {
            "reliability_score": worst.reliability_score,
            "reliability_category": worst.reliability_category,
            "instrument_family": worst.instrument_family,
        },
    }


def _highest_priority_capa(db: Session, tenant_id: str, cache: dict) -> dict | None:
    suggestions = generate_capa_suggestions(db, tenant_id)
    if not suggestions:
        return None
    top = max(suggestions, key=lambda s: s["occurrences"])
    return {
        "subject": top["suggested_title"],
        "priority_score": float(top["occurrences"]),
        "source_specialist": "capa_suggestion_service",
        "rationale": top["recommendation"],
        "evidence": top,
    }


def _highest_priority_inspection(db: Session, tenant_id: str, cache: dict) -> dict | None:
    top = _cached_supervisor_workspace_summary(db, tenant_id, cache)["highest_risk_inspections"][:1]
    if not top:
        return None
    item = top[0]
    return {
        "subject": f"inspection:{item['inspection_id']}",
        "priority_score": item["risk_score"],
        "source_specialist": "sentinelx",
        "rationale": item.get("reasoning_narrative") or f"Highest risk score ({item['risk_score']}) among open inspections.",
        "evidence": item,
    }


def _highest_priority_repair(db: Session, tenant_id: str, cache: dict) -> dict | None:
    rows = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.status == REPAIR_PENDING)
        .order_by(RepairRequest.created_at.asc())
        .all()
    )
    if not rows:
        return None
    top = rows[0]
    created_at = top.created_at if top.created_at.tzinfo else top.created_at.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - created_at).days
    return {
        "subject": top.instrument_identity or f"repair:{top.id}",
        "priority_score": float(age_days),
        "source_specialist": "or_connect",
        "rationale": f"Oldest pending repair request ({age_days} days open), vendor {top.vendor_name or 'unassigned'}.",
        "evidence": {
            "repair_id": top.id, "status": top.status, "repair_type": top.repair_type, "vendor_name": top.vendor_name,
        },
    }


_RISK_TIER_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


def _highest_priority_executive_issue(db: Session, tenant_id: str, cache: dict) -> dict | None:
    rows = (
        db.query(ExecutiveRiskSignal)
        .filter(ExecutiveRiskSignal.tenant_id == tenant_id, ExecutiveRiskSignal.human_review_status == "pending")
        .all()
    )
    if not rows:
        return None
    top = max(rows, key=lambda r: (_RISK_TIER_RANK.get(r.risk_tier, 0), r.confidence_score or 0.0))
    score = round(_RISK_TIER_RANK.get(top.risk_tier, 0) * 25.0 + (top.confidence_score or 0.0) * 10.0, 1)
    return {
        "subject": top.event_type,
        "priority_score": score,
        "source_specialist": "executive_risk_signal",
        "rationale": top.association_reason or f"Unreviewed {top.risk_tier} executive risk signal ({top.event_type}).",
        "evidence": {
            "risk_tier": top.risk_tier, "event_type": top.event_type,
            "estimated_financial_exposure": top.estimated_financial_exposure,
        },
    }


_CATEGORY_RESOLVERS = {
    PRIORITY_HIGHEST_RISK_INSTRUMENT: _highest_risk_instrument,
    PRIORITY_HIGHEST_RISK_WORKFLOW: _highest_risk_workflow,
    PRIORITY_HIGHEST_RISK_FACILITY: _highest_risk_facility,
    PRIORITY_HIGHEST_RISK_TECHNICIAN_EDUCATION_NEED: _highest_risk_technician_education_need,
    PRIORITY_HIGHEST_RISK_EQUIPMENT: _highest_risk_equipment,
    PRIORITY_HIGHEST_PRIORITY_CAPA: _highest_priority_capa,
    PRIORITY_HIGHEST_PRIORITY_INSPECTION: _highest_priority_inspection,
    PRIORITY_HIGHEST_PRIORITY_REPAIR: _highest_priority_repair,
    PRIORITY_HIGHEST_PRIORITY_EXECUTIVE_ISSUE: _highest_priority_executive_issue,
}


def compute_priorities(db: Session, tenant_id: str) -> list[MaestroPriorityItem]:
    """Runs every category resolver, persists one `MaestroPriorityItem` per
    category that has real data (categories with nothing to report are
    skipped, never fabricated), and ranks the result across categories by
    `priority_score`."""
    cache: dict = {}
    candidates = []
    for category, resolver in _CATEGORY_RESOLVERS.items():
        result = resolver(db, tenant_id, cache)
        if result is not None:
            candidates.append((category, result))

    candidates.sort(key=lambda c: c[1]["priority_score"], reverse=True)

    # Stamped once and passed explicitly to every row in this batch --
    # each row's `created_at` default is otherwise evaluated independently
    # at flush time, so two rows from the very same compute_priorities()
    # call can land microseconds apart and never compare equal, which
    # would make latest_priorities() below return only one row instead of
    # the whole batch.
    batch_created_at = datetime.now(timezone.utc)

    rows = []
    for rank, (category, result) in enumerate(candidates, start=1):
        row = MaestroPriorityItem(
            tenant_id=tenant_id,
            created_at=batch_created_at,
            category=category,
            subject=result["subject"][:300],
            priority_score=result["priority_score"],
            rank=rank,
            source_specialist=result["source_specialist"],
            rationale=result["rationale"],
            evidence_json=json.dumps(result["evidence"]),
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def to_dict(row: MaestroPriorityItem) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "category": row.category,
        "subject": row.subject,
        "priority_score": row.priority_score,
        "rank": row.rank,
        "source_specialist": row.source_specialist,
        "rationale": row.rationale,
        "evidence": json.loads(row.evidence_json or "{}"),
    }


def latest_priorities(db: Session, tenant_id: str) -> list[dict]:
    """Returns the most recent priority-engine run's items, ranked."""
    latest = (
        db.query(MaestroPriorityItem)
        .filter(MaestroPriorityItem.tenant_id == tenant_id)
        .order_by(MaestroPriorityItem.created_at.desc())
        .first()
    )
    if latest is None:
        return []
    rows = (
        db.query(MaestroPriorityItem)
        .filter(MaestroPriorityItem.tenant_id == tenant_id, MaestroPriorityItem.created_at == latest.created_at)
        .order_by(MaestroPriorityItem.rank.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
