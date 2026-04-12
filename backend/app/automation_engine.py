from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.notifications.approval_notifications import notify_approval
from app.notifications.dunning_notifications import send_dunning_notification


def _safe_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def list_enabled_rules(db: Session, tenant_id: str, trigger_type: str) -> list[models.AutomationRule]:
    return (
        db.query(models.AutomationRule)
        .filter(
            models.AutomationRule.tenant_id == tenant_id,
            models.AutomationRule.trigger_type == trigger_type,
            models.AutomationRule.is_enabled == True,
        )
        .order_by(models.AutomationRule.id.desc())
        .all()
    )


def _matches(condition: dict, payload: dict) -> bool:
    if not condition:
        return True

    for key, expected in condition.items():
        actual = payload.get(key)

        if isinstance(expected, dict):
            if "gte" in expected and not (actual is not None and float(actual) >= float(expected["gte"])):
                return False
            if "lte" in expected and not (actual is not None and float(actual) <= float(expected["lte"])):
                return False
            if "eq" in expected and actual != expected["eq"]:
                return False
            if "in" in expected and actual not in expected["in"]:
                return False
        else:
            if actual != expected:
                return False

    return True


def _log_run(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    rule_id: int,
    trigger_type: str,
    action_type: str,
    status: str,
    payload: dict,
    result: dict,
):
    row = models.AutomationRun(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        rule_id=rule_id,
        trigger_type=trigger_type,
        action_type=action_type,
        status=status,
        input_json=_compact(payload),
        result_json=_compact(result),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _execute_action(db: Session, tenant_id: str, tenant_name: str, action_type: str, action: dict, payload: dict) -> dict:
    if action_type == "slack_notification":
        return {
            "executed": True,
            "action_type": action_type,
            "message": action.get("message", "Slack notification simulated"),
            "payload": payload,
        }

    if action_type == "email_notification":
        return {
            "executed": True,
            "action_type": action_type,
            "subject": action.get("subject", "Email notification simulated"),
            "payload": payload,
        }

    if action_type == "approval_notification":
        approval_payload = {
            "tenant_name": tenant_name,
            "request_type": payload.get("request_type", "automation"),
            "target_resource": payload.get("target_resource", "unknown"),
            "target_resource_id": payload.get("target_resource_id", ""),
            "requested_by": payload.get("requested_by", "automation@lumenai.local"),
            "status": payload.get("status", "pending"),
            "created_at": payload.get("created_at", ""),
            "requested_payload": payload.get("requested_payload", {}),
        }
        result = notify_approval(approval_payload, mode="new")
        return {"executed": True, "action_type": action_type, "notification": result}

    if action_type == "dunning_notification":
        result = send_dunning_notification(payload, action.get("mode", "payment_failed"))
        return {"executed": True, "action_type": action_type, "notification": result}

    if action_type == "create_governance_approval":
        row = models.GovernanceApproval(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            request_type=action.get("request_type", "automation_request"),
            target_resource=action.get("target_resource", "automation"),
            target_resource_id=str(action.get("target_resource_id", "")),
            requested_by="automation@lumenai.local",
            requested_role="system",
            requested_payload=_compact({"payload": payload, "action": action}),
            status="pending",
            reviewed_by="",
            review_notes="",
            execution_status="not_started",
            execution_notes="",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"executed": True, "action_type": action_type, "approval_id": row.id}

    return {
        "executed": False,
        "action_type": action_type,
        "message": f"Unsupported action_type: {action_type}",
    }


def process_trigger(db: Session, tenant_id: str, tenant_name: str, trigger_type: str, payload: dict) -> dict:
    rules = list_enabled_rules(db, tenant_id, trigger_type)
    results = []

    for rule in rules:
        condition = _safe_json(rule.condition_json)
        action = _safe_json(rule.action_json)

        if not _matches(condition, payload):
            results.append({
                "rule_id": rule.id,
                "name": rule.name,
                "matched": False,
                "result": {"message": "Condition did not match"},
            })
            continue

        try:
            result = _execute_action(db, tenant_id, tenant_name, rule.action_type, action, payload)
            run = _log_run(
                db,
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                rule_id=rule.id,
                trigger_type=trigger_type,
                action_type=rule.action_type,
                status="executed" if result.get("executed") else "skipped",
                payload=payload,
                result=result,
            )
            results.append({
                "rule_id": rule.id,
                "name": rule.name,
                "matched": True,
                "run_id": run.id,
                "result": result,
            })
        except Exception as e:
            run = _log_run(
                db,
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                rule_id=rule.id,
                trigger_type=trigger_type,
                action_type=rule.action_type,
                status="failed",
                payload=payload,
                result={"error": str(e)},
            )
            results.append({
                "rule_id": rule.id,
                "name": rule.name,
                "matched": True,
                "run_id": run.id,
                "result": {"executed": False, "error": str(e)},
            })

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "trigger_type": trigger_type,
        "rule_count": len(rules),
        "results": results,
    }
