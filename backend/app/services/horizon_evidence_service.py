"""v3.4 — Project Horizon, Section 8: Clinical Evidence Repository.

Only a narrow finding-category-to-regulatory-clause mapping
(`app/models/regulatory.py::FindingRegulatoryMapping`) existed before this
sprint. This module is the first general-purpose clinical evidence store
— peer-reviewed literature, manufacturer guidance, AAMI/AORN standards,
an organization's own SOPs, and internal validation studies — and the
first mechanism linking any AI-generated recommendation (from any engine:
Sentinel, Atlas, Insight, Quality Guardian's CAPA/RCA, etc.) to the
evidence that supports it, via a generic `source_type`/`source_id` pair
rather than a foreign key into one specific recommendation table.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.federated_horizon import EVIDENCE_TYPES, ClinicalEvidenceReference, RecommendationEvidenceLink


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def add_evidence(
    db: Session, *, evidence_type: str, title: str, citation_text: str, source: str = "",
    publication_date: datetime | None = None, url: str = "", tenant_id: str = "", added_by: str = "",
) -> dict:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"evidence_type must be one of {EVIDENCE_TYPES}")

    row = ClinicalEvidenceReference(
        evidence_type=evidence_type, title=title, citation_text=citation_text, source=source,
        publication_date=publication_date, url=url, tenant_id=tenant_id, added_by=added_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_evidence(db: Session, *, evidence_type: str = "", tenant_id: str = "") -> list[dict]:
    """Public (global) evidence — `tenant_id == ""` — is always visible.
    A tenant's own private SOPs/validation studies are visible only to
    that tenant; other organizations' private evidence is never returned."""
    q = db.query(ClinicalEvidenceReference)
    if evidence_type:
        q = q.filter(ClinicalEvidenceReference.evidence_type == evidence_type)
    if tenant_id:
        q = q.filter((ClinicalEvidenceReference.tenant_id == "") | (ClinicalEvidenceReference.tenant_id == tenant_id))
    else:
        q = q.filter(ClinicalEvidenceReference.tenant_id == "")
    rows = q.order_by(ClinicalEvidenceReference.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def get_evidence(db: Session, evidence_id: int) -> dict | None:
    row = db.query(ClinicalEvidenceReference).filter(ClinicalEvidenceReference.id == evidence_id).first()
    return _row_to_dict(row) if row else None


def link_evidence_to_recommendation(
    db: Session, *, source_type: str, source_id: str, evidence_id: int, relevance_note: str = "", linked_by: str = "",
) -> dict:
    if db.query(ClinicalEvidenceReference.id).filter(ClinicalEvidenceReference.id == evidence_id).first() is None:
        raise ValueError(f"Evidence reference {evidence_id} not found.")

    row = RecommendationEvidenceLink(
        source_type=source_type, source_id=str(source_id), evidence_id=evidence_id,
        relevance_note=relevance_note, linked_by=linked_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_evidence_for_recommendation(db: Session, source_type: str, source_id: str) -> list[dict]:
    links = (
        db.query(RecommendationEvidenceLink)
        .filter(RecommendationEvidenceLink.source_type == source_type, RecommendationEvidenceLink.source_id == str(source_id))
        .all()
    )
    results = []
    for link in links:
        evidence = get_evidence(db, link.evidence_id)
        if evidence is not None:
            results.append({**evidence, "relevance_note": link.relevance_note, "linked_by": link.linked_by})
    return results
