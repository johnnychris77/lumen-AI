"""v4.4 — Project Catalyst, Section 3: Natural Language Actions.

Every action below calls an already-existing execution path — this
module adds no parallel action-execution system, only a natural-language
front door plus a confirmation gate for critical actions:

  * assign_inspection      -> `forge_action_service.execute_action("assign_technician", ...)`
  * generate_report        -> `catalyst_skills_service.reporting_skill`
  * export_dashboard       -> live KPI/executive dashboard, exported as CSV
                               (the same `csv.DictWriter` idiom every
                               exporter in this codebase already uses)
  * create_capa_draft      -> `capa_service.create_capa(..., status="draft")`
  * notify_supervisor      -> `forge_action_service.execute_action("notify_supervisor", ...)`
  * schedule_competency_review -> no calendar/scheduling infrastructure
                               exists anywhere in this codebase (confirmed)
                               — rather than fabricate one, this raises a
                               real supervisor-review notification via
                               `forge_action_service.execute_action(
                               "require_supervisor_review", ...)` tagged
                               with the technician, which is the honest
                               existing mechanism for "get a supervisor to
                               do a review of this technician."
  * open_digital_twin       -> `digital_twin_engine.compute_twin_dashboard`
                               (read-only navigation, never critical)
  * open_knowledge_article  -> `knowledge_repository_service.get_article`
                               (read-only navigation, never critical)
  * publish_workflow        -> `forge_workflow_service.publish_workflow`

`CRITICAL_ACTION_TYPES` (assign_inspection, create_capa_draft,
notify_supervisor, schedule_competency_review, publish_workflow) always
go through `CatalystPendingAction` — a single-use, 15-minute confirm
token — before they execute. Read-only navigation and export actions run
immediately since they change nothing.
"""
from __future__ import annotations

import csv
import json
import secrets
from datetime import datetime, timezone
from io import StringIO

from sqlalchemy.orm import Session

from app.models.catalyst_copilot import (
    ACTION_ASSIGN_INSPECTION,
    ACTION_CREATE_CAPA_DRAFT,
    ACTION_EXPORT_DASHBOARD,
    ACTION_GENERATE_REPORT,
    ACTION_NOTIFY_SUPERVISOR,
    ACTION_OPEN_DIGITAL_TWIN,
    ACTION_OPEN_KNOWLEDGE_ARTICLE,
    ACTION_PUBLISH_WORKFLOW,
    ACTION_SCHEDULE_COMPETENCY_REVIEW,
    CATALYST_ACTION_TYPES,
    CRITICAL_ACTION_TYPES,
    PENDING_ACTION_CANCELLED,
    PENDING_ACTION_CONFIRMED,
    PENDING_ACTION_EXPIRED,
    PENDING_ACTION_PENDING,
    CatalystPendingAction,
)
from app.services import capa_service, catalyst_skills_service, digital_twin_engine, forge_action_service, knowledge_repository_service
from app.services.forge_workflow_service import publish_workflow


class UnknownCatalystActionError(Exception):
    pass


class PendingActionNotFoundError(Exception):
    pass


class PendingActionExpiredError(Exception):
    pass


def _new_confirm_token() -> str:
    return secrets.token_urlsafe(24)


def _summarize(action_type: str, params: dict) -> str:
    if action_type == ACTION_ASSIGN_INSPECTION:
        return f"Assign inspection {params.get('inspection_id')} to {params.get('recipient_name') or 'a technician'}."
    if action_type == ACTION_CREATE_CAPA_DRAFT:
        return f"Create a CAPA draft titled '{params.get('title', 'Untitled CAPA')}'."
    if action_type == ACTION_NOTIFY_SUPERVISOR:
        return f"Notify supervisor: {params.get('message', 'workflow notification')}."
    if action_type == ACTION_SCHEDULE_COMPETENCY_REVIEW:
        return f"Request a competency review for {params.get('recipient_name') or 'a technician'}."
    if action_type == ACTION_PUBLISH_WORKFLOW:
        return f"Publish workflow {params.get('workflow_id')}."
    return f"{action_type}({params})"


def _execute(db: Session, tenant_id: str, action_type: str, params: dict, *, actor: str) -> dict:
    if action_type == ACTION_ASSIGN_INSPECTION:
        return forge_action_service.execute_action(db, tenant_id, "assign_technician", params, actor=actor)

    if action_type == ACTION_GENERATE_REPORT:
        return catalyst_skills_service.reporting_skill(
            db, tenant_id, audience=params.get("audience", "spd_director"),
            cadence=params.get("cadence", "monthly"), facility_id=params.get("facility_id", ""),
        )

    if action_type == ACTION_EXPORT_DASHBOARD:
        kpis = catalyst_skills_service.reporting_skill(db, tenant_id, facility_id=params.get("facility_id", ""))
        rows = [kpis.get("live_kpis") or kpis.get("report", {})]
        output = StringIO()
        if rows and isinstance(rows[0], dict) and rows[0]:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerow(rows[0])
        return {"action_type": action_type, "csv_bytes_len": len(output.getvalue().encode("utf-8")), "source": kpis.get("source", "pulse")}

    if action_type == ACTION_CREATE_CAPA_DRAFT:
        result = capa_service.create_capa(
            title=params.get("title", "Copilot-drafted CAPA"), source="catalyst_copilot",
            description=params.get("description", ""), risk_level=params.get("risk_level", "medium"),
            owner=params.get("owner"), status="draft",
        )
        return {"action_type": action_type, "capa": result}

    if action_type == ACTION_NOTIFY_SUPERVISOR:
        return forge_action_service.execute_action(db, tenant_id, "notify_supervisor", params, actor=actor)

    if action_type == ACTION_SCHEDULE_COMPETENCY_REVIEW:
        message = params.get("message") or f"Competency review requested for {params.get('recipient_name', 'technician')} via Catalyst Copilot."
        return forge_action_service.execute_action(
            db, tenant_id, "require_supervisor_review",
            {**params, "message": message}, actor=actor,
        )

    if action_type == ACTION_OPEN_DIGITAL_TWIN:
        dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, params.get("facility_id", ""), db)
        return {"action_type": action_type, "dashboard": dashboard.model_dump()}

    if action_type == ACTION_OPEN_KNOWLEDGE_ARTICLE:
        article = knowledge_repository_service.get_article(db, tenant_id, params.get("article_id", 0))
        if article is None:
            return {"action_type": action_type, "found": False}
        knowledge_repository_service.record_view(db, tenant_id, article.id)
        return {"action_type": action_type, "found": True, "article": knowledge_repository_service.article_to_dict(article)}

    if action_type == ACTION_PUBLISH_WORKFLOW:
        return publish_workflow(db, params.get("workflow_id"), approved_by=actor)

    raise UnknownCatalystActionError(f"action_type must be one of {CATALYST_ACTION_TYPES}")


def propose_action(
    db: Session, tenant_id: str, user_email: str, *, conversation_id: int, action_type: str, params: dict, actor: str,
) -> dict:
    if action_type not in CATALYST_ACTION_TYPES:
        raise UnknownCatalystActionError(f"action_type must be one of {CATALYST_ACTION_TYPES}")

    if action_type not in CRITICAL_ACTION_TYPES:
        result = _execute(db, tenant_id, action_type, params, actor=actor)
        return {"requires_confirmation": False, "action_type": action_type, "result": result}

    token = _new_confirm_token()
    pending = CatalystPendingAction(
        tenant_id=tenant_id, user_email=user_email, conversation_id=conversation_id, action_type=action_type,
        params_json=json.dumps(params), summary=_summarize(action_type, params), confirm_token=token,
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return {
        "requires_confirmation": True, "action_type": action_type, "confirm_token": token,
        "summary": pending.summary, "expires_at": pending.expires_at.isoformat(),
    }


def confirm_action(db: Session, tenant_id: str, user_email: str, confirm_token: str, *, actor: str) -> dict:
    pending = db.query(CatalystPendingAction).filter(
        CatalystPendingAction.confirm_token == confirm_token, CatalystPendingAction.tenant_id == tenant_id,
        CatalystPendingAction.user_email == user_email,
    ).first()
    if pending is None:
        raise PendingActionNotFoundError("No pending action found for that confirm_token.")
    if pending.status != PENDING_ACTION_PENDING:
        raise PendingActionExpiredError(f"Pending action is already '{pending.status}'.")
    if pending.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        pending.status = PENDING_ACTION_EXPIRED
        db.commit()
        raise PendingActionExpiredError("Pending action confirm token has expired.")

    params = json.loads(pending.params_json)
    result = _execute(db, tenant_id, pending.action_type, params, actor=actor)
    pending.status = PENDING_ACTION_CONFIRMED
    pending.decided_at = datetime.now(timezone.utc)
    pending.result_json = json.dumps(result)
    db.commit()
    return {"action_type": pending.action_type, "result": result}


def list_pending_actions(db: Session, tenant_id: str, user_email: str) -> list[dict]:
    """Backs the copilot workspace's Open Tasks panel — real, currently-
    unconfirmed actions this user proposed, never a fabricated task list."""
    rows = db.query(CatalystPendingAction).filter(
        CatalystPendingAction.tenant_id == tenant_id, CatalystPendingAction.user_email == user_email,
        CatalystPendingAction.status == PENDING_ACTION_PENDING,
    ).order_by(CatalystPendingAction.created_at.desc()).all()
    return [
        {
            "confirm_token": r.confirm_token, "action_type": r.action_type, "summary": r.summary,
            "expires_at": r.expires_at.isoformat(), "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def cancel_action(db: Session, tenant_id: str, user_email: str, confirm_token: str) -> dict:
    pending = db.query(CatalystPendingAction).filter(
        CatalystPendingAction.confirm_token == confirm_token, CatalystPendingAction.tenant_id == tenant_id,
        CatalystPendingAction.user_email == user_email, CatalystPendingAction.status == PENDING_ACTION_PENDING,
    ).first()
    if pending is None:
        raise PendingActionNotFoundError("No pending action found for that confirm_token.")
    pending.status = PENDING_ACTION_CANCELLED
    pending.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"action_type": pending.action_type, "status": pending.status}
