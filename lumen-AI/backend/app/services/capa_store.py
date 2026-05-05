import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "lumenai_capa.db"
DB_PATH = Path(os.getenv("LUMENAI_CAPA_DB", str(DEFAULT_DB_PATH)))


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_capa_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS capas (
                capa_id TEXT PRIMARY KEY,
                tenant_id TEXT,
                tenant_name TEXT,
                event_id TEXT,
                inspection_id TEXT,
                facility TEXT,
                instrument_name TEXT,
                instrument_category TEXT,
                vendor TEXT,
                finding_type TEXT,
                risk_level TEXT,
                capa_type TEXT,
                status TEXT,
                owner TEXT,
                due_date TEXT,
                problem_statement TEXT,
                containment_action TEXT,
                root_cause TEXT,
                corrective_action TEXT,
                preventive_action TEXT,
                closure_summary TEXT,
                evidence_links TEXT,
                audit_trail TEXT,
                created_at TEXT,
                updated_at TEXT,
                payload_json TEXT
            )
            """
        )
        connection.commit()


def serialize_json(value):
    return json.dumps(value or [], ensure_ascii=False)


def deserialize_json(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []


def row_to_capa(row) -> Dict:
    if row is None:
        return {}

    payload = {}
    try:
        payload_raw = row["payload_json"]
        if payload_raw:
            payload = json.loads(payload_raw)
    except Exception:
        payload = {}

    def safe_get(key, default=None):
        try:
            value = row[key]
            return default if value is None else value
        except Exception:
            return default

    capa = {
        **payload,
        "capa_id": safe_get("capa_id"),
        "tenant_id": safe_get("tenant_id"),
        "tenant_name": safe_get("tenant_name"),
        "event_id": safe_get("event_id"),
        "inspection_id": safe_get("inspection_id"),
        "facility": safe_get("facility"),
        "instrument_name": safe_get("instrument_name"),
        "instrument_category": safe_get("instrument_category"),
        "vendor": safe_get("vendor"),
        "finding_type": safe_get("finding_type"),
        "risk_level": safe_get("risk_level"),
        "capa_type": safe_get("capa_type"),
        "status": safe_get("status"),
        "owner": safe_get("owner"),
        "due_date": safe_get("due_date"),
        "problem_statement": safe_get("problem_statement"),
        "containment_action": safe_get("containment_action"),
        "root_cause": safe_get("root_cause", ""),
        "corrective_action": safe_get("corrective_action", ""),
        "preventive_action": safe_get("preventive_action", ""),
        "closure_summary": safe_get("closure_summary", ""),
        "evidence_links": deserialize_json(safe_get("evidence_links", "[]")),
        "audit_trail": deserialize_json(safe_get("audit_trail", "[]")),
        "created_at": safe_get("created_at"),
        "updated_at": safe_get("updated_at"),
    }

    return capa


def save_capa(capa: Dict) -> Dict:
    init_capa_db()

    payload_json = json.dumps(capa, ensure_ascii=False)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO capas (
                capa_id,
                tenant_id,
                tenant_name,
                event_id,
                inspection_id,
                facility,
                instrument_name,
                instrument_category,
                vendor,
                finding_type,
                risk_level,
                capa_type,
                status,
                owner,
                due_date,
                problem_statement,
                containment_action,
                root_cause,
                corrective_action,
                preventive_action,
                closure_summary,
                evidence_links,
                audit_trail,
                created_at,
                updated_at,
                payload_json
            )
            VALUES (
                :capa_id,
                :tenant_id,
                :tenant_name,
                :event_id,
                :inspection_id,
                :facility,
                :instrument_name,
                :instrument_category,
                :vendor,
                :finding_type,
                :risk_level,
                :capa_type,
                :status,
                :owner,
                :due_date,
                :problem_statement,
                :containment_action,
                :root_cause,
                :corrective_action,
                :preventive_action,
                :closure_summary,
                :evidence_links,
                :audit_trail,
                :created_at,
                :updated_at,
                :payload_json
            )
            ON CONFLICT(capa_id) DO UPDATE SET
                tenant_id = excluded.tenant_id,
                tenant_name = excluded.tenant_name,
                event_id = excluded.event_id,
                inspection_id = excluded.inspection_id,
                facility = excluded.facility,
                instrument_name = excluded.instrument_name,
                instrument_category = excluded.instrument_category,
                vendor = excluded.vendor,
                finding_type = excluded.finding_type,
                risk_level = excluded.risk_level,
                capa_type = excluded.capa_type,
                status = excluded.status,
                owner = excluded.owner,
                due_date = excluded.due_date,
                problem_statement = excluded.problem_statement,
                containment_action = excluded.containment_action,
                root_cause = excluded.root_cause,
                corrective_action = excluded.corrective_action,
                preventive_action = excluded.preventive_action,
                closure_summary = excluded.closure_summary,
                evidence_links = excluded.evidence_links,
                audit_trail = excluded.audit_trail,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            {
                "capa_id": capa.get("capa_id"),
                "tenant_id": capa.get("tenant_id"),
                "tenant_name": capa.get("tenant_name"),
                "event_id": capa.get("event_id"),
                "inspection_id": capa.get("inspection_id"),
                "facility": capa.get("facility"),
                "instrument_name": capa.get("instrument_name"),
                "instrument_category": capa.get("instrument_category"),
                "vendor": capa.get("vendor"),
                "finding_type": capa.get("finding_type"),
                "risk_level": capa.get("risk_level"),
                "capa_type": capa.get("capa_type"),
                "status": capa.get("status"),
                "owner": capa.get("owner"),
                "due_date": capa.get("due_date"),
                "problem_statement": capa.get("problem_statement"),
                "containment_action": capa.get("containment_action"),
                "root_cause": capa.get("root_cause", ""),
                "corrective_action": capa.get("corrective_action", ""),
                "preventive_action": capa.get("preventive_action", ""),
                "closure_summary": capa.get("closure_summary", ""),
                "evidence_links": serialize_json(capa.get("evidence_links")),
                "audit_trail": serialize_json(capa.get("audit_trail")),
                "created_at": capa.get("created_at"),
                "updated_at": capa.get("updated_at"),
                "payload_json": payload_json,
            },
        )
        connection.commit()

    return capa


def get_capa(capa_id: str) -> Optional[Dict]:
    init_capa_db()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM capas WHERE capa_id = ?",
            (capa_id,),
        ).fetchone()

    if not row:
        return None

    return row_to_capa(row)


def list_capas(
    status: Optional[str] = None,
    facility: Optional[str] = None,
    vendor: Optional[str] = None,
) -> List[Dict]:
    init_capa_db()

    query = "SELECT * FROM capas WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if facility:
        query += " AND facility = ?"
        params.append(facility)

    if vendor:
        query += " AND vendor = ?"
        params.append(vendor)

    query += " ORDER BY created_at DESC"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [row_to_capa(row) for row in rows]


def delete_all_capas_for_dev():
    init_capa_db()
    with get_connection() as connection:
        connection.execute("DELETE FROM capas")
        connection.commit()
