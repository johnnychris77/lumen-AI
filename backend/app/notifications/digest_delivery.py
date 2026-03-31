from __future__ import annotations

import os
import uuid
import requests
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.notifications.email_delivery import send_email_with_attachment
from app.routes.board_reporting import build_board_report_xlsx_bytes


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(raw: str) -> list[str]:
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _parse_csv_env(name: str) -> list[str]:
    return _parse_csv(os.getenv(name, "").strip())


def _log_digest_delivery(
    db: Session,
    *,
    digest_type: str,
    channel: str,
    recipients: list[str],
    sent: bool,
    status_code: str,
    failure_reason: str,
    delivery_batch_id: str,
    payload_summary: str,
):
    row = models.DigestDelivery(
        digest_type=digest_type,
        channel=channel,
        recipients=",".join(recipients),
        sent=sent,
        status_code=status_code,
        failure_reason=failure_reason,
        delivery_batch_id=delivery_batch_id,
        payload_summary=payload_summary[:4000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _slack_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")) and _truthy(os.getenv("LUMENAI_SLACK_ENABLED", "false"))


def _email_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")) and _truthy(os.getenv("LUMENAI_EMAIL_ENABLED", "false"))


def build_digest_message(digest: dict[str, Any], scope_label: str = "enterprise") -> str:
    s = digest.get("executive_summary", {})
    narrative = digest.get("leadership_narrative", {})
    top_sites = ", ".join([f"{x['label']} ({x['count']})" for x in s.get("top_sites", [])[:3]]) or "none"
    top_vendors = ", ".join([f"{x['label']} ({x['count']})" for x in s.get("top_vendors", [])[:3]]) or "none"

    return (
        f"LumenAI Weekly Executive Digest [{scope_label}]\n"
        f"- Total inspections: {s.get('total_inspections', 0)}\n"
        f"- Completion rate: {round(float(s.get('completion_rate', 0.0)) * 100, 1)}%\n"
        f"- Open alerts: {s.get('open_alerts', 0)}\n"
        f"- High risk findings: {s.get('high_risk_count', 0)}\n"
        f"- QA override rate: {round(float(s.get('qa_override_rate', 0.0)) * 100, 1)}%\n"
        f"- Top sites: {top_sites}\n"
        f"- Top vendors: {top_vendors}\n\n"
        f"{narrative.get('headline', '')}\n"
        f"{narrative.get('quality_note', '')}\n"
        f"{narrative.get('operations_note', '')}"
    ).strip()


def _filter_digest_for_site(digest_payload: dict[str, Any], site_name: str) -> dict[str, Any]:
    if site_name == "all":
        return digest_payload

    site_benchmark = [x for x in digest_payload.get("site_benchmark", []) if (x.get("site_name") or "").strip().lower() == site_name.strip().lower()]
    executive_summary = dict(digest_payload.get("executive_summary", {}))
    if site_benchmark:
        site = site_benchmark[0]
        executive_summary["total_inspections"] = site.get("total_inspections", 0)
        executive_summary["open_alerts"] = site.get("open_alerts", 0)
        executive_summary["resolved_alerts"] = site.get("resolved_alerts", 0)
        executive_summary["high_risk_count"] = site.get("high_risk_count", 0)
        executive_summary["qa_override_rate"] = site.get("qa_override_rate", 0.0)
        executive_summary["top_sites"] = [{"label": site.get("site_name", site_name), "count": site.get("total_inspections", 0)}]

    leadership_narrative = dict(digest_payload.get("leadership_narrative", {}))
    leadership_narrative["headline"] = f"Site digest for {site_name}: {executive_summary.get('total_inspections', 0)} inspections, {executive_summary.get('open_alerts', 0)} open alerts."

    return {
        **digest_payload,
        "executive_summary": executive_summary,
        "site_benchmark": site_benchmark,
        "leadership_narrative": leadership_narrative,
    }


def _get_subscriptions(db: Session, digest_type: str) -> list[models.DigestSubscription]:
    rows = (
        db.query(models.DigestSubscription)
        .filter(
            models.DigestSubscription.digest_type == digest_type,
            models.DigestSubscription.is_enabled == True,
        )
        .order_by(models.DigestSubscription.id.asc())
        .all()
    )
    return rows


def deliver_digest(
    db: Session,
    *,
    digest_type: str,
    digest_payload: dict[str, Any],
) -> dict[str, Any]:
    enabled = _truthy(os.getenv("LUMENAI_DIGEST_AUTOMATION_ENABLED", "false"))
    batch_id = str(uuid.uuid4())
    results: list[dict[str, Any]] = []

    if not enabled:
        _log_digest_delivery(
            db,
            digest_type=digest_type,
            channel="system",
            recipients=[],
            sent=False,
            status_code="DISABLED",
            failure_reason="Digest automation disabled",
            delivery_batch_id=batch_id,
            payload_summary="Digest automation disabled",
        )
        return {
            "enabled": False,
            "delivery_batch_id": batch_id,
            "results": [],
            "message": "Digest automation disabled",
        }

    subscriptions = _get_subscriptions(db, digest_type)

    if not subscriptions:
        fallback_channels = [x.strip().lower() for x in os.getenv("LUMENAI_DIGEST_AUTOMATION_CHANNEL", "slack").split(",") if x.strip()]
        if "slack" in fallback_channels:
            subscriptions.append(type("Sub", (), {
                "name": "Default Executive Slack",
                "role_scope": "executive",
                "site_name": "all",
                "channel": "slack",
                "recipients": os.getenv("LUMENAI_EXECUTIVE_SLACK_CHANNEL", "").strip(),
                "digest_type": digest_type,
            })())
        if "email" in fallback_channels:
            subscriptions.append(type("Sub", (), {
                "name": "Default Executive Email",
                "role_scope": "executive",
                "site_name": "all",
                "channel": "email",
                "recipients": ",".join(_parse_csv_env("LUMENAI_EXECUTIVE_EMAILS")),
                "digest_type": digest_type,
            })())

    for sub in subscriptions:
        scoped_digest = _filter_digest_for_site(digest_payload, getattr(sub, "site_name", "all") or "all")
        scope_label = f"{getattr(sub, 'role_scope', 'executive')}:{getattr(sub, 'site_name', 'all')}"
        message = build_digest_message(scoped_digest, scope_label=scope_label)
        recipients = _parse_csv(getattr(sub, "recipients", "") or "")
        channel = (getattr(sub, "channel", "") or "").strip().lower()

        if channel == "slack":
            webhook = os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip()
            if not _slack_enabled():
                _log_digest_delivery(
                    db, digest_type=digest_type, channel="slack", recipients=recipients,
                    sent=False, status_code="DISABLED", failure_reason="Slack channel disabled",
                    delivery_batch_id=batch_id, payload_summary=message
                )
                results.append({"subscription": getattr(sub, "name", "unknown"), "channel": "slack", "sent": False, "reason": "Slack channel disabled"})
            elif not webhook:
                _log_digest_delivery(
                    db, digest_type=digest_type, channel="slack", recipients=recipients,
                    sent=False, status_code="NOT_CONFIGURED", failure_reason="Slack webhook not configured",
                    delivery_batch_id=batch_id, payload_summary=message
                )
                results.append({"subscription": getattr(sub, "name", "unknown"), "channel": "slack", "sent": False, "reason": "Slack webhook not configured"})
            else:
                try:
                    resp = requests.post(webhook, json={"text": message}, timeout=20)
                    ok = resp.status_code == 200 and resp.text.strip().lower() == "ok"
                    _log_digest_delivery(
                        db, digest_type=digest_type, channel="slack", recipients=recipients,
                        sent=ok, status_code=str(resp.status_code), failure_reason="" if ok else resp.text[:2000],
                        delivery_batch_id=batch_id, payload_summary=message
                    )
                    results.append({
                        "subscription": getattr(sub, "name", "unknown"),
                        "channel": "slack",
                        "sent": ok,
                        "status_code": resp.status_code,
                        "response_text": resp.text[:500],
                    })
                except Exception as e:
                    _log_digest_delivery(
                        db, digest_type=digest_type, channel="slack", recipients=recipients,
                        sent=False, status_code="REQUEST_ERROR", failure_reason=str(e),
                        delivery_batch_id=batch_id, payload_summary=message
                    )
                    results.append({"subscription": getattr(sub, "name", "unknown"), "channel": "slack", "sent": False, "reason": str(e)})

        elif channel == "email":
            if not _email_enabled():
                _log_digest_delivery(
                    db, digest_type=digest_type, channel="email", recipients=recipients,
                    sent=False, status_code="DISABLED", failure_reason="Email channel disabled",
                    delivery_batch_id=batch_id, payload_summary=message
                )
                results.append({"subscription": getattr(sub, "name", "unknown"), "channel": "email", "sent": False, "reason": "Email channel disabled"})
            else:
                xlsx_bytes = build_board_report_xlsx_bytes(scoped_digest)
                email_result = send_email_with_attachment(
                    subject=f"LumenAI Weekly Digest [{scope_label}]",
                    body=message,
                    attachment_bytes=xlsx_bytes,
                    attachment_filename=f"lumenai_{(getattr(sub, 'site_name', 'all') or 'all').lower()}_weekly_digest.xlsx",
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                _log_digest_delivery(
                    db,
                    digest_type=digest_type,
                    channel="email",
                    recipients=recipients or email_result.get("recipients", []),
                    sent=bool(email_result.get("sent", False)),
                    status_code=str(email_result.get("status_code", "")),
                    failure_reason=str(email_result.get("failure_reason", "")),
                    delivery_batch_id=batch_id,
                    payload_summary=message,
                )
                results.append({
                    "subscription": getattr(sub, "name", "unknown"),
                    "channel": "email",
                    "sent": bool(email_result.get("sent", False)),
                    "status_code": email_result.get("status_code", ""),
                    "reason": email_result.get("failure_reason", ""),
                })

    return {
        "enabled": True,
        "delivery_batch_id": batch_id,
        "results": results,
    }
