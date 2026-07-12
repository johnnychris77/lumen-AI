"""Project Steward, Section 26: Reports.

Reuses Veritas's already-generic export helpers
(`veritas_reports_service.build_report_pdf_bytes` / `build_report_csv_bytes`
/ `build_report_xlsx_bytes`) exactly the way Council's own
`council_reports_service` does -- every report here is just
`{title, content}` fed through that shared renderer, never a second
PDF/CSV/Excel implementation.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import GovernedAction, STATUS_BLOCKED, TERMINAL_STATUSES
from app.services import (
    steward_action_service,
    steward_benefits_realization_service,
    steward_change_management_service,
    steward_timeline_service,
    steward_unintended_consequence_service,
    steward_verification_service,
)
from app.services.veritas_reports_service import build_report_csv_bytes, build_report_pdf_bytes, build_report_xlsx_bytes


def action_implementation_report(db: Session, tenant_id: str, action_id: int) -> dict:
    content = steward_action_service.to_dict(steward_action_service.get_action(db, tenant_id, action_id))
    content["timeline"] = steward_timeline_service.decision_to_outcome_timeline(db, tenant_id, action_id)
    return {"title": "Action Implementation Report", "content": content}


def change_readiness_report(db: Session, tenant_id: str, action_id: int) -> dict:
    return {"title": "Change Readiness Report", "content": steward_change_management_service.generate_change_management_plan(db, tenant_id, action_id)}


def verification_evidence_package(db: Session, tenant_id: str, action_id: int) -> dict:
    return {"title": "Verification Evidence Package", "content": {"verifications": steward_verification_service.list_verifications(db, tenant_id, action_id)}}


def benefits_realization_report(db: Session, tenant_id: str, action_id: int) -> dict:
    return {"title": "Benefits Realization Report", "content": {"outcome_reviews": steward_benefits_realization_service.list_outcome_reviews(db, tenant_id, action_id)}}


def unintended_consequence_report(db: Session, tenant_id: str, action_id: int) -> dict:
    return {"title": "Unintended Consequence Report", "content": {"consequences": steward_unintended_consequence_service.list_consequences(db, tenant_id, action_id)}}


_ACTION_REPORT_BUILDERS = {
    "implementation": action_implementation_report,
    "change_readiness": change_readiness_report,
    "verification_evidence": verification_evidence_package,
    "benefits_realization": benefits_realization_report,
    "unintended_consequence": unintended_consequence_report,
}


def blocked_action_report(db: Session, tenant_id: str) -> dict:
    rows = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id, GovernedAction.status == STATUS_BLOCKED).all()
    return {"title": "Blocked Action Report", "content": {"actions": [steward_action_service.to_dict(r) for r in rows]}}


def executive_initiative_report(db: Session, tenant_id: str) -> dict:
    rows = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id, GovernedAction.category == "governance").all()
    return {"title": "Executive Initiative Report", "content": {"actions": [steward_action_service.to_dict(r) for r in rows]}}


def action_aging_report(db: Session, tenant_id: str) -> dict:
    now = datetime.now(timezone.utc)
    rows = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id, GovernedAction.status.notin_(TERMINAL_STATUSES)).all()
    aged = []
    for r in rows:
        created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
        entry = steward_action_service.to_dict(r)
        entry["age_days"] = (now - created).days
        aged.append(entry)
    return {"title": "Action Aging Report", "content": {"actions": aged}}


def closure_report(db: Session, tenant_id: str) -> dict:
    rows = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id, GovernedAction.closure_decision != "").all()
    return {"title": "Closure Report", "content": {"actions": [steward_action_service.to_dict(r) for r in rows]}}


_TENANT_REPORT_BUILDERS = {
    "blocked_action": blocked_action_report,
    "executive_initiative": executive_initiative_report,
    "action_aging": action_aging_report,
    "closure": closure_report,
}


def _render(doc: dict, export_format: str) -> bytes:
    if export_format == "pdf":
        return build_report_pdf_bytes(doc["title"], doc["content"])
    if export_format == "csv":
        return build_report_csv_bytes(doc["content"])
    if export_format == "xlsx":
        return build_report_xlsx_bytes(doc["title"], doc["content"])
    raise ValueError(f"Unsupported export format '{export_format}'")


def export_action_report(db: Session, tenant_id: str, action_id: int, report_type: str, export_format: str) -> bytes:
    builder = _ACTION_REPORT_BUILDERS.get(report_type)
    if builder is None:
        raise ValueError(f"Unknown report_type '{report_type}'")
    return _render(builder(db, tenant_id, action_id), export_format)


def export_tenant_report(db: Session, tenant_id: str, report_type: str, export_format: str) -> bytes:
    builder = _TENANT_REPORT_BUILDERS.get(report_type)
    if builder is None:
        raise ValueError(f"Unknown report_type '{report_type}'")
    return _render(builder(db, tenant_id), export_format)
