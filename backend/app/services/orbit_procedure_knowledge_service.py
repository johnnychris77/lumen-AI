"""v4.5 — Project Orbit, Section 8: Procedure Knowledge.

Reuses `knowledge_repository_service.list_articles`'s existing
`procedure`/`anatomy_zone`/`applicable_instruments`/`applicable_findings`/
`applicable_manufacturers` fields on `KnowledgeArticle` — no second
procedure-knowledge table is created. Instrument-family/failure-mode/
Digital Twin links are composed from `knowledge_graph_service` and
`digital_twin_engine`, never re-derived.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import digital_twin_engine, knowledge_graph_service, knowledge_repository_service
from app.services.instrument_anatomy import resolve_family


def procedure_knowledge(db: Session, tenant_id: str, *, procedure: str, facility_id: str = "") -> dict:
    articles = knowledge_repository_service.list_articles(db, tenant_id, procedure=procedure, approval_status="approved")

    instrument_families = sorted({
        resolve_family(instr)
        for a in articles for instr in a.get("applicable_instruments", [])
    })
    high_risk_zones = sorted({a["anatomy_zone"] for a in articles if a.get("anatomy_zone")})
    known_failure_modes = sorted({f for a in articles for f in a.get("applicable_findings", [])})
    manufacturer_guidance = sorted({m for a in articles for m in a.get("applicable_manufacturers", [])})

    reasoning_chains = [
        knowledge_graph_service.reasoning_chain(instr, finding)
        for instr in list(instrument_families)[:3]
        for finding in list(known_failure_modes)[:2]
    ]

    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db) if instrument_families else None

    return {
        "procedure": procedure,
        "instrument_families": list(instrument_families),
        "high_risk_anatomy_zones": high_risk_zones,
        "known_failure_modes": known_failure_modes,
        "manufacturer_guidance": manufacturer_guidance,
        "digital_twin_summary": (
            {"utilization_pct": twin_dashboard.twin_state.utilization_pct, "open_alert_count": len(twin_dashboard.open_alerts)}
            if twin_dashboard is not None else None
        ),
        "knowledge_articles": articles,
        "reasoning_chains": reasoning_chains,
    }
