import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_path() -> str:
    """
    Supports common SQLite DATABASE_URL values:
    - sqlite:///./lumenai.db
    - sqlite:////tmp/lumenai.db
    If DATABASE_URL is not SQLite, falls back to a local SQLite file.
    """
    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url.startswith("sqlite:///"):
        raw_path = database_url.replace("sqlite:///", "", 1)

        if raw_path.startswith("/"):
            db_path = Path(raw_path)
        else:
            db_path = Path(raw_path).resolve()

        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)

    fallback = Path(os.getenv("CAPA_DB_PATH", "data/lumenai_capa.db")).resolve()
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return str(fallback)


DB_PATH = _database_path()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_capa_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capas (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                description TEXT,
                risk_level TEXT NOT NULL,
                owner TEXT NOT NULL,
                due_date TEXT,
                corrective_action TEXT,
                preventive_action TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_capas_status
            ON capas(status)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_capas_risk_level
            ON capas(risk_level)
            """
        )

        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "source": row["source"],
        "description": row["description"] or "",
        "risk_level": row["risk_level"],
        "owner": row["owner"],
        "due_date": row["due_date"],
        "corrective_action": row["corrective_action"] or "",
        "preventive_action": row["preventive_action"] or "",
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


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
    init_capa_db()

    now = _utc_now()
    capa = {
        "id": str(uuid4()),
        "title": title,
        "source": source or "manual",
        "description": description or "",
        "risk_level": risk_level or "medium",
        "owner": owner or "Unassigned",
        "due_date": due_date,
        "corrective_action": corrective_action or "",
        "preventive_action": preventive_action or "",
        "status": status or "open",
        "created_at": now,
        "updated_at": now,
    }

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO capas (
                id,
                title,
                source,
                description,
                risk_level,
                owner,
                due_date,
                corrective_action,
                preventive_action,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capa["id"],
                capa["title"],
                capa["source"],
                capa["description"],
                capa["risk_level"],
                capa["owner"],
                capa["due_date"],
                capa["corrective_action"],
                capa["preventive_action"],
                capa["status"],
                capa["created_at"],
                capa["updated_at"],
            ),
        )
        conn.commit()

    return capa


def list_capas(limit: int = 50) -> List[Dict]:
    init_capa_db()

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM capas
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_capa(capa_id: str) -> Optional[Dict]:
    init_capa_db()

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM capas
            WHERE id = ?
            """,
            (capa_id,),
        ).fetchone()

    return _row_to_dict(row) if row else None


def capa_summary() -> Dict:
    init_capa_db()

    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM capas").fetchone()["count"]

        open_count = conn.execute(
            "SELECT COUNT(*) AS count FROM capas WHERE status = ?",
            ("open",),
        ).fetchone()["count"]

        closed_count = conn.execute(
            "SELECT COUNT(*) AS count FROM capas WHERE status = ?",
            ("closed",),
        ).fetchone()["count"]

        high_risk = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM capas
            WHERE risk_level IN ('high', 'critical')
            """
        ).fetchone()["count"]

    return {
        "total": total,
        "open": open_count,
        "high_risk": high_risk,
        "closed": closed_count,
        "database": "sqlite",
        "database_path": DB_PATH,
    }



def update_capa(
    capa_id: str,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    due_date: Optional[str] = None,
    risk_level: Optional[str] = None,
    description: Optional[str] = None,
    corrective_action: Optional[str] = None,
    preventive_action: Optional[str] = None,
) -> Optional[Dict]:
    init_capa_db()

    existing = get_capa(capa_id)
    if not existing:
        return None

    updates = {}
    if status is not None:
        updates["status"] = status
    if owner is not None:
        updates["owner"] = owner
    if due_date is not None:
        updates["due_date"] = due_date
    if risk_level is not None:
        updates["risk_level"] = risk_level
    if description is not None:
        updates["description"] = description
    if corrective_action is not None:
        updates["corrective_action"] = corrective_action
    if preventive_action is not None:
        updates["preventive_action"] = preventive_action

    updates["updated_at"] = _utc_now()

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(capa_id)

    with _connect() as conn:
        conn.execute(
            f"""
            UPDATE capas
            SET {set_clause}
            WHERE id = ?
            """,
            values,
        )
        conn.commit()

    return get_capa(capa_id)


def capa_escalation_summary(days_until_due: int = 7) -> Dict:
    """
    Returns overdue and due-soon CAPA counts for governance escalation.
    Uses ISO date strings in due_date where possible.
    """
    init_capa_db()

    today = datetime.now(timezone.utc).date()
    due_soon = []
    overdue = []
    high_risk_overdue = []

    open_capas = [
        capa
        for capa in list_capas(limit=500)
        if capa.get("status") not in {"closed", "cancelled"}
    ]

    for capa in open_capas:
        due_date_value = capa.get("due_date")
        if not due_date_value:
            continue

        try:
            due_date = datetime.fromisoformat(str(due_date_value)).date()
        except ValueError:
            try:
                due_date = datetime.strptime(str(due_date_value), "%Y-%m-%d").date()
            except ValueError:
                continue

        days_remaining = (due_date - today).days
        enriched = dict(capa)
        enriched["days_remaining"] = days_remaining

        if days_remaining < 0:
            overdue.append(enriched)
            if capa.get("risk_level") in {"high", "critical"}:
                high_risk_overdue.append(enriched)
        elif days_remaining <= days_until_due:
            due_soon.append(enriched)

    return {
        "status": "success",
        "module": "capa_workflow",
        "escalation_window_days": days_until_due,
        "summary": {
            "open_capas": len(open_capas),
            "overdue": len(overdue),
            "due_soon": len(due_soon),
            "high_risk_overdue": len(high_risk_overdue),
            "requires_escalation": len(overdue) + len(high_risk_overdue),
        },
        "overdue": overdue,
        "due_soon": due_soon,
        "high_risk_overdue": high_risk_overdue,
        "message": "CAPA escalation summary generated successfully.",
    }


def build_capa_powerbi_rows(limit: int = 500) -> List[Dict]:
    """
    Builds flat CAPA rows for Power BI / analytics export.
    """
    init_capa_db()

    today = datetime.now(timezone.utc).date()
    rows = []

    for capa in list_capas(limit=limit):
        due_date_value = capa.get("due_date")
        days_to_due = None
        is_overdue = False

        if due_date_value:
            try:
                due_date = datetime.fromisoformat(str(due_date_value)).date()
                days_to_due = (due_date - today).days
                is_overdue = days_to_due < 0 and capa.get("status") not in {"closed", "cancelled"}
            except ValueError:
                try:
                    due_date = datetime.strptime(str(due_date_value), "%Y-%m-%d").date()
                    days_to_due = (due_date - today).days
                    is_overdue = days_to_due < 0 and capa.get("status") not in {"closed", "cancelled"}
                except ValueError:
                    days_to_due = None
                    is_overdue = False

        risk_level = capa.get("risk_level") or ""
        status = capa.get("status") or ""

        rows.append(
            {
                "capa_id": capa.get("id"),
                "title": capa.get("title"),
                "source": capa.get("source"),
                "risk_level": risk_level,
                "status": status,
                "owner": capa.get("owner"),
                "due_date": capa.get("due_date"),
                "created_at": capa.get("created_at"),
                "updated_at": capa.get("updated_at"),
                "days_to_due": days_to_due,
                "is_overdue": "true" if is_overdue else "false",
                "is_high_risk": "true" if risk_level in {"high", "critical"} else "false",
                "is_open": "true" if status not in {"closed", "cancelled"} else "false",
                "corrective_action": capa.get("corrective_action"),
                "preventive_action": capa.get("preventive_action"),
                "description": capa.get("description"),
            }
        )

    return rows

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


init_capa_db()
