"""LCID Sprint 1 — Section 2/9: permanent Dataset IDs and Digital Twin linkage.

Generates the permanent, human-readable `LCID-YYYY-NNNNNNNNN` identifier
required by Section 2 ("The ID must never change") and resolves the Digital
Twin / baseline linkage required by Section 9, reusing the physical-
instrument identity already computed by
`pre_sterilization_command_center_service._instrument_identity` rather than
inventing a second, disconnected concept of "digital twin."
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.baseline_library import BaselineLibraryEntry
from app.models.dataset_governance import LcidSequenceCounter

LCID_PREFIX = "LCID"
_SEQUENCE_WIDTH = 9


def generate_lcid(db: Session, *, at: datetime | None = None) -> str:
    """Atomically allocate the next LCID for the current (or given) year.

    Uses a dedicated per-year counter row rather than counting existing
    entries, so a deleted/archived entry never causes an ID to be reused —
    "the ID must never change" and, implicitly, never collides either.
    """
    year = (at or datetime.now(timezone.utc)).year
    counter = db.query(LcidSequenceCounter).filter(LcidSequenceCounter.year == year).first()
    if counter is None:
        counter = LcidSequenceCounter(year=year, last_sequence=0)
        db.add(counter)
        db.flush()

    counter.last_sequence += 1
    db.flush()
    return f"{LCID_PREFIX}-{year}-{counter.last_sequence:0{_SEQUENCE_WIDTH}d}"


def instrument_digital_twin_id(*, instrument_barcode: str | None, instrument_udi: str | None, instrument_type: str, inspection_id: int | None) -> str:
    """The same barcode/UDI-based physical-instrument identity used
    elsewhere in this codebase (readiness_engine.has_repair_history) — never
    a fabricated re-identification when no real identifier was captured."""
    if instrument_barcode:
        return f"barcode:{instrument_barcode}"
    if instrument_udi:
        return f"udi:{instrument_udi}"
    return f"untracked:{instrument_type}:{inspection_id if inspection_id is not None else 'unknown'}"


def is_untracked_twin(digital_twin_id: str) -> bool:
    return digital_twin_id.startswith("untracked:") or not digital_twin_id


def digital_twin_history(db: Session, *, tenant_id: str, digital_twin_id: str) -> dict:
    """Section 9 — everything this dataset already links for a given
    physical-instrument identity: its other registered dataset images,
    inspection history, and repair history (reusing the real
    barcode/UDI-based Inspection query, not a fabricated twin record)."""
    from app.db import models
    from app.models.dataset_governance import DatasetRegistryEntry

    dataset_images = (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.tenant_id == tenant_id, DatasetRegistryEntry.digital_twin_id == digital_twin_id)
        .order_by(DatasetRegistryEntry.created_at.asc())
        .all()
    )

    inspections: list = []
    if digital_twin_id.startswith("barcode:"):
        barcode = digital_twin_id.split(":", 1)[1]
        inspections = (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.instrument_barcode == barcode)
            .order_by(models.Inspection.created_at.asc())
            .all()
        )
    elif digital_twin_id.startswith("udi:"):
        udi = digital_twin_id.split(":", 1)[1]
        inspections = (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.instrument_udi == udi)
            .order_by(models.Inspection.created_at.asc())
            .all()
        )

    repair_history_count = sum(1 for i in inspections if (i.disposition or "") == "REMOVE FROM SERVICE")

    return {
        "digital_twin_id": digital_twin_id,
        "is_tracked": not is_untracked_twin(digital_twin_id),
        "historical_image_count": len(dataset_images),
        "historical_image_lcids": [e.lcid for e in dataset_images],
        "inspection_history_count": len(inspections),
        "repair_history_count": repair_history_count,
    }


def resolve_baseline_id(db: Session, *, instrument_type: str, manufacturer: str = "") -> int | None:
    """Best-effort real baseline lookup (approved entries only) — returns
    None rather than a guessed ID when nothing approved exists, mirroring
    `baseline_comparison_scoring_service.resolve_baseline`'s own honesty
    contract."""
    query = db.query(BaselineLibraryEntry).filter(
        BaselineLibraryEntry.instrument_category == instrument_type,
        BaselineLibraryEntry.approval_status == "approved",
    )
    if manufacturer:
        query = query.filter(BaselineLibraryEntry.manufacturer_name == manufacturer)
    entry = query.first()
    return entry.id if entry is not None else None
