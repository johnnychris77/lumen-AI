"""Project Veritas, Section 9: Conflict Detection.

Each detector is a small, deterministic comparison over real inputs already
computed by the other Veritas services (match classification, coverage,
governance status) or supplied by the caller (supervisor/AI labels,
timestamps) -- never a fabricated inference.
"""
from __future__ import annotations

from app.models.veritas_evidence import (
    CONFLICT_BASELINE_SUPERSEDED_AFTER_INSPECTION,
    CONFLICT_DUPLICATE_IMAGE_DIFFERENT_ZONES,
    CONFLICT_EVIDENCE_TIMESTAMP_INCONSISTENCY,
    CONFLICT_IMAGE_TAG_DIFFERS,
    CONFLICT_INSTRUMENT_FAMILY_DIFFERS,
    CONFLICT_MANUFACTURER_DIFFERS,
    CONFLICT_MODEL_NOT_APPROVED,
    CONFLICT_MULTIPLE_ACTIVE_BASELINES,
    CONFLICT_SUPERVISOR_LABEL_CONFLICT,
    MATCH_MISMATCH,
)


def _conflict(conflict_type: str, *, severity: str, affected_evidence: dict, recommended_resolution: str, responsible_reviewer_role: str) -> dict:
    return {
        "conflict_type": conflict_type, "severity": severity, "affected_evidence": affected_evidence,
        "recommended_resolution": recommended_resolution, "responsible_reviewer_role": responsible_reviewer_role,
    }


def detect_conflicts(
    *, match_classification: str = "", instrument_manufacturer: str = "", baseline_manufacturer: str = "",
    ai_zone: str = "", tagged_zone: str = "", supervisor_label: str = "", ai_label: str = "",
    model_approved_for_family: bool = True, baseline_superseded_after_inspection: bool = False,
    duplicate_image_zones: list[str] | None = None, timestamp_inconsistent: bool = False,
    multiple_active_baselines: bool = False,
) -> list[dict]:
    conflicts: list[dict] = []

    if match_classification == MATCH_MISMATCH:
        conflicts.append(_conflict(
            CONFLICT_INSTRUMENT_FAMILY_DIFFERS, severity="high",
            affected_evidence={"match_classification": match_classification},
            recommended_resolution="Resolve a baseline matching this instrument's actual anatomy family before scoring.",
            responsible_reviewer_role="baseline_reviewer",
        ))

    if ai_zone and tagged_zone and ai_zone != tagged_zone:
        conflicts.append(_conflict(
            CONFLICT_IMAGE_TAG_DIFFERS, severity="moderate",
            affected_evidence={"ai_zone": ai_zone, "tagged_zone": tagged_zone},
            recommended_resolution="Supervisor to confirm the correct anatomy zone for this image.",
            responsible_reviewer_role="supervisor",
        ))

    if instrument_manufacturer and baseline_manufacturer and instrument_manufacturer.strip().lower() != baseline_manufacturer.strip().lower():
        conflicts.append(_conflict(
            CONFLICT_MANUFACTURER_DIFFERS, severity="high",
            affected_evidence={"instrument_manufacturer": instrument_manufacturer, "baseline_manufacturer": baseline_manufacturer},
            recommended_resolution="Confirm instrument manufacturer/model before using this baseline.",
            responsible_reviewer_role="baseline_reviewer",
        ))

    if multiple_active_baselines:
        conflicts.append(_conflict(
            CONFLICT_MULTIPLE_ACTIVE_BASELINES, severity="high",
            affected_evidence={},
            recommended_resolution="Baseline governance review required to determine the single active baseline.",
            responsible_reviewer_role="baseline_reviewer",
        ))

    if supervisor_label and ai_label and supervisor_label != ai_label:
        conflicts.append(_conflict(
            CONFLICT_SUPERVISOR_LABEL_CONFLICT, severity="moderate",
            affected_evidence={"supervisor_label": supervisor_label, "ai_label": ai_label},
            recommended_resolution="Supervisor review to reconcile the AI and supervisor labels.",
            responsible_reviewer_role="supervisor",
        ))

    if not model_approved_for_family:
        conflicts.append(_conflict(
            CONFLICT_MODEL_NOT_APPROVED, severity="high",
            affected_evidence={},
            recommended_resolution="Do not use this model's output for this instrument family until approved.",
            responsible_reviewer_role="model_governance_reviewer",
        ))

    if baseline_superseded_after_inspection:
        conflicts.append(_conflict(
            CONFLICT_BASELINE_SUPERSEDED_AFTER_INSPECTION, severity="moderate",
            affected_evidence={},
            recommended_resolution="Re-run evidence assessment against the current baseline version.",
            responsible_reviewer_role="baseline_reviewer",
        ))

    if duplicate_image_zones and len(set(duplicate_image_zones)) > 1:
        conflicts.append(_conflict(
            CONFLICT_DUPLICATE_IMAGE_DIFFERENT_ZONES, severity="low",
            affected_evidence={"zones": duplicate_image_zones},
            recommended_resolution="Confirm which zone this image actually depicts.",
            responsible_reviewer_role="supervisor",
        ))

    if timestamp_inconsistent:
        conflicts.append(_conflict(
            CONFLICT_EVIDENCE_TIMESTAMP_INCONSISTENCY, severity="low",
            affected_evidence={},
            recommended_resolution="Investigate evidence timestamp ordering before finalizing.",
            responsible_reviewer_role="baseline_reviewer",
        ))

    return conflicts
