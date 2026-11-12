"""Stage 4 — Data Provenance Enforcement (authoritative, fail-closed).

Clinical model promotion requires VERIFIED, APPROVED ``real_clinical`` provenance
recorded on the governed ``DatasetRegistryEntry`` — never inferred from facility
or manufacturer names, filenames, image bytes, or user-declared free text (the
confirmed fail-open this module replaces). Missing, mixed, unknown, unapproved,
or legacy-unverified provenance can never qualify as clinical evidence.

This does NOT create a second dataset registry or a parallel audit engine: it
reads and writes the provenance columns on the existing ``DatasetRegistryEntry``
and records every classification/approval in the existing immutable enterprise
audit chain (``enterprise_audit_service.record_enterprise_audit_event``).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import (
    CLINICAL_PROVENANCE_CLASS,
    PROVENANCE_APPROVAL_APPROVED,
    PROVENANCE_APPROVAL_NOT_REQUIRED,
    PROVENANCE_APPROVAL_PENDING,
    PROVENANCE_CLASSES,
    PROVENANCE_LEGACY_UNVERIFIED,
    RESEARCH_PROVENANCE_CLASSES,
    UNVERIFIED_PROVENANCE_CLASSES,
    DatasetRegistryEntry,
)

# Governance roles authorized to APPROVE or assign a clinical provenance
# classification — the same authority that performs dataset-registry governance
# writes elsewhere (routes/dataset_registry.py `_WRITE_ROLES`). A client holding
# a lesser role, or none, can never self-certify real_clinical.
PROVENANCE_APPROVAL_ROLES = frozenset({"admin", "spd_manager"})


class ProvenanceAuthorityError(PermissionError):
    """A non-authorized role attempted to approve/assign clinical provenance,
    or a cross-tenant provenance change was attempted."""


class ProvenanceValidationError(ValueError):
    """An invalid provenance class was supplied."""


def normalize_provenance_class(value: str | None) -> str:
    """Return a known provenance class. Anything missing, blank, or unrecognised
    resolves conservatively to LEGACY_UNVERIFIED — never to a clinical or
    research class (fail-closed)."""
    v = (value or "").strip().lower()
    return v if v in PROVENANCE_CLASSES else PROVENANCE_LEGACY_UNVERIFIED


def is_clinical_evidence(entry: DatasetRegistryEntry) -> bool:
    """True only for a VERIFIED clinical row: class == real_clinical AND approval
    == approved. Everything else (research, unknown, legacy, pending, rejected)
    is not clinical evidence."""
    return (
        normalize_provenance_class(entry.data_provenance_class) == CLINICAL_PROVENANCE_CLASS
        and entry.provenance_approval_status == PROVENANCE_APPROVAL_APPROVED
    )


def clinical_exclusion_reason(entry: DatasetRegistryEntry) -> str | None:
    """Why ``entry`` is NOT clinical evidence, or None if it is."""
    cls = normalize_provenance_class(entry.data_provenance_class)
    if cls != CLINICAL_PROVENANCE_CLASS:
        if cls in RESEARCH_PROVENANCE_CLASSES:
            return f"research_provenance:{cls}"
        if cls in UNVERIFIED_PROVENANCE_CLASSES:
            return f"unverified_provenance:{cls}"
        return f"non_clinical_provenance:{cls}"
    if entry.provenance_approval_status != PROVENANCE_APPROVAL_APPROVED:
        return f"clinical_provenance_not_approved:{entry.provenance_approval_status}"
    return None


def set_provenance_classification(
    db: Session,
    *,
    entry: DatasetRegistryEntry,
    provenance_class: str,
    actor: str,
    actor_role: str,
    source_id: str = "",
    source_version: str = "",
    source_institution: str = "",
    rights_evidence_ref: str = "",
    specimen_id: str = "",
    approve: bool = False,
    tenant_id: str | None = None,
    commit: bool = True,
) -> DatasetRegistryEntry:
    """Assign/approve an entry's structured provenance — authority-gated and
    recorded in the immutable audit chain.

    - Assigning ``real_clinical``, or any ``approve=True``, requires an
      authorized governance role (``PROVENANCE_APPROVAL_ROLES``); otherwise
      ``ProvenanceAuthorityError``. This is what stops a client self-certifying
      clinical provenance via an API field.
    - Non-clinical research classes may be recorded without approval (they are
      marked ``not_required`` and never become clinical).
    - Tenant isolation: when ``tenant_id`` is given it must match ``entry``.
    """
    cls = (provenance_class or "").strip().lower()
    if cls not in PROVENANCE_CLASSES:
        raise ProvenanceValidationError(f"Unknown provenance class: {provenance_class!r}")
    if tenant_id is not None and entry.tenant_id != tenant_id:
        raise ProvenanceAuthorityError("Cross-tenant provenance change denied.")

    wants_clinical = cls == CLINICAL_PROVENANCE_CLASS
    if (wants_clinical or approve) and actor_role not in PROVENANCE_APPROVAL_ROLES:
        raise ProvenanceAuthorityError(
            f"Role '{actor_role}' may not approve or assign clinical provenance."
        )

    prev_class = entry.data_provenance_class
    prev_status = entry.provenance_approval_status

    entry.data_provenance_class = cls
    if source_id:
        entry.provenance_source_id = source_id
    if source_version:
        entry.provenance_source_version = source_version
    if source_institution:
        entry.provenance_source_institution = source_institution
    if rights_evidence_ref:
        entry.provenance_rights_evidence_ref = rights_evidence_ref
    if specimen_id:
        entry.provenance_specimen_id = specimen_id

    if approve:
        entry.provenance_approval_status = PROVENANCE_APPROVAL_APPROVED
        entry.provenance_approved_by = actor
        entry.provenance_approved_at = datetime.now(timezone.utc)
    elif cls in RESEARCH_PROVENANCE_CLASSES:
        entry.provenance_approval_status = PROVENANCE_APPROVAL_NOT_REQUIRED
        entry.provenance_approved_by = ""
        entry.provenance_approved_at = None
    else:
        entry.provenance_approval_status = PROVENANCE_APPROVAL_PENDING
        entry.provenance_approved_by = ""
        entry.provenance_approved_at = None

    # Immutable, hash-chained audit — the single existing writer, never a new one.
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    record_enterprise_audit_event(
        db,
        action_type="dataset.provenance.classified",
        resource_type="dataset_registry_entry",
        resource_id=entry.id,
        actor=actor,
        actor_role=actor_role,
        tenant_id=entry.tenant_id,
        status="success",
        details={
            "lcid": entry.lcid,
            "previous_class": prev_class,
            "new_class": cls,
            "previous_approval": prev_status,
            "new_approval": entry.provenance_approval_status,
            "source_id": entry.provenance_source_id,
            "source_version": entry.provenance_source_version,
            "source_institution": entry.provenance_source_institution,
            "rights_evidence_ref": entry.provenance_rights_evidence_ref,
            "specimen_id": entry.provenance_specimen_id,
        },
        commit=False,
    )
    if commit:
        db.commit()
        db.refresh(entry)
    return entry


def _sample_class(sample: dict[str, Any]) -> str:
    return normalize_provenance_class(sample.get("data_provenance_class"))


def _sample_is_clinical(sample: dict[str, Any]) -> bool:
    return (
        _sample_class(sample) == CLINICAL_PROVENANCE_CLASS
        and sample.get("provenance_approval_status") == PROVENANCE_APPROVAL_APPROVED
    )


def summarize_cohort_provenance(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-class counts and the cohort's clinical/research eligibility.

    - ``clinical_promotion_eligible`` is True ONLY when the cohort is non-empty
      and EVERY sample is verified ``real_clinical`` + approved. A mixed,
      unknown, legacy, unapproved, or empty cohort is rejected for clinical
      promotion (never silently granted).
    - ``research_experiment_eligible`` is True when the cohort is non-empty and
      no sample has unverified (unknown/legacy) provenance — i.e. every sample
      has an established research or clinical source. Research datasets may
      support an approved experiment but never clinical promotion.
    - ``aggregate_class`` is the single honest label: the shared class if the
      cohort is homogeneous, else ``"mixed"`` (or ``"none"`` when empty).
    """
    counts: dict[str, int] = {}
    excluded_from_clinical: dict[str, int] = {}
    clinical_samples = 0
    unverified_samples = 0
    for s in samples:
        cls = _sample_class(s)
        counts[cls] = counts.get(cls, 0) + 1
        if _sample_is_clinical(s):
            clinical_samples += 1
        else:
            reason = (
                "clinical_not_approved"
                if cls == CLINICAL_PROVENANCE_CLASS
                else cls
            )
            excluded_from_clinical[reason] = excluded_from_clinical.get(reason, 0) + 1
        if cls in UNVERIFIED_PROVENANCE_CLASSES:
            unverified_samples += 1

    total = len(samples)
    distinct = set(counts)
    if total == 0:
        aggregate = "none"
    elif len(distinct) == 1:
        aggregate = next(iter(distinct))
    else:
        aggregate = "mixed"

    clinical_promotion_eligible = total > 0 and clinical_samples == total
    research_experiment_eligible = total > 0 and unverified_samples == 0

    return {
        "total_samples": total,
        "class_counts": counts,
        "clinical_sample_count": clinical_samples,
        "excluded_from_clinical": excluded_from_clinical,
        "aggregate_class": aggregate,
        "clinical_promotion_eligible": clinical_promotion_eligible,
        "research_experiment_eligible": research_experiment_eligible,
    }
