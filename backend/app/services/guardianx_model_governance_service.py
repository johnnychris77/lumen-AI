"""v5.2 — Project GuardianX, Section 2: Model Governance.

Extends Olympus's `AIModelRegistryEntry` (`olympus_model_registry_service.py`,
v5.1) directly -- reuses its `get_model_or_404`/`model_row_to_dict` helpers
rather than a parallel model-lookup path. Every setter here only touches
the new GuardianX governance columns; it never re-implements
`register_model`/`version_chain`/certification, which stay owned by
`olympus_model_registry_service.py` and `olympus_certification_registry_service.py`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.olympus_network import AIModelRegistryEntry
from app.services.olympus_model_registry_service import get_model_or_404, model_row_to_dict


def _governance_dict(entry) -> dict:
    base = model_row_to_dict(entry)
    base.update({
        "model_owner": entry.model_owner,
        "clinical_owner": entry.clinical_owner,
        "technical_owner": entry.technical_owner,
        "approval_committee": entry.approval_committee,
        "validation_date": entry.validation_date.isoformat() if entry.validation_date else None,
        "retirement_date": entry.retirement_date.isoformat() if entry.retirement_date else None,
        "training_dataset_metadata": json.loads(entry.training_dataset_metadata_json or "{}"),
        "known_limitations": entry.known_limitations,
        "approved_use_cases": json.loads(entry.approved_use_cases_json or "[]"),
        "out_of_scope_uses": json.loads(entry.out_of_scope_uses_json or "[]"),
        "governance_status": entry.governance_status,
        "governance_chain_id": entry.governance_chain_id,
        "governance_instance_id": entry.governance_instance_id,
    })
    return base


def set_ownership(db: Session, model_id: int, *, model_owner: str = "", clinical_owner: str = "", technical_owner: str = "", approval_committee: str = "") -> dict:
    entry = get_model_or_404(db, model_id)
    if model_owner:
        entry.model_owner = model_owner
    if clinical_owner:
        entry.clinical_owner = clinical_owner
    if technical_owner:
        entry.technical_owner = technical_owner
    if approval_committee:
        entry.approval_committee = approval_committee
    db.commit()
    db.refresh(entry)
    return _governance_dict(entry)


def set_validation_date(db: Session, model_id: int) -> dict:
    entry = get_model_or_404(db, model_id)
    entry.validation_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return _governance_dict(entry)


def retire_model(db: Session, model_id: int) -> dict:
    entry = get_model_or_404(db, model_id)
    entry.retirement_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return _governance_dict(entry)


def set_training_dataset_metadata(db: Session, model_id: int, metadata: dict) -> dict:
    entry = get_model_or_404(db, model_id)
    entry.training_dataset_metadata_json = json.dumps(metadata)
    db.commit()
    db.refresh(entry)
    return _governance_dict(entry)


def set_known_limitations(db: Session, model_id: int, known_limitations: str) -> dict:
    entry = get_model_or_404(db, model_id)
    entry.known_limitations = known_limitations
    db.commit()
    db.refresh(entry)
    return _governance_dict(entry)


def set_use_cases(db: Session, model_id: int, *, approved_use_cases: list[str] | None = None, out_of_scope_uses: list[str] | None = None) -> dict:
    entry = get_model_or_404(db, model_id)
    if approved_use_cases is not None:
        entry.approved_use_cases_json = json.dumps(approved_use_cases)
    if out_of_scope_uses is not None:
        entry.out_of_scope_uses_json = json.dumps(out_of_scope_uses)
    db.commit()
    db.refresh(entry)
    return _governance_dict(entry)


def get_governance_record(db: Session, model_id: int) -> dict:
    return _governance_dict(get_model_or_404(db, model_id))


def list_governance_records(db: Session) -> list[dict]:
    rows = db.query(AIModelRegistryEntry).order_by(AIModelRegistryEntry.created_at.desc()).all()
    return [_governance_dict(r) for r in rows]
