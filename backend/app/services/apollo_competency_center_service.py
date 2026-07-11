"""v4.7 — Project Apollo, Section 5: Competency Center.

Composes `competency_service.py`'s single `CompetencyEvent` log — including
the four new event types Apollo added there (annual competency, procedure
validation, simulation result, knowledge contribution) — into one
Competency Center view. No parallel competency model.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import competency_service


def record_annual_competency(db: Session, *, tenant_id: str, technician: str, competency_area: str) -> dict:
    competency_service.record_annual_competency(
        db, tenant_id=tenant_id, technician=technician, competency_area=competency_area,
    )
    db.commit()
    return competency_service.competency_summary(db, technician)


def record_procedure_validation(db: Session, *, tenant_id: str, technician: str, procedure_name: str) -> dict:
    competency_service.record_procedure_validation(
        db, tenant_id=tenant_id, technician=technician, procedure_name=procedure_name,
    )
    db.commit()
    return competency_service.competency_summary(db, technician)


def record_simulation_result(db: Session, *, tenant_id: str, technician: str, scenario: str, passed: bool) -> dict:
    competency_service.record_simulation_result(
        db, tenant_id=tenant_id, technician=technician, scenario=scenario, passed=passed,
    )
    db.commit()
    return competency_service.competency_summary(db, technician)


def record_knowledge_contribution(db: Session, *, tenant_id: str, technician: str, topic: str) -> dict:
    competency_service.record_knowledge_contribution(
        db, tenant_id=tenant_id, technician=technician, topic=topic,
    )
    db.commit()
    return competency_service.competency_summary(db, technician)


def competency_center_summary(db: Session, tenant_id: str) -> dict:
    """Technician/Supervisor/Manager rollup for the Competency Center tab —
    reuses the existing per-technician quality dashboard, adding no second
    aggregation of the same events."""
    dashboard = competency_service.technician_quality_dashboard(db, tenant_id)
    technicians = dashboard["technicians"]
    return {
        "technicians": technicians,
        "technician_count": len(technicians),
        "annual_competencies_total": sum(
            competency_service.competency_summary(db, t["technician"])["annual_competencies"] for t in technicians
        ),
        "knowledge_contributions_total": sum(
            competency_service.competency_summary(db, t["technician"])["knowledge_contributions"] for t in technicians
        ),
        "human_review_required": True,
    }
