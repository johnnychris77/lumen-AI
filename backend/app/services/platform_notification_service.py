"""v4.0 — LumenAI OS (Project Genesis), Section 1: Platform Core —
Notification Engine.

No unified notification service existed before Genesis — three separate
per-sprint notification tables do: `app/models/or_connect.py::
CaseNotification`, `app/models/workflow.py::WorkflowNotification`, and
`app/models/mobile.py::MobileNotification`. This module composes all
three into one read-only, time-ordered feed for the Platform Launcher
(Section 4) rather than adding a fourth notification table.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.mobile import MobileNotification
from app.models.or_connect import CaseNotification
from app.models.workflow import WorkflowNotification


def _normalize(source: str, *, id_: int, created_at, message: str, read: bool, recipient_role: str = "") -> dict:
    return {
        "source": source,
        "id": id_,
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        "message": message,
        "read": read,
        "recipient_role": recipient_role,
    }


def unified_notifications(db: Session, tenant_id: str, *, recipient_role: str = "", limit: int = 50) -> list[dict]:
    items: list[dict] = []

    case_q = db.query(CaseNotification).filter(CaseNotification.tenant_id == tenant_id)
    if recipient_role:
        case_q = case_q.filter(CaseNotification.recipient_role == recipient_role)
    for n in case_q.order_by(CaseNotification.id.desc()).limit(limit).all():
        items.append(_normalize("or_connect", id_=n.id, created_at=n.created_at, message=n.message, read=n.read, recipient_role=n.recipient_role))

    wf_q = db.query(WorkflowNotification).filter(WorkflowNotification.tenant_id == tenant_id)
    if recipient_role:
        wf_q = wf_q.filter(WorkflowNotification.recipient_role == recipient_role)
    for n in wf_q.order_by(WorkflowNotification.id.desc()).limit(limit).all():
        items.append(_normalize("workflow", id_=n.id, created_at=n.created_at, message=n.message, read=n.read, recipient_role=n.recipient_role))

    mobile_q = db.query(MobileNotification).filter(MobileNotification.tenant_id == tenant_id)
    for n in mobile_q.order_by(MobileNotification.id.desc()).limit(limit).all():
        items.append(_normalize(
            "mobile", id_=n.id, created_at=n.created_at, message=n.title or n.body,
            read=(n.read_status == "read"),
        ))

    items.sort(key=lambda i: i["created_at"] or "", reverse=True)
    return items[:limit]


def unread_count(db: Session, tenant_id: str, *, recipient_role: str = "") -> int:
    return sum(1 for n in unified_notifications(db, tenant_id, recipient_role=recipient_role, limit=500) if not n["read"])
