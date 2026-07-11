"""v5.1 — Project Olympus, Section 2: Trust Network.

No trust construct anywhere in this codebase scores an *organization* —
Athena's Knowledge Trust Score (`athena_trust_service.py`) scores a single
`KnowledgeArticle`. Every component here is computed live from real,
pre-existing rows and persisted only as a historical `NetworkTrustSnapshot`
(the same snapshot pattern as Phoenix's `PlatformMaturitySnapshot` and
Apollo's `QualityTwinSnapshot`) — never a fabricated number.

Trust is earned, not assigned: a brand-new participant with no history in
any of the six components below scores 0 on every component that has no
data yet, not a default/optimistic score.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.federated_horizon import ClinicalEvidenceReference, KnowledgeContribution
from app.models.knowledge import KnowledgeArticle
from app.models.olympus_network import HIX_APPROVED, HIX_PUBLISHED, HIXExchangePackage, NetworkTrustSnapshot
from app.models.p24_standards import AdvisoryConsortiumMember
from app.services import athena_trust_service

_MEMBERSHIP_STATUS_SCORES = {"active": 100.0, "pending": 40.0, "suspended": 10.0, "resigned": 0.0}


def _participation_status(member: AdvisoryConsortiumMember | None) -> float:
    if member is None:
        return 0.0
    return _MEMBERSHIP_STATUS_SCORES.get(member.membership_status, 0.0)


def _knowledge_quality(db: Session, tenant_id: str) -> float:
    articles = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).all()
    if not articles:
        return 0.0
    scores = [athena_trust_service.compute_trust_score(db, a)["overall_trust_score"] for a in articles]
    return round(sum(scores) / len(scores), 1)


def _validation_history(db: Session, tenant_id: str) -> float:
    """This organization's own Healthcare Intelligence Exchange
    submissions (Sections 3/4) that have passed governance review --
    packages still in draft or pending review don't count either way,
    only ones a reviewer has actually decided on."""
    decided = (
        db.query(HIXExchangePackage)
        .filter(
            HIXExchangePackage.source_tenant_id == tenant_id,
            HIXExchangePackage.status.in_([HIX_APPROVED, HIX_PUBLISHED, "rejected"]),
        )
        .all()
    )
    if not decided:
        return 0.0
    passed = sum(1 for pkg in decided if pkg.status in (HIX_APPROVED, HIX_PUBLISHED))
    return round(100.0 * passed / len(decided), 1)


def _evidence_contributions(db: Session, tenant_id: str) -> float:
    count = db.query(ClinicalEvidenceReference).filter(ClinicalEvidenceReference.tenant_id == tenant_id).count()
    return round(min(100.0, 20.0 * count), 1)


def _peer_recognition(db: Session, tenant_id: str) -> float:
    """Genuinely new: no endorsement/rating construct existed before this
    table. Approved cross-organization knowledge contributions stand in
    as the only real signal of peer-recognized value this codebase has
    today -- documented honestly rather than inventing a rating system."""
    approved = (
        db.query(KnowledgeContribution)
        .filter(KnowledgeContribution.source_tenant_id == tenant_id, KnowledgeContribution.approval_status == "approved")
        .count()
    )
    return round(min(100.0, 15.0 * approved), 1)


def _governance_compliance(member: AdvisoryConsortiumMember | None) -> float:
    if member is None:
        return 0.0
    score = 0.0
    if member.voting_rights:
        score += 50.0
    roles = json.loads(member.governance_roles or "[]")
    score += min(50.0, 12.5 * len(roles))
    return round(score, 1)


def compute_trust_snapshot(db: Session, tenant_id: str) -> dict:
    member = db.query(AdvisoryConsortiumMember).filter(AdvisoryConsortiumMember.tenant_id == tenant_id).first()
    components = {
        "participation_status": _participation_status(member),
        "knowledge_quality": _knowledge_quality(db, tenant_id),
        "validation_history": _validation_history(db, tenant_id),
        "evidence_contributions": _evidence_contributions(db, tenant_id),
        "peer_recognition": _peer_recognition(db, tenant_id),
        "governance_compliance": _governance_compliance(member),
    }
    overall = round(sum(components.values()) / len(components), 1)
    return {
        "tenant_id": tenant_id,
        "components": components,
        "overall_trust_score": overall,
        "participation_level": member.membership_tier if member else "",
    }


def compute_and_record_trust_snapshot(db: Session, tenant_id: str) -> dict:
    computed = compute_trust_snapshot(db, tenant_id)
    row = NetworkTrustSnapshot(
        tenant_id=tenant_id,
        components_json=json.dumps(computed["components"]),
        overall_trust_score=computed["overall_trust_score"],
        participation_level=computed["participation_level"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "components": json.loads(row.components_json),
        "overall_trust_score": row.overall_trust_score,
        "participation_level": row.participation_level,
        "computed_at": row.computed_at.isoformat(),
        "human_review_required": row.human_review_required,
    }


def trust_history(db: Session, tenant_id: str, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(NetworkTrustSnapshot)
        .filter(NetworkTrustSnapshot.tenant_id == tenant_id)
        .order_by(NetworkTrustSnapshot.computed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "overall_trust_score": r.overall_trust_score,
            "components": json.loads(r.components_json), "computed_at": r.computed_at.isoformat(),
        }
        for r in rows
    ]


def network_trust_leaderboard(db: Session, *, top_n: int = 10) -> list[dict]:
    """Latest snapshot per tenant, ranked highest-first — reads only
    already-computed snapshots, never computes on the fly for every
    participant (that stays an explicit per-tenant action)."""
    latest_by_tenant: dict[str, NetworkTrustSnapshot] = {}
    for row in db.query(NetworkTrustSnapshot).order_by(NetworkTrustSnapshot.computed_at.asc()).all():
        latest_by_tenant[row.tenant_id] = row
    ranked = sorted(latest_by_tenant.values(), key=lambda r: r.overall_trust_score, reverse=True)[:top_n]
    return [
        {"tenant_id": r.tenant_id, "overall_trust_score": r.overall_trust_score, "computed_at": r.computed_at.isoformat()}
        for r in ranked
    ]
