"""v2.4 — Similar Instrument Search (Clinical Memory, Section 2).

Fleet-wide: given one physical instrument, finds OTHER physical instruments
in this tenant that resemble it and returns a 0-1 similarity score. Distinct
from `similar_case_finder_service.find_similar_cases`, which matches a single
finding to prior `ClinicalCase` snapshots — this compares whole instruments
across type, declared vendor (the closest thing to "manufacturer" the
`Inspection` record carries — there is no separate model field), resolved
anatomy family, and overlapping finding types (including contamination/damage
patterns).

"Untracked" instruments (no barcode/UDI — see `_instrument_identity`) are
per-inspection singletons, not re-identified physical instruments, so they're
excluded from this comparison rather than compared as if they were real.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_finding import InspectionFinding
from app.services.instrument_anatomy import resolve_family
from app.services.pre_sterilization_command_center_service import _instrument_identity
from app.services.recurrence_detection_service import CONTAMINATION_TYPES, DAMAGE_TYPES


def _rows_for_identity(db: Session, tenant_id: str, instrument_identity: str) -> list:
    if instrument_identity.startswith("barcode:"):
        value = instrument_identity.removeprefix("barcode:")
        column = models.Inspection.instrument_barcode
    elif instrument_identity.startswith("udi:"):
        value = instrument_identity.removeprefix("udi:")
        column = models.Inspection.instrument_udi
    else:
        return []
    return (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, column == value)
        .order_by(models.Inspection.created_at.asc())
        .all()
    )


def _finding_types(db: Session, inspection_ids: list[int]) -> set[str]:
    if not inspection_ids:
        return set()
    rows = (
        db.query(InspectionFinding.finding_type)
        .filter(InspectionFinding.inspection_id.in_(inspection_ids))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def find_similar_instruments(db: Session, tenant_id: str, *, instrument_identity: str, limit: int = 5) -> list[dict]:
    target_rows = _rows_for_identity(db, tenant_id, instrument_identity)
    if not target_rows:
        return []

    target_type = target_rows[-1].instrument_type
    target_vendor = target_rows[-1].vendor_name
    target_family = resolve_family(target_type)
    target_findings = _finding_types(db, [r.id for r in target_rows])

    all_rows = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).all()
    by_identity: dict[str, list] = defaultdict(list)
    for row in all_rows:
        by_identity[_instrument_identity(row)].append(row)
    by_identity.pop(instrument_identity, None)
    by_identity = {k: v for k, v in by_identity.items() if not k.startswith("untracked:")}

    candidates = []
    for identity, rows in by_identity.items():
        rows_sorted = sorted(rows, key=lambda r: (r.created_at or r.id))
        cand_type = rows_sorted[-1].instrument_type
        cand_vendor = rows_sorted[-1].vendor_name
        cand_family = resolve_family(cand_type)
        cand_findings = _finding_types(db, [r.id for r in rows_sorted])

        score = 0.0
        if cand_type == target_type:
            score += 0.3
        if cand_family == target_family:
            score += 0.2
        if cand_vendor == target_vendor and target_vendor != "unknown":
            score += 0.15

        shared_findings = target_findings & cand_findings
        union_findings = target_findings | cand_findings
        if union_findings:
            score += 0.2 * (len(shared_findings) / len(union_findings))
        if shared_findings & CONTAMINATION_TYPES:
            score += 0.075
        if shared_findings & DAMAGE_TYPES:
            score += 0.075

        if score <= 0:
            continue
        candidates.append({
            "instrument_identity": identity,
            "instrument_type": cand_type,
            "vendor_name": cand_vendor,
            "similarity_score": round(min(1.0, score), 2),
            "shared_finding_types": sorted(shared_findings),
            "inspection_count": len(rows_sorted),
        })

    candidates.sort(key=lambda c: c["similarity_score"], reverse=True)
    return candidates[:limit]
