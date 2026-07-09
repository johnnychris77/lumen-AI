"""v2.9 — LumenAI Quality (Project Guardian), Section 3: SPD Quality Taxonomy.

A governed, versioned taxonomy for the Quality Event Engine's classification
output — deliberately separate from the AI agents' own finding-type
vocabularies (`contamination_agent.CONTAMINATION_FINDING_TYPES`,
`damage_agent.DAMAGE_FINDING_TYPES`, `clinical_mentor.FINDING_EDUCATION`),
which are left untouched. `DEFAULT_TAXONOMY` seeds the `QualityTaxonomyTerm`
table on first use; tenants can add further terms at runtime (configurable),
each carrying the taxonomy version it was added under.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.quality_guardian import DEFAULT_TAXONOMY, TAXONOMY_VERSION, QualityTaxonomyTerm


def ensure_default_taxonomy(db: Session, tenant_id: str) -> None:
    """Idempotently seed the default taxonomy for a tenant if not present."""
    existing = db.query(QualityTaxonomyTerm.id).filter(QualityTaxonomyTerm.tenant_id == tenant_id).first()
    if existing is not None:
        return
    for category, terms in DEFAULT_TAXONOMY.items():
        for term in terms:
            db.add(
                QualityTaxonomyTerm(
                    tenant_id=tenant_id, category=category, term=term,
                    display_label=term.replace("_", " ").title(), version=TAXONOMY_VERSION,
                ),
            )
    db.commit()


def list_taxonomy(db: Session, tenant_id: str) -> dict:
    ensure_default_taxonomy(db, tenant_id)
    rows = (
        db.query(QualityTaxonomyTerm)
        .filter(QualityTaxonomyTerm.tenant_id == tenant_id, QualityTaxonomyTerm.active.is_(True))
        .order_by(QualityTaxonomyTerm.category.asc(), QualityTaxonomyTerm.term.asc())
        .all()
    )
    by_category: dict[str, list[dict]] = {}
    for row in rows:
        by_category.setdefault(row.category, []).append(
            {"id": row.id, "term": row.term, "display_label": row.display_label, "version": row.version},
        )
    return {"taxonomy": by_category, "current_version": TAXONOMY_VERSION}


def add_taxonomy_term(db: Session, tenant_id: str, *, category: str, term: str, display_label: str = "") -> dict:
    ensure_default_taxonomy(db, tenant_id)
    row = QualityTaxonomyTerm(
        tenant_id=tenant_id, category=category, term=term,
        display_label=display_label or term.replace("_", " ").title(), version=TAXONOMY_VERSION,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "category": row.category, "term": row.term, "display_label": row.display_label, "version": row.version}


def category_for_term(term: str) -> str:
    for category, terms in DEFAULT_TAXONOMY.items():
        if term in terms:
            return category
    return "unknown"
