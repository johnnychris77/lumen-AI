from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4


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
