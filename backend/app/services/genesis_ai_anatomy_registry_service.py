"""v5.3 — Project Genesis AI, Section 2: Global Anatomy Registry.

`AnatomyProfile` is the standardization taxonomy this codebase never had
-- every existing `zone`/`instrument_type` field elsewhere is free text.
This module owns the taxonomy CRUD only; it never rewrites existing
free-text fields on `Inspection`/`InspectionFinding`.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.genesis_ai_intelligence_cloud import ANATOMY_PROFILE_TYPES, AnatomyProfile


class UnknownAnatomyProfileError(Exception):
    pass


def _to_dict(row: AnatomyProfile) -> dict:
    return {
        "id": row.id,
        "profile_type": row.profile_type,
        "name": row.name,
        "description": row.description,
        "standard_terminology": json.loads(row.standard_terminology_json or "[]"),
        "zones": json.loads(row.zones_json or "[]"),
        "created_at": row.created_at.isoformat(),
    }


def create_anatomy_profile(
    db: Session, *, profile_type: str, name: str, description: str = "",
    standard_terminology: list[str] | None = None, zones: list[str] | None = None,
) -> dict:
    if profile_type not in ANATOMY_PROFILE_TYPES:
        raise ValueError(f"profile_type must be one of {ANATOMY_PROFILE_TYPES}")
    row = AnatomyProfile(
        profile_type=profile_type, name=name, description=description,
        standard_terminology_json=json.dumps(standard_terminology or []), zones_json=json.dumps(zones or []),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_or_404(db: Session, profile_id: int) -> AnatomyProfile:
    row = db.query(AnatomyProfile).filter(AnatomyProfile.id == profile_id).first()
    if row is None:
        raise UnknownAnatomyProfileError(f"Anatomy profile {profile_id} not found.")
    return row


def get_anatomy_profile(db: Session, profile_id: int) -> dict:
    return _to_dict(_get_or_404(db, profile_id))


def list_anatomy_profiles(db: Session, *, profile_type: str = "") -> list[dict]:
    query = db.query(AnatomyProfile)
    if profile_type:
        if profile_type not in ANATOMY_PROFILE_TYPES:
            raise ValueError(f"profile_type must be one of {ANATOMY_PROFILE_TYPES}")
        query = query.filter(AnatomyProfile.profile_type == profile_type)
    rows = query.order_by(AnatomyProfile.created_at.desc()).all()
    return [_to_dict(r) for r in rows]


def anatomy_registry_summary(db: Session) -> dict:
    rows = db.query(AnatomyProfile).all()
    by_type: dict[str, int] = {t: 0 for t in ANATOMY_PROFILE_TYPES}
    for r in rows:
        by_type[r.profile_type] = by_type.get(r.profile_type, 0) + 1
    return {"profile_types": ANATOMY_PROFILE_TYPES, "total_profiles": len(rows), "by_profile_type": by_type}
