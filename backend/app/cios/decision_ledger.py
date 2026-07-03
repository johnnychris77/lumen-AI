"""Phase 23 §5 — Clinical Decision Ledger service.

Records and reads ClinicalDecisionLedgerEntry rows. Every entry snapshots
the governance versions active at the moment it was recorded — see
app/cios/governance.py.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.cios.governance import governance_snapshot
from app.models.clinical_decision_ledger import ClinicalDecisionLedgerEntry


def record_decision(
    db: Session,
    tenant_id: str,
    inspection_id: int,
    decision_type: str,
    made_by: str,
    rationale: str = "",
    evidence: dict | None = None,
    confidence: float | None = None,
) -> ClinicalDecisionLedgerEntry:
    versions = governance_snapshot()
    entry = ClinicalDecisionLedgerEntry(
        tenant_id=tenant_id,
        inspection_id=inspection_id,
        decision_type=decision_type,
        made_by=made_by,
        rationale=rationale,
        evidence_json=json.dumps(evidence or {}, default=str),
        confidence=confidence,
        model_version=versions["model_version"],
        knowledge_graph_version=versions["knowledge_graph_version"],
        ontology_version=versions["ontology_version"],
        architecture_version=versions["architecture_version"],
        inspection_pipeline_version=versions["inspection_pipeline_version"],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_decisions(db: Session, tenant_id: str, inspection_id: int) -> list[dict]:
    rows = (
        db.query(ClinicalDecisionLedgerEntry)
        .filter(
            ClinicalDecisionLedgerEntry.tenant_id == tenant_id,
            ClinicalDecisionLedgerEntry.inspection_id == inspection_id,
        )
        .order_by(ClinicalDecisionLedgerEntry.created_at.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "decision_type": r.decision_type,
            "made_by": r.made_by,
            "rationale": r.rationale,
            "evidence": json.loads(r.evidence_json or "{}"),
            "confidence": r.confidence,
            "model_version": r.model_version,
            "knowledge_graph_version": r.knowledge_graph_version,
            "ontology_version": r.ontology_version,
            "architecture_version": r.architecture_version,
            "inspection_pipeline_version": r.inspection_pipeline_version,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
