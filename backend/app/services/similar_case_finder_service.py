"""v1.8 — Similar Case Finder (Deliverable 5).

When the AI detects a finding, surfaces prior real cases on the same
instrument family with the same finding type — previous images (via the
originating inspection), previous recommendations, supervisor outcomes,
and any educational notes attached. Matches on instrument *family* (not
exact instrument_type) so a Kerrison from one manufacturer surfaces a
similar case from another, since anatomy — not brand — drives the finding.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge import ClinicalCase
from app.services.clinical_case_library_service import case_to_dict
from app.services.instrument_anatomy import resolve_family


def find_similar_cases(
    db: Session, tenant_id: str, *, instrument_type: str, finding_type: str, exclude_inspection_id: int | None = None,
    limit: int = 5,
) -> list[dict]:
    family = resolve_family(instrument_type)
    rows = (
        db.query(ClinicalCase)
        .filter(ClinicalCase.tenant_id == tenant_id, ClinicalCase.finding_type == finding_type)
        .order_by(ClinicalCase.id.desc())
        .all()
    )
    matches = [
        r for r in rows
        if resolve_family(r.instrument_type) == family and r.inspection_id != exclude_inspection_id
    ]
    return [case_to_dict(r) for r in matches[:limit]]
