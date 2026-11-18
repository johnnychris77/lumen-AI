"""Vendor governance events.

Tenant isolation (P472-03 AW-10): every event records the tenant that created
it, and every function here takes the caller's tenant and sees only that
tenant's events. An event of another tenant is indistinguishable from one that
does not exist. Routes pass the tenant of the verified auth context.

The store is still one in-process list: events are lost on restart and differ
between replicas. That is a durability limitation, not an isolation one.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from app.services.capa_service import create_capa, get_capa


_VENDOR_EVENTS: List[Dict] = []

# The three illustrative events seeded at start-up belong to the demo tenant
# (the tenant DEMO_MODE sessions run in). They used to be served to every caller
# as if they were that caller's own governance events.
DEMO_TENANT_ID = "demo"


def _tenant(tenant_id: Optional[str]) -> str:
    tenant = (tenant_id or "").strip() if isinstance(tenant_id, str) else ""
    if not tenant:
        raise ValueError("vendor_governance_service: a tenant_id is required; events are tenant-owned.")
    return tenant


def _events(tenant_id: str) -> List[Dict]:
    tenant = _tenant(tenant_id)
    return [event for event in _VENDOR_EVENTS if event.get("tenant_id") == tenant]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_vendor_event(
    vendor_name: str,
    event_type: str,
    event_summary: str,
    risk_level: str = "medium",
    site: Optional[str] = None,
    device_or_tray: Optional[str] = None,
    owner: Optional[str] = None,
    capa_id: Optional[str] = None,
    *,
    tenant_id: str,
) -> Dict:
    event = {
        "id": str(uuid4()),
        "tenant_id": _tenant(tenant_id),
        "vendor_name": vendor_name,
        "event_type": event_type,
        "event_summary": event_summary,
        "risk_level": risk_level,
        "site": site or "Not specified",
        "device_or_tray": device_or_tray or "Not specified",
        "owner": owner or "Quality / Operations",
        "capa_id": capa_id,
        "status": "open",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }

    _VENDOR_EVENTS.insert(0, event)
    return event


def list_vendor_events(limit: int = 50, *, tenant_id: str) -> List[Dict]:
    return _events(tenant_id)[:limit]


def vendor_governance_summary(*, tenant_id: str) -> Dict:
    events = _events(tenant_id)
    total = len(events)
    open_events = len([e for e in events if e.get("status") == "open"])
    high_risk = len([
        e for e in events
        if e.get("risk_level") in {"high", "critical"}
    ])
    linked_capas = len([e for e in events if e.get("capa_id")])

    vendor_counts: Dict[str, int] = {}
    for event in events:
        vendor = event.get("vendor_name") or "Unknown"
        vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1

    top_vendors = sorted(
        [{"vendor_name": k, "event_count": v} for k, v in vendor_counts.items()],
        key=lambda x: x["event_count"],
        reverse=True,
    )

    return {
        "total_vendor_events": total,
        "open_vendor_events": open_events,
        "high_risk_vendor_events": high_risk,
        "vendor_events_linked_to_capa": linked_capas,
        "top_vendors": top_vendors[:10],
    }


def seed_vendor_events_if_empty() -> None:
    if _VENDOR_EVENTS:
        return

    create_vendor_event(
        vendor_name="Stryker",
        event_type="Tray Quality Signal",
        event_summary="Repeated vendor tray condition issue identified during quality review.",
        risk_level="high",
        site="ORC",
        device_or_tray="Orthopedic vendor tray",
        owner="Quality / Operations",
        tenant_id=DEMO_TENANT_ID,
    )

    create_vendor_event(
        vendor_name="DePuy Synthes",
        event_type="Missing Instrument Signal",
        event_summary="Vendor tray received with missing or incomplete instrument configuration.",
        risk_level="medium",
        site="St Mary",
        device_or_tray="Loaner tray",
        owner="SPD / OR Leadership",
        tenant_id=DEMO_TENANT_ID,
    )

    create_vendor_event(
        vendor_name="Medtronic",
        event_type="Documentation / IFU Review",
        event_summary="Vendor device workflow requires additional IFU review and documentation traceability.",
        risk_level="medium",
        site="St Francis",
        device_or_tray="Specialty device set",
        owner="Quality / Operations",
        tenant_id=DEMO_TENANT_ID,
    )


seed_vendor_events_if_empty()


def get_vendor_event(event_id: str, *, tenant_id: str) -> Optional[Dict]:
    for event in _events(tenant_id):
        if event.get("id") == event_id:
            return event
    return None


class CapaNotFoundError(LookupError):
    """The CAPA to link does not exist in the caller's tenant."""


def link_vendor_event_to_capa(event_id: str, capa_id: str, *, tenant_id: str) -> Optional[Dict]:
    event = get_vendor_event(event_id, tenant_id=tenant_id)
    if not event:
        return None

    # Both ends of the link must belong to the caller: an event can only point at
    # a CAPA of the same tenant.
    if get_capa(capa_id, tenant_id=tenant_id) is None:
        raise CapaNotFoundError(capa_id)

    event["capa_id"] = capa_id
    event["updated_at"] = _utc_now()
    return event


def create_capa_from_vendor_event(event_id: str, *, tenant_id: str) -> Optional[Dict]:
    event = get_vendor_event(event_id, tenant_id=tenant_id)
    if not event:
        return None

    capa = create_capa(
        title=f"Vendor CAPA Review: {event.get('vendor_name')} - {event.get('event_type')}",
        source="vendor_governance",
        description=event.get("event_summary") or "",
        risk_level=event.get("risk_level") or "medium",
        owner=event.get("owner") or "Quality / Operations",
        due_date=None,
        corrective_action="Contain vendor quality signal, review affected trays/devices, and document immediate correction.",
        preventive_action="Trend vendor events, review recurrence, and define vendor accountability controls.",
        status="open",
        tenant_id=tenant_id,
    )

    link_vendor_event_to_capa(event_id, capa["id"], tenant_id=tenant_id)

    return {
        "vendor_event": get_vendor_event(event_id, tenant_id=tenant_id),
        "capa": capa,
    }


def vendor_capa_linkage_summary(*, tenant_id: str) -> Dict:
    events = _events(tenant_id)
    total = len(events)
    linked = [event for event in events if event.get("capa_id")]
    unlinked = [event for event in events if not event.get("capa_id")]

    high_risk_unlinked = [
        event
        for event in unlinked
        if event.get("risk_level") in {"high", "critical"}
    ]

    return {
        "total_vendor_events": total,
        "vendor_events_linked_to_capa": len(linked),
        "vendor_events_without_capa": len(unlinked),
        "high_risk_vendor_events_without_capa": len(high_risk_unlinked),
        "linked_events": linked[:25],
        "unlinked_high_risk_events": high_risk_unlinked[:25],
    }


def build_vendor_governance_powerbi_rows(limit: int = 500, *, tenant_id: str) -> List[Dict]:
    """
    Builds flat Vendor Governance rows for Power BI / analytics export.
    """
    rows = []

    for event in list_vendor_events(limit=limit, tenant_id=tenant_id):
        risk_level = event.get("risk_level") or ""
        capa_id = event.get("capa_id")

        rows.append(
            {
                "vendor_event_id": event.get("id"),
                "vendor_name": event.get("vendor_name"),
                "event_type": event.get("event_type"),
                "event_summary": event.get("event_summary"),
                "risk_level": risk_level,
                "site": event.get("site"),
                "device_or_tray": event.get("device_or_tray"),
                "owner": event.get("owner"),
                "status": event.get("status"),
                "capa_id": capa_id or "",
                "is_high_risk": "true" if risk_level in {"high", "critical"} else "false",
                "is_linked_to_capa": "true" if capa_id else "false",
                "created_at": event.get("created_at"),
                "updated_at": event.get("updated_at"),
            }
        )

    return rows
