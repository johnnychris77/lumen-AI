"""v2.9 — LumenAI Quality (Project Guardian), Section 6: CAPA lifecycle.

Extends `capa_service.py`'s existing raw-sqlite `capas` table additively
(new nullable columns via `ALTER TABLE`) rather than introducing a second
CAPA store — `docs/quality/capa-integration.md` already establishes "no
parallel CAPA system" as policy, and that store predates any SQLAlchemy
model for CAPA.

Adds the real Open -> Assigned -> In Progress -> Verified -> Closed
lifecycle the existing `status` free-string column never enforced, plus a
typed `recommendation_type`, tenant scoping, and linkage back to the quality
event / inspection / root cause assignment that produced the CAPA.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.services import capa_service

LIFECYCLE_OPEN = "open"
LIFECYCLE_ASSIGNED = "assigned"
LIFECYCLE_IN_PROGRESS = "in_progress"
LIFECYCLE_VERIFIED = "verified"
LIFECYCLE_CLOSED = "closed"
CAPA_LIFECYCLE_STATES = [
    LIFECYCLE_OPEN, LIFECYCLE_ASSIGNED, LIFECYCLE_IN_PROGRESS, LIFECYCLE_VERIFIED, LIFECYCLE_CLOSED,
]

_VALID_TRANSITIONS: dict[str, set[str]] = {
    LIFECYCLE_OPEN: {LIFECYCLE_ASSIGNED, LIFECYCLE_IN_PROGRESS, LIFECYCLE_CLOSED},
    LIFECYCLE_ASSIGNED: {LIFECYCLE_IN_PROGRESS, LIFECYCLE_CLOSED},
    LIFECYCLE_IN_PROGRESS: {LIFECYCLE_VERIFIED, LIFECYCLE_CLOSED},
    LIFECYCLE_VERIFIED: {LIFECYCLE_CLOSED},
    LIFECYCLE_CLOSED: set(),
}

_NEW_COLUMNS = {
    "tenant_id": "TEXT",
    "lifecycle_status": "TEXT",
    "recommendation_type": "TEXT",
    "assignee": "TEXT",
    "linked_event_id": "INTEGER",
    "linked_inspection_id": "INTEGER",
    "root_cause_assignment_id": "INTEGER",
    "verified_by": "TEXT",
    "verified_at": "TEXT",
    "closed_by": "TEXT",
    "closed_at": "TEXT",
}


class InvalidLifecycleTransitionError(Exception):
    pass


def ensure_lifecycle_columns() -> None:
    """Idempotent additive migration — sqlite has no `ADD COLUMN IF NOT EXISTS`."""
    capa_service.init_capa_db()
    with capa_service._connect() as conn:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(capas)").fetchall()}
        for column, sql_type in _NEW_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE capas ADD COLUMN {column} {sql_type}")  # noqa: S608
        conn.commit()


def _row_to_dict(row) -> dict:
    result = capa_service._row_to_dict(row)
    for column in _NEW_COLUMNS:
        result[column] = row[column] if column in row.keys() else None
    result["lifecycle_status"] = result["lifecycle_status"] or LIFECYCLE_OPEN
    return result


def create_capa_with_recommendation(
    tenant_id: str, *, recommendation_type: str, title: str, description: str = "",
    risk_level: str = "medium", owner: Optional[str] = None, due_date: Optional[str] = None,
    linked_event_id: Optional[int] = None, linked_inspection_id: Optional[int] = None,
    root_cause_assignment_id: Optional[int] = None,
) -> dict:
    ensure_lifecycle_columns()
    capa = capa_service.create_capa(
        title=title, source="quality_guardian", description=description, risk_level=risk_level,
        owner=owner, due_date=due_date, status=LIFECYCLE_OPEN,
    )
    with capa_service._connect() as conn:
        conn.execute(
            """
            UPDATE capas SET tenant_id = ?, lifecycle_status = ?, recommendation_type = ?,
                assignee = ?, linked_event_id = ?, linked_inspection_id = ?, root_cause_assignment_id = ?
            WHERE id = ?
            """,
            (
                tenant_id, LIFECYCLE_OPEN, recommendation_type, owner or "", linked_event_id,
                linked_inspection_id, root_cause_assignment_id, capa["id"],
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM capas WHERE id = ?", (capa["id"],)).fetchone()
    return _row_to_dict(row)


def get_capa(tenant_id: str, capa_id: str) -> dict | None:
    ensure_lifecycle_columns()
    with capa_service._connect() as conn:
        row = conn.execute(
            "SELECT * FROM capas WHERE id = ? AND (tenant_id = ? OR tenant_id IS NULL)", (capa_id, tenant_id),
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_capas(tenant_id: str, *, lifecycle_status: str = "", limit: int = 100) -> list[dict]:
    ensure_lifecycle_columns()
    query = "SELECT * FROM capas WHERE (tenant_id = ? OR tenant_id IS NULL)"
    params: list = [tenant_id]
    if lifecycle_status:
        query += " AND lifecycle_status = ?"
        params.append(lifecycle_status)
    query += " ORDER BY datetime(created_at) DESC LIMIT ?"
    params.append(limit)
    with capa_service._connect() as conn:
        rows = conn.execute(query, params).fetchall()  # noqa: S608
    return [_row_to_dict(r) for r in rows]


def advance_lifecycle(tenant_id: str, capa_id: str, new_status: str, *, actor: str) -> dict:
    if new_status not in CAPA_LIFECYCLE_STATES:
        raise InvalidLifecycleTransitionError(f"Unknown lifecycle status '{new_status}'.")

    capa = get_capa(tenant_id, capa_id)
    if capa is None:
        raise ValueError(f"CAPA {capa_id} not found for tenant {tenant_id}.")

    current = capa["lifecycle_status"] or LIFECYCLE_OPEN
    if new_status not in _VALID_TRANSITIONS.get(current, set()):
        raise InvalidLifecycleTransitionError(
            f"Cannot move CAPA from '{current}' to '{new_status}'. Valid next states: "
            f"{sorted(_VALID_TRANSITIONS.get(current, set()))}",
        )

    now = datetime.now(timezone.utc).isoformat()
    fields = {"lifecycle_status": new_status, "updated_at": now}
    if new_status == LIFECYCLE_ASSIGNED:
        fields["assignee"] = actor
    if new_status == LIFECYCLE_VERIFIED:
        fields["verified_by"] = actor
        fields["verified_at"] = now
    if new_status == LIFECYCLE_CLOSED:
        fields["closed_by"] = actor
        fields["closed_at"] = now
        fields["status"] = "closed"

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    with capa_service._connect() as conn:
        conn.execute(f"UPDATE capas SET {set_clause} WHERE id = ?", (*fields.values(), capa_id))  # noqa: S608
        conn.commit()
        row = conn.execute("SELECT * FROM capas WHERE id = ?", (capa_id,)).fetchone()
    return _row_to_dict(row)


def lifecycle_summary(tenant_id: str) -> dict:
    ensure_lifecycle_columns()
    with capa_service._connect() as conn:
        rows = conn.execute(
            "SELECT lifecycle_status, COUNT(*) as n FROM capas WHERE (tenant_id = ? OR tenant_id IS NULL) GROUP BY lifecycle_status",
            (tenant_id,),
        ).fetchall()
    counts = {state: 0 for state in CAPA_LIFECYCLE_STATES}
    for row in rows:
        counts[row["lifecycle_status"] or LIFECYCLE_OPEN] = row["n"]
    return counts
