from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models

DEFAULT_TEMPLATES = {
    ("alert", "slack"): {
        "subject_template": "",
        "body_template": "LumenAI Alert\nTenant: {tenant_name}\nInspection: {inspection_id}\nIssue: {detected_issue}\nRisk: {risk_score}",
    },
    ("approval", "slack"): {
        "subject_template": "",
        "body_template": "Approval needed\nTenant: {tenant_name}\nRequest: {request_type}\nTarget: {target_resource}",
    },
    ("dunning", "email"): {
        "subject_template": "Payment update for {tenant_name}",
        "body_template": "Plan: {plan_name}\nStatus: {status}\nPayment: {last_payment_status}\nRenewal: {current_period_end}",
    },
    ("digest", "email"): {
        "subject_template": "{tenant_name} Executive Digest",
        "body_template": "Weekly summary for {tenant_name}\nInspections: {inspection_count}\nAlerts: {alert_count}\nExports: {export_count}",
    },
}


def get_template(db: Session, tenant_id: str, tenant_name: str, template_key: str, channel: str) -> dict:
    row = (
        db.query(models.NotificationTemplate)
        .filter(
            models.NotificationTemplate.tenant_id == tenant_id,
            models.NotificationTemplate.template_key == template_key,
            models.NotificationTemplate.channel == channel,
            models.NotificationTemplate.is_enabled == True,
        )
        .order_by(models.NotificationTemplate.id.desc())
        .first()
    )

    if row:
        return {
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant_name,
            "template_key": row.template_key,
            "channel": row.channel,
            "subject_template": row.subject_template,
            "body_template": row.body_template,
            "source": "configured",
        }

    default = DEFAULT_TEMPLATES.get((template_key, channel), {"subject_template": "", "body_template": ""})
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "template_key": template_key,
        "channel": channel,
        "subject_template": default["subject_template"],
        "body_template": default["body_template"],
        "source": "default",
    }


def render_template(db: Session, tenant_id: str, tenant_name: str, template_key: str, channel: str, context: dict) -> dict:
    template = get_template(db, tenant_id, tenant_name, template_key, channel)
    safe_context = {k: ("" if v is None else v) for k, v in context.items()}
    subject = template["subject_template"].format(**safe_context) if template["subject_template"] else ""
    body = template["body_template"].format(**safe_context)
    return {
        "template": template,
        "rendered_subject": subject,
        "rendered_body": body,
    }
