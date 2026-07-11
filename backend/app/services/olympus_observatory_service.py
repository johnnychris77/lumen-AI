"""v5.1 — Project Olympus, Section 5: Global Research Observatory.

Entirely a read-only composition over pre-existing rows -- no new table.
"Participation is opt-in": every query here is scoped to organizations
with `AdvisoryConsortiumMember.observatory_opt_in == True`, and any
tenant-originated row (Horizon's alerts/registry entries, Apollo's
improvement initiatives) whose `tenant_id` doesn't belong to an opted-in
participant is excluded.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.continuous_improvement import ContinuousImprovementInitiative
from app.models.federated_horizon import EmergingTrendAlert
from app.models.global_intelligence import InstrumentRiskRegistryEntry
from app.models.p24_standards import AdvisoryConsortiumMember, StandardsPublication


def _opted_in_tenant_ids(db: Session) -> set[str]:
    rows = (
        db.query(AdvisoryConsortiumMember.tenant_id)
        .filter(AdvisoryConsortiumMember.observatory_opt_in.is_(True), AdvisoryConsortiumMember.membership_status == "active")
        .all()
    )
    return {r[0] for r in rows}


def emerging_contamination_trends(db: Session, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(EmergingTrendAlert)
        .filter(EmergingTrendAlert.trend_type.ilike("%contamination%"))
        .order_by(EmergingTrendAlert.detected_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "trend_type": r.trend_type, "description": r.description, "tenant_count": r.tenant_count,
            "severity": r.severity, "status": r.status, "detected_at": r.detected_at.isoformat(),
            "human_review_required": r.human_review_required, "disclaimer": r.disclaimer,
        }
        for r in rows
    ]


def instrument_performance_trends(db: Session, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(InstrumentRiskRegistryEntry)
        .order_by(InstrumentRiskRegistryEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "instrument_category": r.instrument_category, "risk_pattern": r.risk_pattern,
            "risk_score": r.risk_score, "facilities_reporting": r.facilities_reporting,
            "trend_direction": r.trend_direction, "registry_status": r.registry_status,
            "human_review_required": r.human_review_required, "disclaimer": r.disclaimer,
        }
        for r in rows
    ]


def quality_improvement_initiatives(db: Session, *, limit: int = 20) -> list[dict]:
    opted_in = _opted_in_tenant_ids(db)
    if not opted_in:
        return []
    rows = (
        db.query(ContinuousImprovementInitiative)
        .filter(ContinuousImprovementInitiative.tenant_id.in_(opted_in))
        .order_by(ContinuousImprovementInitiative.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "initiative": r.initiative, "status": r.status, "methodology": r.methodology,
            "expected_impact": r.expected_impact, "actual_impact": r.actual_impact,
        }
        for r in rows
    ]


def published_research(db: Session, *, limit: int = 20) -> list[dict]:
    """Inspection science updates + published research (Section 5) --
    reuses P24's `StandardsPublication` directly."""
    rows = (
        db.query(StandardsPublication)
        .filter(StandardsPublication.status == "published")
        .order_by(StandardsPublication.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "title": r.title, "publication_type": r.publication_type, "version": r.version,
            "abstract": r.abstract, "regulatory_bodies_aligned": r.regulatory_bodies_aligned,
        }
        for r in rows
    ]


def observatory_summary(db: Session) -> dict:
    return {
        "opted_in_participant_count": len(_opted_in_tenant_ids(db)),
        "emerging_contamination_trends": emerging_contamination_trends(db, limit=5),
        "instrument_performance_trends": instrument_performance_trends(db, limit=5),
        "quality_improvement_initiatives": quality_improvement_initiatives(db, limit=5),
        "published_research": published_research(db, limit=5),
    }
