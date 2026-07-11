"""v5.2 — Project GuardianX, Section 3: Explainability Dashboard.

`AIExplainabilityRecord` is referenced by `source_type`/`source_id`
rather than copying the underlying AI output, the same reference-only
pattern already used by `HIXExchangePackage` (Olympus). Digital Twin
Context reuses Phoenix's `compute_digital_twin_health_score`
(`phoenix_platform_health_service.py`, v4.9) directly rather than a
second Digital Twin summarizer -- never re-queries
`digital_twin_engine` from scratch.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import AIExplainabilityRecord
from app.services import phoenix_platform_health_service


class UnknownExplainabilityRecordError(Exception):
    pass


def _to_dict(record: AIExplainabilityRecord) -> dict:
    return {
        "id": record.id,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "input_summary": record.input_summary,
        "evidence_used": json.loads(record.evidence_used_json or "[]"),
        "knowledge_sources": json.loads(record.knowledge_sources_json or "[]"),
        "digital_twin_context": json.loads(record.digital_twin_context_json or "{}"),
        "clinical_rules_applied": json.loads(record.clinical_rules_applied_json or "[]"),
        "confidence": record.confidence,
        "alternative_explanations": json.loads(record.alternative_explanations_json or "[]"),
        "human_overrides": json.loads(record.human_overrides_json or "[]"),
        "created_by": record.created_by,
        "created_at": record.created_at.isoformat(),
    }


def create_explanation(
    db: Session, *, source_type: str, source_id: str, input_summary: str = "",
    evidence_used: list[str] | None = None, knowledge_sources: list[str] | None = None,
    tenant_id_for_digital_twin: str = "", clinical_rules_applied: list[str] | None = None,
    confidence: float | None = None, alternative_explanations: list[str] | None = None,
    human_overrides: list[str] | None = None, created_by: str = "",
) -> dict:
    digital_twin_context: dict = {}
    if tenant_id_for_digital_twin:
        digital_twin_context = phoenix_platform_health_service.compute_digital_twin_health_score(
            db, tenant_id_for_digital_twin,
        )

    row = AIExplainabilityRecord(
        source_type=source_type, source_id=source_id, input_summary=input_summary,
        evidence_used_json=json.dumps(evidence_used or []),
        knowledge_sources_json=json.dumps(knowledge_sources or []),
        digital_twin_context_json=json.dumps(digital_twin_context),
        clinical_rules_applied_json=json.dumps(clinical_rules_applied or []),
        confidence=confidence,
        alternative_explanations_json=json.dumps(alternative_explanations or []),
        human_overrides_json=json.dumps(human_overrides or []),
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_or_404(db: Session, record_id: int) -> AIExplainabilityRecord:
    row = db.query(AIExplainabilityRecord).filter(AIExplainabilityRecord.id == record_id).first()
    if row is None:
        raise UnknownExplainabilityRecordError(f"Explainability record {record_id} not found.")
    return row


def get_explanation(db: Session, record_id: int) -> dict:
    return _to_dict(_get_or_404(db, record_id))


def record_human_override(db: Session, record_id: int, *, override_note: str, overridden_by: str) -> dict:
    row = _get_or_404(db, record_id)
    overrides = json.loads(row.human_overrides_json or "[]")
    overrides.append({"note": override_note, "overridden_by": overridden_by})
    row.human_overrides_json = json.dumps(overrides)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_explanations_for_source(db: Session, source_type: str, source_id: str) -> list[dict]:
    rows = (
        db.query(AIExplainabilityRecord)
        .filter(AIExplainabilityRecord.source_type == source_type, AIExplainabilityRecord.source_id == source_id)
        .order_by(AIExplainabilityRecord.created_at.desc())
        .all()
    )
    return [_to_dict(r) for r in rows]
