"""v5.3 — Project Genesis AI, Section 6: Research Collaboration Hub.

Zero new tables. P20's `ResearchDataset`/`ResearchStudy`/
`ResearchPublication` (`p20_network_intelligence.py`) already implement
governance-gated, IRB-aware research proposals (`ResearchStudy.status ==
"proposed"`), multi-center studies, benchmark datasets, academic
collaboration (`ResearchStudy.institution`), and publication tracking --
already composed by `horizon_research_portal_service.py` (v3.4). This
module only adds "participation is opt-in": every function here is
scoped to `AdvisoryConsortiumMember.research_opt_in == True` participants.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.p20_network_intelligence import ResearchDataset, ResearchStudy
from app.models.p24_standards import AdvisoryConsortiumMember
from app.services import horizon_research_portal_service


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _opted_in_tenant_ids(db: Session) -> set[str]:
    rows = (
        db.query(AdvisoryConsortiumMember.tenant_id)
        .filter(AdvisoryConsortiumMember.research_opt_in.is_(True), AdvisoryConsortiumMember.membership_status == "active")
        .all()
    )
    return {r[0] for r in rows}


def research_hub_summary(db: Session) -> dict:
    portal = horizon_research_portal_service.research_portal_summary(db)
    proposed_studies = db.query(ResearchStudy).filter(ResearchStudy.status == "proposed").all()
    draft_datasets = db.query(ResearchDataset).filter(ResearchDataset.release_status == "draft").all()
    return {
        **portal,
        "opted_in_participant_count": len(_opted_in_tenant_ids(db)),
        "proposed_studies": [_row_to_dict(r) for r in proposed_studies],
        "draft_datasets": [_row_to_dict(r) for r in draft_datasets],
    }
