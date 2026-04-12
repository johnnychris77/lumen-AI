from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.branding import get_branding
from app.db import models
from app.executive_reporting import build_board_narrative, build_scorecard_summary


def _compact(value: Any, limit: int = 4000) -> str:
    return json.dumps(value, default=str)[:limit]


def _latest_subscription(db: Session, tenant_id: str):
    return (
        db.query(models.TenantSubscription)
        .filter(models.TenantSubscription.tenant_id == tenant_id)
        .order_by(models.TenantSubscription.id.desc())
        .first()
    )


def _latest_scorecard(db: Session, tenant_id: str):
    return (
        db.query(models.ExecutiveScorecard)
        .filter(models.ExecutiveScorecard.tenant_id == tenant_id)
        .order_by(models.ExecutiveScorecard.id.desc())
        .first()
    )


def _governance_summary(db: Session, tenant_id: str) -> dict:
    approvals = (
        db.query(models.GovernanceApproval)
        .filter(models.GovernanceApproval.tenant_id == tenant_id)
        .all()
    )
    return {
        "pending": sum(1 for x in approvals if (x.status or "") == "pending"),
        "approved": sum(1 for x in approvals if (x.status or "") == "approved"),
        "rejected": sum(1 for x in approvals if (x.status or "") == "rejected"),
        "execution_failed": sum(1 for x in approvals if (getattr(x, "execution_status", "") or "") == "failed"),
    }


def _finance_summary(db: Session, tenant_id: str) -> dict:
    payments = (
        db.query(models.PaymentEvent)
        .filter(models.PaymentEvent.tenant_id == tenant_id)
        .all()
    )
    invoices = (
        db.query(models.InvoiceLineItem)
        .filter(models.InvoiceLineItem.tenant_id == tenant_id)
        .all()
    )
    return {
        "payment_failed_count": sum(1 for x in payments if (x.status or "") == "failed"),
        "payment_succeeded_count": sum(1 for x in payments if (x.status or "") == "succeeded"),
        "billed_cents": sum(int(x.amount_cents or 0) for x in invoices),
    }


def _compliance_summary(db: Session, tenant_id: str) -> dict:
    audits = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.tenant_id == tenant_id)
        .all()
    )
    rollbacks = (
        db.query(models.GovernanceRollback)
        .filter(models.GovernanceRollback.tenant_id == tenant_id)
        .all()
    )
    return {
        "audit_count": len(audits),
        "compliance_flagged_count": sum(1 for x in audits if bool(getattr(x, "compliance_flag", False))),
        "rollback_count": len(rollbacks),
    }


def build_slide_outline(
    *,
    branding: dict,
    briefing_type: str,
    period_label: str,
    scorecard_summary: dict,
    governance: dict,
    finance: dict,
    compliance: dict,
) -> list[dict]:
    title = branding["display_name"] or branding["tenant_name"]

    slides = [
        {
            "title": f"{title} — {briefing_type.replace('_', ' ').title()}",
            "subtitle": period_label,
            "bullets": [
                branding.get("welcome_text", "") or f"Executive briefing for {title}",
                f"Prepared for leadership review: {period_label}",
            ],
        },
        {
            "title": "Executive KPI Snapshot",
            "bullets": [
                f"Inspections processed: {scorecard_summary.get('inspection_count', 0)}",
                f"High-risk findings: {scorecard_summary.get('high_risk_count', 0)} ({scorecard_summary.get('high_risk_rate', 0)}%)",
                f"Clean rate: {scorecard_summary.get('clean_rate', 0)}%",
            ],
        },
        {
            "title": "Operational Trends",
            "bullets": [
                f"Top issue: {(scorecard_summary.get('top_issues') or [{'name':'n/a'}])[0]['name']}",
                f"Top vendor: {(scorecard_summary.get('top_vendors') or [{'name':'n/a'}])[0]['name']}",
                f"Top site: {(scorecard_summary.get('top_sites') or [{'name':'n/a'}])[0]['name']}",
            ],
        },
        {
            "title": "Governance and Compliance",
            "bullets": [
                f"Pending approvals: {governance.get('pending', 0)}",
                f"Approved actions: {governance.get('approved', 0)}",
                f"Execution failures: {governance.get('execution_failed', 0)}",
                f"Compliance audit events: {compliance.get('audit_count', 0)}",
            ],
        },
        {
            "title": "Finance and Subscription Health",
            "bullets": [
                f"Invoice line items billed: ${finance.get('billed_cents', 0) / 100:.2f}",
                f"Failed payments: {finance.get('payment_failed_count', 0)}",
                f"Recovered/succeeded payments: {finance.get('payment_succeeded_count', 0)}",
            ],
        },
    ]

    if briefing_type == "compliance_review":
        slides.append({
            "title": "Compliance Review Focus",
            "bullets": [
                f"Compliance-flagged audit events: {compliance.get('compliance_flagged_count', 0)}",
                f"Rollback records available: {compliance.get('rollback_count', 0)}",
                "Review legal hold, evidence exports, and governance execution outcomes.",
            ],
        })

    return slides


def build_memo(
    *,
    branding: dict,
    briefing_type: str,
    audience: str,
    period_label: str,
    scorecard_summary: dict,
    governance: dict,
    finance: dict,
    compliance: dict,
    subscription: dict,
) -> str:
    intro = f"{branding['display_name']} {briefing_type.replace('_', ' ').title()} for {period_label}"
    body = build_board_narrative(scorecard_summary)

    tail = (
        f"\n\nGovernance summary: {governance.get('pending', 0)} pending approvals, "
        f"{governance.get('approved', 0)} approved actions, and "
        f"{governance.get('execution_failed', 0)} execution failures."
        f"\nFinance summary: ${finance.get('billed_cents', 0) / 100:.2f} billed, "
        f"{finance.get('payment_failed_count', 0)} failed payments, and "
        f"{finance.get('payment_succeeded_count', 0)} successful payments."
        f"\nCompliance summary: {compliance.get('audit_count', 0)} audit events, "
        f"{compliance.get('compliance_flagged_count', 0)} compliance-flagged records, and "
        f"{compliance.get('rollback_count', 0)} rollback entries."
        f"\nSubscription status: {subscription.get('plan_name', 'n/a')} plan, "
        f"status {subscription.get('status', 'n/a')}."
    )

    close = "\n\nRecommended leadership action: review high-risk trend concentration, payment stability, and pending governance items."

    return f"{intro}\n\nAudience: {audience}\n\n{body}{tail}{close}"


def generate_briefing(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    briefing_type: str,
    audience: str,
    period_label: str,
    days: int = 30,
):
    branding = get_branding(db, tenant_id, tenant_name)
    scorecard_summary = build_scorecard_summary(db, tenant_id, tenant_name, days)
    governance = _governance_summary(db, tenant_id)
    finance = _finance_summary(db, tenant_id)
    compliance = _compliance_summary(db, tenant_id)
    sub = _latest_subscription(db, tenant_id)
    subscription = {
        "plan_name": getattr(sub, "plan_name", "n/a"),
        "status": getattr(sub, "status", "n/a"),
    }

    slides = build_slide_outline(
        branding=branding,
        briefing_type=briefing_type,
        period_label=period_label,
        scorecard_summary=scorecard_summary,
        governance=governance,
        finance=finance,
        compliance=compliance,
    )

    memo = build_memo(
        branding=branding,
        briefing_type=briefing_type,
        audience=audience,
        period_label=period_label,
        scorecard_summary=scorecard_summary,
        governance=governance,
        finance=finance,
        compliance=compliance,
        subscription=subscription,
    )

    title = f"{branding['display_name']} — {briefing_type.replace('_', ' ').title()}"

    row = models.GeneratedBriefing(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        briefing_type=briefing_type,
        audience=audience,
        period_label=period_label,
        title=title,
        slide_outline_json=json.dumps(slides)[:12000],
        memo_text=memo[:12000],
        summary_json=_compact({
            "scorecard_summary": scorecard_summary,
            "governance": governance,
            "finance": finance,
            "compliance": compliance,
            "subscription": subscription,
        }),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
