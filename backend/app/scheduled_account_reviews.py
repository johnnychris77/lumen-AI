from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.account_review_exports import build_account_review_export
from app.account_reviews import generate_account_review_packet
from app.db import models
from app.distribution_governance import resolve_delivery_target
from app.report_delivery import deliver_report


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def _period_label(template: str) -> str:
    now = datetime.now(timezone.utc)
    quarter = ((now.month - 1) // 3) + 1
    return template.format(
        year=now.year,
        month=now.strftime("%B"),
        quarter=f"Q{quarter}",
        date=now.date().isoformat(),
    )


def run_scheduled_account_review_once(db: Session, schedule: models.ScheduledAccountReview) -> dict:
    review = generate_account_review_packet(
        db,
        tenant_id=schedule.tenant_id,
        tenant_name=schedule.tenant_name,
        review_type=schedule.review_type,
        period_label=_period_label(schedule.period_label_template),
    )

    export = build_account_review_export(
        db,
        tenant_id=schedule.tenant_id,
        tenant_name=schedule.tenant_name,
        account_review_id=review.id,
    )

    delivery_payload = {
        "tenant_id": schedule.tenant_id,
        "tenant_name": schedule.tenant_name,
        "report_type": schedule.review_type,
        "account_review_id": review.id,
        "export_id": export.id,
        "title": export.title,
        "docx_path": export.docx_path if schedule.include_docx else "",
        "pptx_path": export.pptx_path if schedule.include_pptx else "",
        "pdf_path": export.pdf_path if schedule.include_pdf else "",
    }

    resolved_target = resolve_delivery_target(
        db,
        schedule.tenant_id,
        schedule.delivery_target,
        schedule.distribution_list_id or 0,
    )

    if not resolved_target["allowed"]:
        delivery = {
            "sent": False,
            "channel": schedule.delivery_channel,
            "target": resolved_target.get("target", ""),
            "governance": resolved_target,
            "reason": resolved_target.get("reason", "Delivery blocked by governance"),
        }
        status = "blocked"
    else:
        delivery = deliver_report(schedule.delivery_channel, resolved_target["target"], delivery_payload)
        delivery["governance"] = resolved_target
        status = "sent" if delivery.get("sent") else "failed"

    row = models.AccountReviewDelivery(
        tenant_id=schedule.tenant_id,
        tenant_name=schedule.tenant_name,
        schedule_id=schedule.id,
        account_review_id=review.id,
        export_id=export.id,
        delivery_channel=schedule.delivery_channel,
        delivery_target=resolved_target.get("target", schedule.delivery_target),
        delivery_status=status,
        result_json=_compact(delivery),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "schedule_id": schedule.id,
        "account_review_id": review.id,
        "export_id": export.id,
        "delivery_id": row.id,
        "delivery_status": status,
        "delivery": delivery,
    }
