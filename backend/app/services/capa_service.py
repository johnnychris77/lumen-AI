from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4


_CAPA_STORE: List[Dict] = []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_capa(
    title: str,
    source: str = "manual",
    description: Optional[str] = None,
    risk_level: str = "medium",
    owner: Optional[str] = None,
    due_date: Optional[str] = None,
    corrective_action: Optional[str] = None,
    preventive_action: Optional[str] = None,
    status: str = "open",
) -> Dict:
    capa = {
        "id": str(uuid4()),
        "title": title,
        "source": source,
        "description": description or "",
        "risk_level": risk_level,
        "owner": owner or "Unassigned",
        "due_date": due_date,
        "corrective_action": corrective_action or "",
        "preventive_action": preventive_action or "",
        "status": status,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }

    _CAPA_STORE.insert(0, capa)
    return capa


def list_capas(limit: int = 50) -> List[Dict]:
    return _CAPA_STORE[:limit]


def capa_summary() -> Dict:
    total = len(_CAPA_STORE)
    open_count = len([item for item in _CAPA_STORE if item.get("status") == "open"])
    high_risk = len(
        [
            item
            for item in _CAPA_STORE
            if item.get("risk_level") in {"high", "critical"}
        ]
    )

    return {
        "total": total,
        "open": open_count,
        "high_risk": high_risk,
        "closed": len([item for item in _CAPA_STORE if item.get("status") == "closed"]),
    }


def create_capa_from_audit_signal(signal: Dict) -> Dict:
    event_type = signal.get("event_type") or "Audit Signal"
    risk_level = signal.get("risk_level") or "medium"
    event_summary = signal.get("event_summary") or signal.get("description") or ""

    title = f"CAPA Review: {event_type}"

    corrective_action = (
        "Contain issue, review affected workflow, and document immediate correction."
    )

    preventive_action = (
        "Perform root cause review, define process control, and monitor recurrence."
    )

    return create_capa(
        title=title,
        source="audit_signal",
        description=event_summary,
        risk_level=risk_level,
        owner=signal.get("owner") or "Quality / Operations",
        due_date=signal.get("due_date"),
        corrective_action=corrective_action,
        preventive_action=preventive_action,
        status="open",
    )
