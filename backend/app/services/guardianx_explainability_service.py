"""v5.2 — Project GuardianX, Section 3: Explainability Dashboard.

`AIExplainabilityRecord` is referenced by `source_type`/`source_id`
rather than copying the underlying AI output, the same reference-only
pattern already used by `HIXExchangePackage` (Olympus). Digital Twin
Context reuses Phoenix's `compute_digital_twin_health_score`
(`phoenix_platform_health_service.py`, v4.9) directly rather than a
second Digital Twin summarizer -- never re-queries
`digital_twin_engine` from scratch.

P472-03 Batch 8 (RB-T32, GX-11..GX-13): every creation and human override
records a hash-chained audit event under the writer's verified tenant, and
every read or amendment is limited to the explanation's provable owner
(`guardianx_source_ownership.explanation_owner`). A row with no provable owner
is served to no tenant. A missing and a foreign explanation are
indistinguishable (`UnknownExplainabilityRecordError` -> 404).
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import AIExplainabilityRecord
from app.services import guardianx_source_ownership as ownership
from app.services import phoenix_platform_health_service
from app.services.enterprise_audit_service import record_enterprise_audit_event


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
    human_overrides: list[str] | None = None, created_by: str = "", tenant_id: str,
) -> dict:
    if not (tenant_id or "").strip():
        raise ownership.SourceWriteRefusedError("No verified tenant for this request.")
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
    db.flush()
    # Row and its ownership event commit together: an explanation never exists
    # without the audit event that attributes it.
    record_enterprise_audit_event(
        db, action_type="guardianx.explanation_recorded", resource_type=ownership.EXPLANATION_RESOURCE_TYPE,
        resource_id=str(row.id), actor=created_by or "unknown", actor_email=created_by or None,
        tenant_id=tenant_id, details={"source_type": source_type, "source_id": source_id}, commit=False,
    )
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_owned_or_404(db: Session, record_id: int, tenant_id: str) -> AIExplainabilityRecord:
    row = db.query(AIExplainabilityRecord).filter(AIExplainabilityRecord.id == record_id).first()
    if row is None or not ownership.explanation_readable_by(db, row.id, tenant_id):
        raise UnknownExplainabilityRecordError(f"Explainability record {record_id} not found.")
    return row


def get_explanation(db: Session, record_id: int, *, tenant_id: str) -> dict:
    return _to_dict(_get_owned_or_404(db, record_id, tenant_id))


def record_human_override(db: Session, record_id: int, *, override_note: str, overridden_by: str,
                          tenant_id: str) -> dict:
    row = _get_owned_or_404(db, record_id, tenant_id)
    overrides = json.loads(row.human_overrides_json or "[]")
    overrides.append({"note": override_note, "overridden_by": overridden_by})
    row.human_overrides_json = json.dumps(overrides)
    record_enterprise_audit_event(
        db, action_type="guardianx.explanation_overridden", resource_type=ownership.EXPLANATION_RESOURCE_TYPE,
        resource_id=str(row.id), actor=overridden_by or "unknown", actor_email=overridden_by or None,
        tenant_id=tenant_id, details={"override_count": len(overrides)}, commit=False,
    )
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_explanations_for_source(db: Session, source_type: str, source_id: str, tenant_id: str) -> list[dict]:
    """Explanations of a source that the verified tenant provably owns; nothing without a tenant."""
    if not (tenant_id or "").strip():
        return []
    rows = (
        db.query(AIExplainabilityRecord)
        .filter(AIExplainabilityRecord.source_type == source_type, AIExplainabilityRecord.source_id == source_id)
        .order_by(AIExplainabilityRecord.created_at.desc())
        .all()
    )
    return [_to_dict(r) for r in rows if ownership.explanation_readable_by(db, r.id, tenant_id)]
