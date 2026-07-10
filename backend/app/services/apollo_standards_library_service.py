"""v4.7 — Project Apollo, Section 7: Standards Knowledge Library.

Composes three pre-existing standards/publication systems into one library
view — `regulatory_standards_catalogue.py` (AAMI/AORN/DNV/FDA/CMS/JC/ISO
clause-level standards, now extended with ST91/AORN/DNV), `beacon_standards_
service.py` (governed guidance/recommended-practice publications), and
`p24_standards_service.py` (internal quality-classification standards). Every
recommendation still shows its own source system — Apollo never re-derives
or merges the underlying records, only groups them for one library view.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import beacon_standards_service, p24_standards_service
from app.services.apollo_policy_service import list_policies
from app.services.regulatory_standards_catalogue import get_standards
from app.models.apollo_quality import DISCLAIMER, POLICY_PUBLISHED


def regulatory_catalogue_by_body(body: str | None = None) -> list[dict]:
    """Clause-level regulatory standards (Section 7's AAMI/AORN/Manufacturer
    IFU/regulatory references), sourced from `regulatory_standards_
    catalogue.py` — the source system for every citation."""
    standards = get_standards()
    if body:
        standards = [s for s in standards if s.body == body]
    return [
        {
            "code": s.code, "body": s.body, "title": s.title, "description": s.description,
            "category": s.category, "applicability": s.applicability, "source": "regulatory_standards_catalogue",
        }
        for s in standards
    ]


def standards_library_summary(db: Session, tenant_id: str) -> dict:
    """One Standards Knowledge Library view composing all three existing
    systems, each recommendation retaining its own `source` field."""
    regulatory = regulatory_catalogue_by_body()
    beacon = beacon_standards_service.standards_center_summary(db)
    p24_internal_standards = p24_standards_service.get_quality_standards(db)
    internal_sops = [
        {**p, "source": "internal_quality_policy"}
        for p in list_policies(db, tenant_id, status=POLICY_PUBLISHED)
    ]

    body_counts: dict[str, int] = {}
    for s in regulatory:
        body_counts[s["body"]] = body_counts.get(s["body"], 0) + 1

    return {
        "regulatory_standards": regulatory,
        "regulatory_body_counts": body_counts,
        "beacon_guidance": beacon["guidance"],
        "beacon_recommended_practices": beacon["recommended_practices"],
        "beacon_educational_content": beacon["educational_content"],
        "beacon_reference_materials": beacon["reference_materials"],
        "internal_classification_standards": [
            {**s, "source": "p24_standards_service"} for s in p24_internal_standards
        ],
        "internal_sops": internal_sops,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
