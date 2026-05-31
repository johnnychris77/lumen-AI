from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from app.services.capa_service import create_capa


_VENDOR_EVENTS: List[Dict] = []


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
) -> Dict:
    event = {
        "id": str(uuid4()),
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


def list_vendor_events(limit: int = 50) -> List[Dict]:
    return _VENDOR_EVENTS[:limit]


def vendor_governance_summary() -> Dict:
    total = len(_VENDOR_EVENTS)
    open_events = len([e for e in _VENDOR_EVENTS if e.get("status") == "open"])
    high_risk = len([
        e for e in _VENDOR_EVENTS
        if e.get("risk_level") in {"high", "critical"}
    ])
    linked_capas = len([e for e in _VENDOR_EVENTS if e.get("capa_id")])

    vendor_counts: Dict[str, int] = {}
    for event in _VENDOR_EVENTS:
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
    )

    create_vendor_event(
        vendor_name="DePuy Synthes",
        event_type="Missing Instrument Signal",
        event_summary="Vendor tray received with missing or incomplete instrument configuration.",
        risk_level="medium",
        site="St Mary",
        device_or_tray="Loaner tray",
        owner="SPD / OR Leadership",
    )

    create_vendor_event(
        vendor_name="Medtronic",
        event_type="Documentation / IFU Review",
        event_summary="Vendor device workflow requires additional IFU review and documentation traceability.",
        risk_level="medium",
        site="St Francis",
        device_or_tray="Specialty device set",
        owner="Quality / Operations",
    )


seed_vendor_events_if_empty()


def get_vendor_event(event_id: str) -> Optional[Dict]:
    for event in _VENDOR_EVENTS:
        if event.get("id") == event_id:
            return event
    return None


def link_vendor_event_to_capa(event_id: str, capa_id: str) -> Optional[Dict]:
    event = get_vendor_event(event_id)
    if not event:
        return None

    event["capa_id"] = capa_id
    event["updated_at"] = _utc_now()
    return event


def create_capa_from_vendor_event(event_id: str) -> Optional[Dict]:
    event = get_vendor_event(event_id)
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
    )

    link_vendor_event_to_capa(event_id, capa["id"])

    return {
        "vendor_event": get_vendor_event(event_id),
        "capa": capa,
    }


def vendor_capa_linkage_summary() -> Dict:
    total = len(_VENDOR_EVENTS)
    linked = [event for event in _VENDOR_EVENTS if event.get("capa_id")]
    unlinked = [event for event in _VENDOR_EVENTS if not event.get("capa_id")]

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
