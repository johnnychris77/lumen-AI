"""v4.4 — Project Catalyst, Sections 4-6: Executive / Supervisor /
Technician Copilot personas.

These are role-gated *views* over the same query/skill/action engines
already built in this sprint — no persona computes a second copy of any
number. Role -> persona mapping uses Genesis's canonical role catalog
(`platform_identity_service.CANONICAL_ROLE_CATALOG`) rather than a new
role list.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import catalyst_skills_service, competency_service

PERSONA_EXECUTIVE = "executive"
PERSONA_SUPERVISOR = "supervisor"
PERSONA_TECHNICIAN = "technician"
CATALYST_PERSONAS = [PERSONA_EXECUTIVE, PERSONA_SUPERVISOR, PERSONA_TECHNICIAN]

_EXECUTIVE_ROLES = {"enterprise_admin", "hospital_admin", "facility_director", "market_director", "regional_administrator"}
_SUPERVISOR_ROLES = {"supervisor", "spd_manager", "admin"}


def persona_for_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role in _EXECUTIVE_ROLES:
        return PERSONA_EXECUTIVE
    if role in _SUPERVISOR_ROLES:
        return PERSONA_SUPERVISOR
    return PERSONA_TECHNICIAN


# ── Section 4: Executive Copilot ─────────────────────────────────────────────

_CADENCES = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90}


def executive_briefing(db: Session, tenant_id: str, *, cadence: str = "weekly") -> dict:
    cadence = cadence if cadence in _CADENCES else "weekly"
    reporting = catalyst_skills_service.reporting_skill(db, tenant_id, cadence=cadence)
    analytics = catalyst_skills_service.analytics_skill(db, tenant_id, days=_CADENCES[cadence] * 6 or 180)
    forecast = catalyst_skills_service.forecast_skill(db, tenant_id)
    return {
        "cadence": cadence,
        "quality": reporting,
        "risk": analytics["anatomy_risk"],
        "forecast": forecast["forecast"],
        "recommendations": reporting.get("report", {}).get("summary", {}).get("recommendations", []),
        "emerging_trends": analytics["finding_trends"],
    }


# ── Section 5: Supervisor Copilot ────────────────────────────────────────────

def supervisor_coaching(db: Session, tenant_id: str, *, technician: str) -> dict:
    summary = competency_service.competency_summary(db, technician)
    return {"technician": technician, "competency_summary": summary}


def supervisor_finding_explanation(db: Session, tenant_id: str, *, instrument_type: str, finding_type: str, manufacturer: str = "") -> dict:
    return catalyst_skills_service.research_skill(db, tenant_id, instrument_type=instrument_type, finding_type=finding_type, manufacturer=manufacturer)


# ── Section 6: Technician Copilot ────────────────────────────────────────────

def technician_contextual_help(db: Session, tenant_id: str, *, instrument_type: str = "") -> dict:
    """Contextual assistance only — never a disposition override. A
    technician's copilot answer surfaces knowledge and history; it never
    approves/rejects an inspection, which remains a supervisor's exclusive
    authority everywhere else in this codebase."""
    inspection_context = catalyst_skills_service.inspection_skill(db, tenant_id, instrument_query=instrument_type)
    knowledge = catalyst_skills_service.knowledge_search_skill(db, tenant_id, query=instrument_type)
    return {
        "instrument_type": instrument_type, "recent_inspections": inspection_context,
        "knowledge": knowledge, "note": "Informational only — supervisor review authority is unchanged.",
    }
