"""Project Sage, Section 6: Microlearning Generator.

Generates short educational modules *only* from the platform's one approved
knowledge source -- `education_library.get_article` (itself built from
`clinical_mentor.FINDING_EDUCATION` + `instrument_anatomy.py` + the IFU
reference note). A `finding_type` outside that approved 12-category library
is refused (returns `None`) rather than have Sage author unsupported
clinical guidance -- satisfies "unapproved guidance is excluded."
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.sage_education import SageMicrolearningModule
from app.services.education_library import CATEGORIES, get_article


def _knowledge_check(article: dict) -> list[dict]:
    return [{
        "question": f"What is the clinical significance of {article['finding'].lower()}?",
        "answer": article["clinical_importance"],
    }, {
        "question": f"Which anatomy zones most commonly retain {article['finding'].lower()}?",
        "answer": ", ".join(article["typical_anatomy_locations"]) or "Not yet established for this finding.",
    }]


def build_module_from_finding(db: Session, tenant_id: str, finding_type: str, *, instrument_family: str = "", anatomy_zone: str = "") -> SageMicrolearningModule | None:
    """Refuses to build a module for any finding_type outside the approved
    knowledge library -- returns None, never fabricates content."""
    article = get_article(finding_type)
    if article is None:
        return None

    title = f"Recognizing {article['finding'].capitalize()}" if finding_type != "insulation_damage" else "Recognizing Insulation Damage"
    row = SageMicrolearningModule(
        tenant_id=tenant_id,
        title=title,
        learning_objective=f"Correctly identify and document {article['finding'].lower()} during inspection.",
        why_it_matters=article["clinical_importance"],
        anatomy_overview=", ".join(article["typical_anatomy_locations"]) or "General inspection zones.",
        common_findings_json=json.dumps([article["finding"]]),
        inspection_steps_json=json.dumps(article["inspection_tips"]),
        corrective_actions_json=json.dumps(article["corrective_actions"]),
        knowledge_check_json=json.dumps(_knowledge_check(article)),
        source_refs_json=json.dumps([article["reference"], "clinical_mentor.FINDING_EDUCATION", "education_library"]),
        instrument_family=instrument_family,
        anatomy_zone=anatomy_zone,
        competency_domain=finding_type,
        approval_status="draft",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def approve_module(db: Session, tenant_id: str, module_id: int, *, approved_by: str) -> SageMicrolearningModule | None:
    row = db.query(SageMicrolearningModule).filter(SageMicrolearningModule.id == module_id, SageMicrolearningModule.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.approval_status = "approved"
    row.approved_by = approved_by
    from datetime import datetime, timezone
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def _to_dict(row: SageMicrolearningModule) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "title": row.title,
        "learning_objective": row.learning_objective,
        "why_it_matters": row.why_it_matters,
        "anatomy_overview": row.anatomy_overview,
        "common_findings": json.loads(row.common_findings_json or "[]"),
        "inspection_steps": json.loads(row.inspection_steps_json or "[]"),
        "corrective_actions": json.loads(row.corrective_actions_json or "[]"),
        "knowledge_check": json.loads(row.knowledge_check_json or "[]"),
        "source_refs": json.loads(row.source_refs_json or "[]"),
        "instrument_family": row.instrument_family,
        "anatomy_zone": row.anatomy_zone,
        "competency_domain": row.competency_domain,
        "approval_status": row.approval_status,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "version": row.version,
    }


def list_modules(db: Session, tenant_id: str, *, approval_status: str = "") -> list[dict]:
    q = db.query(SageMicrolearningModule).filter(SageMicrolearningModule.tenant_id == tenant_id)
    if approval_status:
        q = q.filter(SageMicrolearningModule.approval_status == approval_status)
    return [_to_dict(r) for r in q.order_by(SageMicrolearningModule.created_at.desc()).all()]


def available_categories() -> list[str]:
    """The only finding_types Sage may generate approved modules for."""
    return list(CATEGORIES)
