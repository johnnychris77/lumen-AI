from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.briefing_generator import generate_briefing
from app.db import models
from app.leadership_packet_exports import build_leadership_packet
from app.report_delivery import deliver_report
from app.distribution_governance import resolve_delivery_target
from app.packet_release_governance import release_allows_delivery


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

    release_state = release_allows_delivery(db, schedule.tenant_id, packet.id)
    if not release_state["allowed"]:
        delivery = {
            "sent": False,
            "channel": schedule.delivery_channel,
            "target": "",
            "reason": release_state["reason"],
            "release_governance": release_state,
        }
        status = "blocked"
    else:
        resolved_target = resolve_delivery_target(
        db,
        schedule.tenant_id,
        schedule.delivery_target,
        getattr(schedule, "distribution_list_id", 0) or 0,
    )

        if not resolved_target["allowed"]:
            delivery = {
                "sent": False,
                "channel": schedule.delivery_channel,
                "target": resolved_target.get("target", ""),
                "governance": resolved_target,
                "release_governance": release_state,
                "reason": resolved_target.get("reason", "Delivery blocked by governance"),
            }
            status = "blocked"
        else:
            delivery = deliver_report(schedule.delivery_channel, resolved_target["target"], delivery_payload)
            delivery["governance"] = resolved_target
            delivery["release_governance"] = release_state
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
