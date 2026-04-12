from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db import models


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _since(days: int) -> datetime:
    return _now() - timedelta(days=days)


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def build_scorecard_summary(db: Session, tenant_id: str, tenant_name: str, days: int = 30) -> dict:
    inspections = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= _since(days),
        )
        .all()
    )

    usage_events = (
        db.query(models.UsageEvent)
        .filter(
            models.UsageEvent.tenant_id == tenant_id,
            models.UsageEvent.created_at >= _since(days),
        )
        .all()
    )

    approvals = (
        db.query(models.GovernanceApproval)
        .filter(
            models.GovernanceApproval.tenant_id == tenant_id,
            models.GovernanceApproval.created_at >= _since(days),
        )
        .all()
    )

    payments = (
        db.query(models.PaymentEvent)
        .filter(
            models.PaymentEvent.tenant_id == tenant_id,
            models.PaymentEvent.created_at >= _since(days),
        )
        .all()
    )

    invoice_items = (
        db.query(models.InvoiceLineItem)
        .filter(models.InvoiceLineItem.tenant_id == tenant_id)
        .all()
    )

    inspection_count = len(inspections)
    high_risk_count = sum(1 for r in inspections if int(r.risk_score or 0) >= 80)
    clean_count = sum(1 for r in inspections if (r.detected_issue or "") == "clean")
    issue_mix = defaultdict(int)
    vendor_mix = defaultdict(int)
    site_mix = defaultdict(int)

    for row in inspections:
        issue_mix[row.detected_issue or "unknown"] += 1
        vendor_mix[row.vendor_name or "unknown"] += 1
        site_mix[row.site_name or "unknown"] += 1

    usage_mix = defaultdict(int)
    for row in usage_events:
        usage_mix[row.event_type or "unknown"] += int(row.quantity or 0)

    approval_pending = sum(1 for r in approvals if (r.status or "") == "pending")
    approval_approved = sum(1 for r in approvals if (r.status or "") == "approved")
    approval_failed = sum(1 for r in approvals if (r.execution_status or "") == "failed")

    payment_failed = sum(1 for r in payments if (r.status or "") == "failed")
    payment_succeeded = sum(1 for r in payments if (r.status or "") == "succeeded")
    billed_cents = sum(int(r.amount_cents or 0) for r in invoice_items)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "days": days,
        "inspection_count": inspection_count,
        "high_risk_count": high_risk_count,
        "clean_count": clean_count,
        "high_risk_rate": round((high_risk_count / inspection_count) * 100, 2) if inspection_count else 0,
        "clean_rate": round((clean_count / inspection_count) * 100, 2) if inspection_count else 0,
        "top_issues": [{"name": k, "count": v} for k, v in sorted(issue_mix.items(), key=lambda x: x[1], reverse=True)[:5]],
        "top_vendors": [{"name": k, "count": v} for k, v in sorted(vendor_mix.items(), key=lambda x: x[1], reverse=True)[:5]],
        "top_sites": [{"name": k, "count": v} for k, v in sorted(site_mix.items(), key=lambda x: x[1], reverse=True)[:5]],
        "usage_mix": [{"event_type": k, "quantity": v} for k, v in sorted(usage_mix.items(), key=lambda x: x[0])],
        "governance": {
            "pending": approval_pending,
            "approved": approval_approved,
            "execution_failed": approval_failed,
        },
        "finance": {
            "payment_failed_count": payment_failed,
            "payment_succeeded_count": payment_succeeded,
            "billed_cents": billed_cents,
        },
    }


def build_board_narrative(summary: dict) -> str:
    top_issue = summary["top_issues"][0]["name"] if summary["top_issues"] else "no dominant issue"
    top_vendor = summary["top_vendors"][0]["name"] if summary["top_vendors"] else "no dominant vendor"
    top_site = summary["top_sites"][0]["name"] if summary["top_sites"] else "no dominant site"

    return (
        f"Over the last {summary['days']} days, {summary['tenant_name']} processed "
        f"{summary['inspection_count']} inspections, with {summary['high_risk_count']} high-risk findings "
        f"({summary['high_risk_rate']}%) and a clean rate of {summary['clean_rate']}%. "
        f"The leading issue trend was {top_issue}, with the highest concentration of activity tied to vendor "
        f"{top_vendor} and site {top_site}. "
        f"Governance activity included {summary['governance']['pending']} pending approvals, "
        f"{summary['governance']['approved']} approved actions, and "
        f"{summary['governance']['execution_failed']} execution failures. "
        f"Financially, the tenant recorded {summary['finance']['payment_failed_count']} failed payment events, "
        f"{summary['finance']['payment_succeeded_count']} successful payment events, and "
        f"${summary['finance']['billed_cents'] / 100:.2f} in invoice line items. "
        f"Executive attention should focus on reducing high-risk inspection volume, monitoring issue concentration "
        f"around {top_issue}, and sustaining governance and payment stability."
    )


def persist_scorecard(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    scorecard_type: str,
    period_label: str,
    summary: dict,
    narrative_text: str,
):
    row = models.ExecutiveScorecard(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        scorecard_type=scorecard_type,
        period_label=period_label,
        summary_json=_compact(summary),
        narrative_text=narrative_text[:8000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
