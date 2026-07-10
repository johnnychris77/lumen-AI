"""v3.4 — Project Horizon, Section 7: Research Portal.

Composes what already exists rather than re-deriving it: P20's Research
Data Exchange (`app/models/p20_network_intelligence.py::ResearchDataset`/
`ResearchStudy`/`ResearchPublication`) already implements governance-gated,
IRB-aware dataset release — this module only adds the presentation layer
(`/research`) that surfaces P20's already-released datasets alongside
Horizon's own new global signals, benchmarks, emerging trends, and
approved knowledge contributions. Every field returned here is already
de-identified by the service that produced it.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.federated_horizon import APPROVED, DISCLAIMER
from app.models.p20_network_intelligence import ResearchDataset, ResearchPublication, ResearchStudy
from app.services import (
    horizon_benchmark_service,
    horizon_contribution_service,
    horizon_federated_signal_service,
    horizon_knowledge_graph_service,
    horizon_trend_detection_service,
)


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _released_datasets(db: Session) -> list[dict]:
    rows = db.query(ResearchDataset).filter(ResearchDataset.release_status == "released").order_by(ResearchDataset.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def _published_studies(db: Session) -> list[dict]:
    rows = db.query(ResearchStudy).filter(ResearchStudy.status.in_(["active", "completed", "published"])).order_by(ResearchStudy.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def _publications(db: Session) -> list[dict]:
    rows = db.query(ResearchPublication).filter(ResearchPublication.governance_cleared.is_(True)).order_by(ResearchPublication.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def research_portal_summary(db: Session) -> dict:
    return {
        "global_trend_summaries": horizon_federated_signal_service.list_federated_signals(db),
        "global_benchmarks": horizon_benchmark_service.compute_all_horizon_benchmarks(db),
        "emerging_risks": horizon_trend_detection_service.list_emerging_trends(db),
        "published_knowledge": horizon_contribution_service.list_contributions(db, approval_status=APPROVED),
        "global_knowledge_graph": horizon_knowledge_graph_service.list_global_graph(db),
        "released_datasets": _released_datasets(db),
        "research_studies": _published_studies(db),
        "publications": _publications(db),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
