"""v4.0 — LumenAI OS (Project Genesis), Section 5: Global Search.

No cross-entity global search endpoint existed before Genesis — only
narrow per-entity search endpoints (`GET /search` in
`app/routes/instrument_registry.py` and `app/routes/baseline_library.py`,
`post_search` in `app/routes/knowledge.py`). This module is a genuinely
new aggregator, built entirely on top of the existing tables those
per-entity endpoints already query — it introduces no new search index
and fabricates no relevance score beyond a simple case-insensitive
substring match, grouped by the application/module each result belongs to.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.baseline_library import BaselineLibraryEntry
from app.models.digital_twin import InstrumentFlowRecord
from app.models.enterprise_hierarchy import EnterpriseFacility
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.instrument_registry import RegistryInstrument
from app.models.knowledge import KnowledgeArticle
from app.models.p20_network_intelligence import ResearchStudy
from app.models.user import User

_LIMIT_PER_CATEGORY = 10


def _like(term: str) -> str:
    return f"%{term}%"


def global_search(db: Session, tenant_id: str, query: str) -> dict:
    if not query or len(query.strip()) < 2:
        return {"query": query, "results": {}, "total": 0}

    term = query.strip()
    like_term = _like(term)
    results: dict[str, list[dict]] = {}

    twins = (
        db.query(InstrumentFlowRecord)
        .filter(InstrumentFlowRecord.tenant_id == tenant_id, InstrumentFlowRecord.instrument_name.ilike(like_term))
        .limit(_LIMIT_PER_CATEGORY).all()
    )
    results["twin"] = [{"id": t.id, "title": t.instrument_name, "subtitle": t.to_station, "module": "twin"} for t in twins]

    inspections = (
        db.query(Inspection)
        .filter(Inspection.tenant_id == tenant_id, Inspection.file_name.ilike(like_term))
        .limit(_LIMIT_PER_CATEGORY).all()
    )
    results["inspect"] = [{"id": i.id, "title": i.file_name, "subtitle": i.instrument_type, "module": "inspect"} for i in inspections]

    knowledge = (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.title.ilike(like_term))
        .limit(_LIMIT_PER_CATEGORY).all()
    )
    results["knowledge"] = [{"id": k.id, "title": k.title, "subtitle": k.category, "module": "knowledge"} for k in knowledge]

    baselines = (
        db.query(BaselineLibraryEntry)
        .filter(BaselineLibraryEntry.model_name.ilike(like_term) | BaselineLibraryEntry.manufacturer_name.ilike(like_term))
        .limit(_LIMIT_PER_CATEGORY).all()
    )
    results["knowledge_baselines"] = [
        {"id": b.id, "title": b.model_name, "subtitle": b.manufacturer_name, "module": "knowledge"} for b in baselines
    ]

    users = db.query(User).filter(User.email.ilike(like_term)).limit(_LIMIT_PER_CATEGORY).all()
    results["users"] = [{"id": u.id, "title": u.email, "subtitle": u.role, "module": "developer"} for u in users]

    facilities = db.query(EnterpriseFacility).filter(EnterpriseFacility.facility_name.ilike(like_term)).limit(_LIMIT_PER_CATEGORY).all()
    results["facilities"] = [{"id": f.id, "title": f.facility_name, "subtitle": f.facility_type, "module": "connect"} for f in facilities]

    instrument_families = (
        db.query(RegistryInstrument)
        .filter(RegistryInstrument.model_name.ilike(like_term) | RegistryInstrument.manufacturer_name.ilike(like_term))
        .limit(_LIMIT_PER_CATEGORY).all()
    )
    results["instrument_families"] = [
        {"id": r.id, "title": r.model_name, "subtitle": r.manufacturer_name, "module": "knowledge"} for r in instrument_families
    ]

    anatomy_zones = (
        db.query(InspectionFinding.zone)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.zone.ilike(like_term))
        .distinct().limit(_LIMIT_PER_CATEGORY).all()
    )
    results["anatomy"] = [{"id": z[0], "title": z[0], "subtitle": "anatomy zone", "module": "knowledge"} for z in anatomy_zones if z[0]]

    research = db.query(ResearchStudy).filter(ResearchStudy.title.ilike(like_term)).limit(_LIMIT_PER_CATEGORY).all()
    results["research"] = [{"id": r.id, "title": r.title, "subtitle": r.institution or "", "module": "research"} for r in research]

    results = {k: v for k, v in results.items() if v}
    total = sum(len(v) for v in results.values())
    return {"query": term, "results": results, "total": total}
