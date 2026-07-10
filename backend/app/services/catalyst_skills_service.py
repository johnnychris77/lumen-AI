"""v4.4 — Project Catalyst, Section 10: AI Skills Framework.

Every skill below is an independently callable, independently testable
function that wraps one or more already-existing services — no skill
computes anything a prior sprint didn't already compute for real.
`CatalystSkill` rows are a catalog for discovery/`GET /api/catalyst/skills`
only; the functions here are what actually run.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.atlas_enterprise import REPORT_AUDIENCES, REPORT_CADENCES
from app.models.catalyst_copilot import SKILL_CATEGORIES, CatalystSkill
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.predictive_insight import HORIZON_7_DAY, OPERATIONAL_FORECAST_TYPES
from app.services import (
    anatomy_risk_service,
    atlas_report_service,
    digital_twin_engine,
    finding_trend_service,
    insight_operational_forecast_service,
    knowledge_graph_service,
    knowledge_repository_service,
    platform_org_service,
    pulse_executive_service,
    pulse_kpi_service,
)
from app.services.forge_workflow_service import get_workflow, list_workflows, version_history

_SEED_SKILLS = [
    {"skill_key": "inspection", "name": "Inspection Skill", "category": "inspection",
     "description": "Answers questions about inspection queues, findings, and instrument-specific history from real Inspection/InspectionFinding rows."},
    {"skill_key": "digital_twin", "name": "Digital Twin Skill", "category": "digital_twin",
     "description": "Retrieves live Digital Twin dashboards, station status, and flow history for a facility."},
    {"skill_key": "knowledge_search", "name": "Knowledge Search Skill", "category": "knowledge_search",
     "description": "Searches the institutional Knowledge Graph and Knowledge Article repository."},
    {"skill_key": "analytics", "name": "Analytics Skill", "category": "analytics",
     "description": "Computes contamination-by-zone and finding-type trend analytics from real InspectionFinding rows."},
    {"skill_key": "forecast", "name": "Forecast Skill", "category": "forecast",
     "description": "Projects operational forecasts (workload, backlog, availability) via the existing OLS-based forecast engine."},
    {"skill_key": "workflow", "name": "Workflow Skill", "category": "workflow",
     "description": "Looks up and publishes Forge workflow definitions."},
    {"skill_key": "research", "name": "Research Skill", "category": "research",
     "description": "Explains a finding's reasoning chain via the Knowledge Graph's clinical reasoning engine."},
    {"skill_key": "reporting", "name": "Reporting Skill", "category": "reporting",
     "description": "Generates and retrieves executive reports and live KPI/executive dashboards."},
]


def ensure_skills_seeded(db: Session) -> None:
    existing = {s.skill_key for s in db.query(CatalystSkill).all()}
    for seed in _SEED_SKILLS:
        if seed["skill_key"] not in existing:
            db.add(CatalystSkill(**seed))
    db.commit()


def list_skills(db: Session) -> list[dict]:
    ensure_skills_seeded(db)
    rows = db.query(CatalystSkill).order_by(CatalystSkill.id.asc()).all()
    return [
        {"skill_key": r.skill_key, "name": r.name, "category": r.category, "description": r.description, "enabled": r.enabled}
        for r in rows
    ]


# ── Section 10 skill functions ───────────────────────────────────────────────

def inspection_skill(db: Session, tenant_id: str, *, instrument_query: str = "", finding_type: str = "", days: int = 7) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since)
    if instrument_query:
        q = q.filter(Inspection.instrument_type.ilike(f"%{instrument_query}%"))
    inspections = q.all()

    if finding_type:
        ids = {i.id for i in inspections}
        findings = db.query(InspectionFinding).filter(
            InspectionFinding.tenant_id == tenant_id, InspectionFinding.finding_type == finding_type,
            InspectionFinding.inspection_id.in_(ids) if ids else False,
        ).all()
        matched_ids = {f.inspection_id for f in findings}
        inspections = [i for i in inspections if i.id in matched_ids]

    return {
        "skill": "inspection", "since": since.isoformat(), "count": len(inspections),
        "inspections": [
            {"id": i.id, "instrument_type": i.instrument_type, "detected_issue": i.detected_issue,
             "risk_score": i.risk_score, "status": i.status, "created_at": i.created_at.isoformat()}
            for i in inspections[:50]
        ],
    }


def digital_twin_skill(db: Session, tenant_id: str, *, facility_id: str = "") -> dict:
    dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db)
    return {"skill": "digital_twin", "dashboard": dashboard.model_dump()}


def knowledge_search_skill(db: Session, tenant_id: str, *, query: str = "", category: str = "instrument") -> dict:
    """`knowledge_repository_service.list_articles`'s `instrument`/
    `manufacturer`/`finding` filters are exact facet matches against an
    article's structured `applicable_*` fields — not a free-text search —
    so a free-text query is matched against each article's title/body
    directly here, in addition to (never instead of) those facets."""
    graph_results = knowledge_graph_service.explore(db, tenant_id, category, query)
    needle = query.strip().lower()
    articles = knowledge_repository_service.list_articles(db, tenant_id, approval_status="approved")
    if needle:
        articles = [a for a in articles if needle in a["title"].lower() or needle in a["body"].lower()]
    return {"skill": "knowledge_search", "graph": graph_results, "articles": articles[:20]}


def analytics_skill(db: Session, tenant_id: str, *, days: int = 180, granularity: str = "monthly") -> dict:
    return {
        "skill": "analytics",
        "anatomy_risk": anatomy_risk_service.anatomy_risk_dashboard(db, tenant_id, days=days),
        "finding_trends": finding_trend_service.finding_trends(db, tenant_id, granularity=granularity),
    }


def forecast_skill(db: Session, tenant_id: str, *, forecast_type: str = "", horizon: str = HORIZON_7_DAY) -> dict:
    forecast_type = forecast_type if forecast_type in OPERATIONAL_FORECAST_TYPES else OPERATIONAL_FORECAST_TYPES[0]
    result = insight_operational_forecast_service.forecast_operational(db, tenant_id, forecast_type=forecast_type, horizon=horizon)
    return {"skill": "forecast", "forecast": result}


def workflow_skill(db: Session, tenant_id: str, *, workflow_id: int | None = None, category: str = "") -> dict:
    if workflow_id is not None:
        return {"skill": "workflow", "workflow": get_workflow(db, workflow_id), "versions": version_history(db, workflow_id)}
    return {"skill": "workflow", "workflows": list_workflows(db, tenant_id, category=category)}


def research_skill(db: Session, tenant_id: str, *, instrument_type: str = "", finding_type: str = "", manufacturer: str = "") -> dict:
    return {"skill": "research", "reasoning_chain": knowledge_graph_service.reasoning_chain(instrument_type, finding_type, manufacturer)}


def reporting_skill(db: Session, tenant_id: str, *, audience: str = "spd_director", cadence: str = "monthly", facility_id: str = "") -> dict:
    """`atlas_report_service`'s cadence enum is monthly/quarterly/annual
    only (no daily/weekly — confirmed in `REPORT_CADENCES`) and requires a
    resolvable enterprise-hierarchy facility. A daily/weekly briefing, or
    any tenant with no such facility, gets the live Pulse executive
    dashboard instead — never a persisted report coerced into a cadence
    it doesn't support."""
    facility = platform_org_service.facility_for_tenant(db, tenant_id)
    if facility is not None and cadence in REPORT_CADENCES and audience in REPORT_AUDIENCES:
        report = atlas_report_service.generate_executive_report(
            db, facility["system_id"], audience=audience, cadence=cadence, facility_id=facility_id, generated_by="catalyst_copilot",
        )
        return {"skill": "reporting", "source": "atlas_report", "report": report}
    return {
        "skill": "reporting", "source": "pulse_executive_dashboard",
        "executive_dashboard": pulse_executive_service.executive_command_dashboard(db, tenant_id, facility_id=facility_id),
        "live_kpis": pulse_kpi_service.live_kpis(db, tenant_id),
        "note": "Falling back to the live executive dashboard (either no enterprise-hierarchy facility on record, or cadence/audience isn't one atlas_report_service persists) rather than fabricating a report it can't produce.",
    }


SKILL_DISPATCH = {
    "inspection": inspection_skill,
    "digital_twin": digital_twin_skill,
    "knowledge_search": knowledge_search_skill,
    "analytics": analytics_skill,
    "forecast": forecast_skill,
    "workflow": workflow_skill,
    "research": research_skill,
    "reporting": reporting_skill,
}

assert set(SKILL_DISPATCH) == set(SKILL_CATEGORIES)
