"""v5.3 — Project Genesis AI, Section 8: Clinical Intelligence Exchange.

Zero new tables. Olympus's `HIXExchangePackage`/`olympus_exchange_service.py`
(v5.1) already packages knowledge/workflow/Digital-Twin/education content
with mandatory governance approval and full provenance
(`content_ref_type`/`content_ref_id`, `reviewed_by`/`reviewed_at`,
de-identified `source_tenant_id`). Genesis AI extended
`HIX_PACKAGE_TYPES` with `research_dataset` so P20's governance-gated
research datasets can flow through the same exchange pipeline. This
module is a thin, named wrapper for Genesis AI's own routes/frontend --
it never duplicates `olympus_exchange_service.py`'s logic.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.olympus_network import HIX_PACKAGE_RESEARCH_DATASET, HIX_PACKAGE_TYPES
from app.services import olympus_exchange_service


def submit_research_dataset_package(
    db: Session, source_tenant_id: str, *, dataset_ref: int, title: str, description: str,
    no_phi_confirmed: bool, no_identifiable_customer_data_confirmed: bool, submitted_by: str,
) -> dict:
    """A convenience wrapper over Olympus's generic `submit_package`,
    pre-filling `package_type`/`content_ref_type` for P20 research
    datasets specifically."""
    return olympus_exchange_service.submit_package(
        db, source_tenant_id, package_type=HIX_PACKAGE_RESEARCH_DATASET, title=title, description=description,
        content_ref_type="p20_research_dataset", content_ref_id=dataset_ref, no_phi_confirmed=no_phi_confirmed,
        no_identifiable_customer_data_confirmed=no_identifiable_customer_data_confirmed, submitted_by=submitted_by,
    )


def intelligence_exchange_summary(db: Session) -> dict:
    return {
        "package_types": HIX_PACKAGE_TYPES,
        "published_packages": olympus_exchange_service.list_published_packages(db),
    }
