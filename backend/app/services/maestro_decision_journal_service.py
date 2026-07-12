"""Project Maestro, Section 8: Decision Journal.

The leadership knowledge base: for every recommendation a leader acts on,
records the evidence it was based on, which specialists were consulted,
Maestro's confidence, what the leader actually decided, the outcome, and
lessons learned. Recording a journal entry also advances the linked
recommendation's `status` -- this is the only place a recommendation
moves out of `pending`.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import MaestroDecisionJournalEntry, MaestroRecommendation


def record_decision(
    db: Session, tenant_id: str, recommendation_id: int, *, leader_decision: str, decided_by: str,
    decided_role: str = "", outcome: str = "", lessons_learned: str = "", new_status: str | None = None,
) -> MaestroDecisionJournalEntry:
    recommendation = (
        db.query(MaestroRecommendation)
        .filter(MaestroRecommendation.tenant_id == tenant_id, MaestroRecommendation.id == recommendation_id)
        .first()
    )
    if recommendation is None:
        raise ValueError(f"Recommendation {recommendation_id} not found for this tenant")
    if not leader_decision:
        raise ValueError("leader_decision is required for an auditable journal entry")

    entry = MaestroDecisionJournalEntry(
        tenant_id=tenant_id,
        recommendation_id=recommendation_id,
        evidence_json=recommendation.evidence_json,
        specialists_consulted_json=recommendation.specialists_consulted_json,
        confidence=recommendation.confidence,
        leader_decision=leader_decision,
        outcome=outcome,
        lessons_learned=lessons_learned,
        decided_by=decided_by,
        decided_role=decided_role,
    )
    db.add(entry)

    if new_status:
        recommendation.status = new_status

    db.commit()
    db.refresh(entry)
    return entry


def to_dict(row: MaestroDecisionJournalEntry) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "recommendation_id": row.recommendation_id,
        "evidence": json.loads(row.evidence_json or "{}"),
        "specialists_consulted": json.loads(row.specialists_consulted_json or "[]"),
        "confidence": row.confidence,
        "leader_decision": row.leader_decision,
        "outcome": row.outcome,
        "lessons_learned": row.lessons_learned,
        "decided_by": row.decided_by,
        "decided_role": row.decided_role,
    }


def journal_for_recommendation(db: Session, tenant_id: str, recommendation_id: int) -> list[dict]:
    rows = (
        db.query(MaestroDecisionJournalEntry)
        .filter(
            MaestroDecisionJournalEntry.tenant_id == tenant_id,
            MaestroDecisionJournalEntry.recommendation_id == recommendation_id,
        )
        .order_by(MaestroDecisionJournalEntry.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]


def list_journal(db: Session, tenant_id: str, *, limit: int = 50) -> list[dict]:
    rows = (
        db.query(MaestroDecisionJournalEntry)
        .filter(MaestroDecisionJournalEntry.tenant_id == tenant_id)
        .order_by(MaestroDecisionJournalEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [to_dict(r) for r in rows]
