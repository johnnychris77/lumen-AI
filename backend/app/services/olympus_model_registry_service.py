"""v5.1 — Project Olympus, Section 6: AI Model Registry.

Nothing in this codebase tracks an AI model as a first-class, versioned
registry object -- Sentinel's AI health service reports live operational
health, and Phoenix's `AIInferenceLatencySample` is a performance sample,
not a model identity. `AIModelRegistryEntry` is genuinely new, with a
`supersedes_id` self-FK forming a real version chain, the same pattern
already used by `QualityPolicy` (Apollo) and `StandardsPublication` (P24).
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.olympus_network import AI_MODEL_TYPES, MODEL_VALIDATION_STATUSES, AIModelRegistryEntry


class UnknownModelRegistryEntryError(Exception):
    pass


def model_row_to_dict(entry: AIModelRegistryEntry) -> dict:
    return {
        "id": entry.id,
        "model_type": entry.model_type,
        "name": entry.name,
        "version": entry.version,
        "supersedes_id": entry.supersedes_id,
        "validation_status": entry.validation_status,
        "clinical_scope": entry.clinical_scope,
        "evidence": json.loads(entry.evidence_json or "[]"),
        "performance_metrics": json.loads(entry.performance_metrics_json or "{}"),
        "certification_status": entry.certification_status,
        "certification_chain_id": entry.certification_chain_id,
        "certification_instance_id": entry.certification_instance_id,
        "registered_by": entry.registered_by,
        "human_review_required": entry.human_review_required,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def get_model_or_404(db: Session, entry_id: int) -> AIModelRegistryEntry:
    row = db.query(AIModelRegistryEntry).filter(AIModelRegistryEntry.id == entry_id).first()
    if row is None:
        raise UnknownModelRegistryEntryError(f"AI model registry entry {entry_id} not found.")
    return row


def register_model(
    db: Session, *, model_type: str, name: str, version: str, clinical_scope: str,
    evidence: list[str] | None = None, performance_metrics: dict | None = None,
    registered_by: str, supersedes_id: int | None = None,
) -> dict:
    if model_type not in AI_MODEL_TYPES:
        raise ValueError(f"model_type must be one of {AI_MODEL_TYPES}")
    if supersedes_id is not None:
        get_model_or_404(db, supersedes_id)
    row = AIModelRegistryEntry(
        model_type=model_type, name=name, version=version, supersedes_id=supersedes_id,
        clinical_scope=clinical_scope, evidence_json=json.dumps(evidence or []),
        performance_metrics_json=json.dumps(performance_metrics or {}), registered_by=registered_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return model_row_to_dict(row)


def set_validation_status(db: Session, entry_id: int, *, validation_status: str) -> dict:
    if validation_status not in MODEL_VALIDATION_STATUSES:
        raise ValueError(f"validation_status must be one of {MODEL_VALIDATION_STATUSES}")
    row = get_model_or_404(db, entry_id)
    row.validation_status = validation_status
    db.commit()
    db.refresh(row)
    return model_row_to_dict(row)


def get_model(db: Session, entry_id: int) -> dict:
    return model_row_to_dict(get_model_or_404(db, entry_id))


def list_models(db: Session, *, model_type: str = "", validation_status: str = "") -> list[dict]:
    query = db.query(AIModelRegistryEntry)
    if model_type:
        if model_type not in AI_MODEL_TYPES:
            raise ValueError(f"model_type must be one of {AI_MODEL_TYPES}")
        query = query.filter(AIModelRegistryEntry.model_type == model_type)
    if validation_status:
        query = query.filter(AIModelRegistryEntry.validation_status == validation_status)
    rows = query.order_by(AIModelRegistryEntry.created_at.desc()).all()
    return [model_row_to_dict(r) for r in rows]


def version_chain(db: Session, entry_id: int) -> list[dict]:
    """Walks backward through `supersedes_id`, oldest first -- the same
    version-chain-walker pattern used by Beacon/Forge/Apollo."""
    chain: list[AIModelRegistryEntry] = []
    current: AIModelRegistryEntry | None = get_model_or_404(db, entry_id)
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        chain.append(current)
        current = (
            db.query(AIModelRegistryEntry).filter(AIModelRegistryEntry.id == current.supersedes_id).first()
            if current.supersedes_id is not None else None
        )
    return [model_row_to_dict(r) for r in reversed(chain)]
