"""v4.1 — Project Forge, Section 6: Automation Actions.

Every action calls an already-existing service/model directly rather
than reinventing its effect:

  * Create CAPA -> `app.services.capa_service.create_capa`
  * Create Knowledge Article Draft -> `knowledge_repository_service.create_article`
  * Update Digital Twin -> `digital_twin_engine.log_instrument_flow`/`complete_flow`
  * Notify Supervisor / Escalate / Assign Technician -> `WorkflowNotification`
    (the same recipient-role fan-out idiom `or_connect`/`workflow`
    notifications already use)
  * Flag Instrument / Create Watchlist Entry -> a `ClinicalWatchlistEntry`
    row, matching Sentinel's existing watchlist model shape exactly
    (its own `_upsert` is private and batch-oriented, so this constructs
    the row directly rather than reaching into another module's private
    helper)
  * Create Enterprise Alert -> an `EnterpriseAlert` row, resolving
    `system_id` from the tenant's facility via Genesis's
    `platform_org_service.facility_for_tenant` — best-effort; a tenant
    with no enterprise hierarchy record simply cannot raise an
    enterprise-scoped alert, which is skipped rather than fabricated.
  * Generate Report -> `atlas_report_service`'s existing CSV/XLSX/PDF
    exporters, given a plain dict payload (no Atlas system dependency
    required for this lightweight per-execution report).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.knowledge import DRAFT
from app.models.workflow import WorkflowNotification
from app.models.workflow_forge import ACTION_TYPES
from app.services import capa_service, knowledge_repository_service, platform_org_service
from app.services import digital_twin_engine as _digital_twin_engine


class UnknownActionTypeError(Exception):
    pass


def _new_watchlist_ref() -> str:
    return f"WATCH-{uuid.uuid4().hex[:8].upper()}"


def _new_alert_ref() -> str:
    return f"ALERT-{uuid.uuid4().hex[:8].upper()}"


def execute_action(db: Session, tenant_id: str, action_type: str, params: dict, *, actor: str = "workflow_forge") -> dict:
    if action_type not in ACTION_TYPES:
        raise UnknownActionTypeError(f"action_type must be one of {ACTION_TYPES}")

    if action_type in ("assign_technician", "notify_supervisor", "escalate", "require_supervisor_review", "recommend_reclean"):
        recipient_role = params.get("recipient_role") or ("supervisor" if action_type != "assign_technician" else "technician")
        message = params.get("message") or f"Workflow action: {action_type.replace('_', ' ')}"
        notification = WorkflowNotification(
            inspection_id=params.get("inspection_id", 0), tenant_id=tenant_id, notification_type=action_type,
            recipient_role=recipient_role, recipient_name=params.get("recipient_name", ""), message=message,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return {"action_type": action_type, "notification_id": notification.id}

    if action_type == "create_capa":
        result = capa_service.create_capa(
            title=params.get("title", "Workflow-triggered CAPA"), source="workflow_forge",
            description=params.get("description", ""), risk_level=params.get("risk_level", "medium"),
            owner=params.get("owner"),
        )
        return {"action_type": action_type, "capa": result}

    if action_type == "create_knowledge_draft":
        article = knowledge_repository_service.create_article(
            db, tenant_id=tenant_id, category=params.get("category", "best_practice"),
            title=params.get("title", "Workflow-captured knowledge note"), body=params.get("body", ""),
            author=actor, source_inspection_id=params.get("inspection_id"), approval_status=DRAFT,
        )
        db.commit()
        db.refresh(article)
        return {"action_type": action_type, "article_id": article.id}

    if action_type == "update_digital_twin":
        flow = _digital_twin_engine.log_instrument_flow(
            tenant_id, params.get("facility_id", ""), params.get("instrument_name", ""),
            params.get("instrument_id", ""), params.get("from_station", ""),
            params.get("to_station", "inspection"), params.get("station_type", "inspection"),
            params.get("notes", "workflow-triggered update"), db,
        )
        return {"action_type": action_type, "flow_id": flow.id, "outcome": flow.outcome}

    if action_type in ("flag_instrument", "create_watchlist_entry"):
        from app.models.sentinel_orchestration import ClinicalWatchlistEntry
        row = ClinicalWatchlistEntry(
            tenant_id=tenant_id, entity_type=params.get("entity_type", "instrument"),
            entity_value=params.get("entity_value", ""), risk_score=params.get("risk_score", 0.0),
            reason=params.get("reason", f"Flagged by workflow action '{action_type}'"), status="active",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"action_type": action_type, "watchlist_entry_id": row.id}

    if action_type == "create_enterprise_alert":
        facility = platform_org_service.facility_for_tenant(db, tenant_id)
        if facility is None:
            return {"action_type": action_type, "skipped": True, "reason": "tenant has no enterprise hierarchy facility to scope an enterprise alert to"}
        from app.models.atlas_enterprise import EnterpriseAlert
        row = EnterpriseAlert(
            system_id=facility["system_id"], alert_ref=_new_alert_ref(),
            title=params.get("title", "Workflow-triggered enterprise alert"),
            narrative=params.get("narrative", ""), recommendation=params.get("recommendation", ""),
            reasoning=params.get("reasoning", "Raised by an automated workflow action."),
            severity=params.get("severity", "medium"), affected_facility_count=1,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"action_type": action_type, "alert_id": row.id}

    if action_type == "generate_report":
        # `atlas_report_service.build_report_csv_bytes` requires an
        # Atlas-shaped `{"summary": {"facility_comparison": [...]}}` dict
        # (it is that system's executive report, not a generic exporter) —
        # a workflow's report is arbitrary rows, so this reuses the same
        # `csv.DictWriter`/`StringIO` pattern every exporter in this
        # codebase already uses, rather than forcing an Atlas-shaped input.
        import csv
        from io import StringIO
        rows = params.get("rows", [])
        output = StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        csv_bytes = output.getvalue().encode("utf-8")
        return {
            "action_type": action_type, "title": params.get("title", "Workflow Execution Report"),
            "generated_at": datetime.now(timezone.utc).isoformat(), "report_size_bytes": len(csv_bytes),
        }

    raise UnknownActionTypeError(f"action_type '{action_type}' is not implemented.")
