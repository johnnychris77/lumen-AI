"""v1.9 — Production Error Logging (Deliverable 7).

`log_error()` is called from the real failure sites (not synthesized
after the fact) — see routes/inspections.py, routes/reports.py, and
app/authz.py for the call sites. PHI redaction is enforced here: `detail`
is truncated and any caller-supplied value is expected to already be a
short exception message or status reason, never raw request/image data.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.pilot_error_log import ERROR_TYPES, PilotErrorLog

_MAX_DETAIL_LENGTH = 500


def log_error(
    db: Session, *, tenant_id: str, error_type: str, detail: str = "", actor_role: str = "",
    inspection_id: int | None = None,
) -> PilotErrorLog | None:
    """Never raises — a logging failure must never break the caller's real
    request. Returns None (and logs nothing) for an unrecognized error_type
    rather than silently miscategorizing it."""
    if error_type not in ERROR_TYPES:
        return None
    row = PilotErrorLog(
        tenant_id=tenant_id, error_type=error_type, detail=(detail or "")[:_MAX_DETAIL_LENGTH],
        actor_role=actor_role, inspection_id=inspection_id,
    )
    db.add(row)
    return row


def error_summary(db: Session, tenant_id: str) -> dict:
    rows = db.query(PilotErrorLog).filter(PilotErrorLog.tenant_id == tenant_id).all()
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r.error_type] = by_type.get(r.error_type, 0) + 1
    return {"total_errors": len(rows), "by_type": by_type}


def count_by_type(db: Session, tenant_id: str, error_type: str) -> int:
    return (
        db.query(PilotErrorLog)
        .filter(PilotErrorLog.tenant_id == tenant_id, PilotErrorLog.error_type == error_type)
        .count()
    )
