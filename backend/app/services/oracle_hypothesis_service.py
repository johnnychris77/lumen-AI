"""Project Oracle, Sections 3 & 5: the Discovery Engine and Hypothesis
Generator -- core CRUD for `OracleHypothesis`. `hypothesis_statement` and
`outcome_summary` must always be phrased as a potential association or
possible contributing factor, never a causal claim; callers pass that
phrasing in, this module does not rewrite free text, so every route/service
that writes these fields must not phrase them as causation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.oracle_discovery import (
    CONFIDENCE_EXPLORATORY,
    CONFIDENCE_LEVELS,
    DISCLAIMER,
    DISCOVERY_CATEGORIES,
    OracleHypothesis,
    STAGE_OBSERVATION,
    OracleStageTransition,
)


def to_dict(row: OracleHypothesis) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "tenant_id": row.tenant_id,
        "facility_id": row.facility_id,
        "hypothesis_code": row.hypothesis_code,
        "discovery_category": row.discovery_category,
        "title": row.title,
        "observation_summary": row.observation_summary,
        "hypothesis_statement": row.hypothesis_statement,
        "supporting_literature": json.loads(row.supporting_literature_json or "[]"),
        "related_instruments": json.loads(row.related_instruments_json or "[]"),
        "related_anatomy": json.loads(row.related_anatomy_json or "[]"),
        "digital_twin_refs": json.loads(row.digital_twin_refs_json or "[]"),
        "knowledge_links": json.loads(row.knowledge_links_json or "[]"),
        "evidence": json.loads(row.evidence_json or "[]"),
        "statistical_summary": json.loads(row.statistical_summary_json or "{}"),
        "sample_size": row.sample_size,
        "confidence_level": row.confidence_level,
        "current_stage": row.current_stage,
        "research_owner": row.research_owner,
        "outcome": row.outcome,
        "outcome_summary": row.outcome_summary,
        "rejected_reason": row.rejected_reason,
        "human_review_required": row.human_review_required,
        "agent_version": row.agent_version,
        "disclaimer": row.disclaimer,
    }


def create_hypothesis(
    db: Session, tenant_id: str, *, discovery_category: str, title: str, observation_summary: str = "",
    hypothesis_statement: str = "", facility_id: str = "", research_owner: str = "",
    related_instruments: list[str] | None = None, related_anatomy: list[str] | None = None,
    supporting_literature: list[str] | None = None, sample_size: int | None = None,
    statistical_summary: dict | None = None, changed_by: str = "", changed_by_role: str = "",
) -> OracleHypothesis:
    """Section 3: every discovery starts life as an OBSERVATION -- Oracle
    never creates a hypothesis directly at a later pipeline stage."""
    if discovery_category not in DISCOVERY_CATEGORIES:
        raise ValueError(f"Unknown discovery category: {discovery_category}")
    if not title.strip():
        raise ValueError("A hypothesis requires a title.")

    row = OracleHypothesis(
        tenant_id=tenant_id, facility_id=facility_id, discovery_category=discovery_category, title=title.strip(),
        observation_summary=observation_summary, hypothesis_statement=hypothesis_statement,
        research_owner=research_owner,
        related_instruments_json=json.dumps(related_instruments or []),
        related_anatomy_json=json.dumps(related_anatomy or []),
        supporting_literature_json=json.dumps(supporting_literature or []),
        statistical_summary_json=json.dumps(statistical_summary or {}),
        sample_size=sample_size, current_stage=STAGE_OBSERVATION, confidence_level=CONFIDENCE_EXPLORATORY,
        disclaimer=DISCLAIMER,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.hypothesis_code = f"ORC-{row.id:05d}"
    db.add(OracleStageTransition(
        tenant_id=tenant_id, hypothesis_id=row.id, from_stage="", to_stage=STAGE_OBSERVATION,
        changed_by=changed_by, changed_by_role=changed_by_role, reason="Observation recorded; hypothesis opened.",
    ))
    db.commit()
    db.refresh(row)
    return row


def get_hypothesis(db: Session, tenant_id: str, hypothesis_id: int) -> OracleHypothesis | None:
    return db.query(OracleHypothesis).filter(
        OracleHypothesis.tenant_id == tenant_id, OracleHypothesis.id == hypothesis_id,
    ).first()


def list_hypotheses(
    db: Session, tenant_id: str, *, discovery_category: str = "", current_stage: str = "",
    confidence_level: str = "", research_owner: str = "", outcome: str = "",
) -> list[dict]:
    q = db.query(OracleHypothesis).filter(OracleHypothesis.tenant_id == tenant_id)
    if discovery_category:
        q = q.filter(OracleHypothesis.discovery_category == discovery_category)
    if current_stage:
        q = q.filter(OracleHypothesis.current_stage == current_stage)
    if confidence_level:
        q = q.filter(OracleHypothesis.confidence_level == confidence_level)
    if research_owner:
        q = q.filter(OracleHypothesis.research_owner == research_owner)
    if outcome:
        q = q.filter(OracleHypothesis.outcome == outcome)
    return [to_dict(r) for r in q.order_by(OracleHypothesis.created_at.desc()).all()]


def add_evidence(
    db: Session, tenant_id: str, hypothesis_id: int, *, evidence_summary: str, submitted_by: str,
    evidence_type: str = "observation",
) -> OracleHypothesis:
    """Section 11: append one piece of supporting/contradicting evidence.
    Evidence is append-only -- prior entries are never edited or removed,
    so a hypothesis's full evidentiary history stays reconstructable."""
    row = get_hypothesis(db, tenant_id, hypothesis_id)
    if row is None:
        raise ValueError("Hypothesis not found")
    if not evidence_summary.strip():
        raise ValueError("Evidence requires a non-empty summary.")
    evidence = json.loads(row.evidence_json or "[]")
    evidence.append({
        "evidence_type": evidence_type, "summary": evidence_summary, "submitted_by": submitted_by,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    row.evidence_json = json.dumps(evidence)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def link_supporting_literature(db: Session, tenant_id: str, hypothesis_id: int, *, reference: str) -> OracleHypothesis:
    row = get_hypothesis(db, tenant_id, hypothesis_id)
    if row is None:
        raise ValueError("Hypothesis not found")
    refs = json.loads(row.supporting_literature_json or "[]")
    if reference not in refs:
        refs.append(reference)
    row.supporting_literature_json = json.dumps(refs)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def link_knowledge_reference(db: Session, tenant_id: str, hypothesis_id: int, *, knowledge_ref: dict) -> OracleHypothesis:
    """Records a link to a `OracleKnowledgeSuggestion` or a real
    `KnowledgeArticle` id -- called by `oracle_knowledge_evolution_service`,
    never used to write knowledge directly."""
    row = get_hypothesis(db, tenant_id, hypothesis_id)
    if row is None:
        raise ValueError("Hypothesis not found")
    links = json.loads(row.knowledge_links_json or "[]")
    links.append(knowledge_ref)
    row.knowledge_links_json = json.dumps(links)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def link_digital_twin_ref(db: Session, tenant_id: str, hypothesis_id: int, *, twin_insight_id: int) -> OracleHypothesis:
    row = get_hypothesis(db, tenant_id, hypothesis_id)
    if row is None:
        raise ValueError("Hypothesis not found")
    refs = json.loads(row.digital_twin_refs_json or "[]")
    if twin_insight_id not in refs:
        refs.append(twin_insight_id)
    row.digital_twin_refs_json = json.dumps(refs)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def set_confidence_level(
    db: Session, tenant_id: str, hypothesis_id: int, *, confidence_level: str, changed_by: str = "",
    changed_by_role: str = "", reason: str = "",
) -> OracleHypothesis:
    """Section 5: confidence is graded, never binary -- moving it up or
    down is itself an auditable event, since it directly affects what
    downstream review a hypothesis receives."""
    if confidence_level not in CONFIDENCE_LEVELS:
        raise ValueError(f"Unknown confidence level: {confidence_level}")
    row = get_hypothesis(db, tenant_id, hypothesis_id)
    if row is None:
        raise ValueError("Hypothesis not found")
    row.confidence_level = confidence_level
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    db.add(OracleStageTransition(
        tenant_id=tenant_id, hypothesis_id=row.id, from_stage=row.current_stage, to_stage=row.current_stage,
        changed_by=changed_by, changed_by_role=changed_by_role,
        reason=reason or f"Confidence level updated to {confidence_level}.",
    ))
    db.commit()
    return row
