from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.briefing_generator import generate_briefing
from app.db import models
from app.leadership_packet_exports import build_leadership_packet
from app.report_delivery import deliver_report


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def _period_label(days: int) -> str:
    return f"Scheduled Leadership Packet — Last {days} Days — {datetime.now(timezone.utc).date().isoformat()}"


def run_scheduled_packet_once(db: Session, schedule: models.ScheduledLeadershipPacket) -> dict:
    briefing = generate_briefing(
        db,
        tenant_id=schedule.tenant_id,
        tenant_name=schedule.tenant_name,
        briefing_type=schedule.briefing_type,
        audience=schedule.audience,
        period_label=_period_label(schedule.days),
        days=schedule.days,
    )

    packet = build_leadership_packet(
        db,
        tenant_id=schedule.tenant_id,
        tenant_name=schedule.tenant_name,
        briefing_id=briefing.id,
    )

    delivery_payload = {
        "tenant_id": schedule.tenant_id,
        "tenant_name": schedule.tenant_name,
        "report_type": schedule.briefing_type,
        "briefing_id": briefing.id,
        "packet_id": packet.id,
        "title": packet.title,
        "docx_path": packet.docx_path if schedule.include_docx else "",
        "pptx_path": packet.pptx_path if schedule.include_pptx else "",
        "pdf_path": packet.pdf_path if schedule.include_pdf else "",
    }

    delivery = deliver_report(schedule.delivery_channel, schedule.delivery_target, delivery_payload)
    status = "sent" if delivery.get("sent") else "failed"

    row = models.LeadershipPacketDelivery(
        tenant_id=schedule.tenant_id,
        tenant_name=schedule.tenant_name,
        schedule_id=schedule.id,
        briefing_id=briefing.id,
        packet_id=packet.id,
        delivery_channel=schedule.delivery_channel,
        delivery_target=schedule.delivery_target,
        delivery_status=status,
        result_json=_compact(delivery),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "schedule_id": schedule.id,
        "briefing_id": briefing.id,
        "packet_id": packet.id,
        "delivery_id": row.id,
        "delivery_status": status,
        "delivery": delivery,
    }
