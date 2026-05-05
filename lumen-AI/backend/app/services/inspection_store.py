import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "lumenai_inspections.db"
DB_PATH = Path(os.getenv("LUMENAI_INSPECTION_DB", str(DEFAULT_DB_PATH)))


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_inspection_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS inspections (
                inspection_id TEXT PRIMARY KEY,
                event_id TEXT,
                tenant_id TEXT,
                tenant_name TEXT,
                facility TEXT,
                department TEXT,
                instrument_name TEXT,
                instrument_category TEXT,
                vendor TEXT,
                tray_name TEXT,
                finding_type TEXT,
                finding_detail TEXT,
                evidence_url TEXT,
                inspector TEXT,
                classification TEXT,
                risk_level TEXT,
                recommended_routing TEXT,
                recommended_containment TEXT,
                capa_required INTEGER,
                vendor_escalation_recommended INTEGER,
                ip_review_recommended INTEGER,
                capa_id TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                audit_trail TEXT,
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


def row_to_inspection(row) -> Optional[Dict]:
    if not row:
        return None

    payload = {}
    try:
        if row["payload_json"]:
            payload = json.loads(row["payload_json"])
    except Exception:
        payload = {}

    record = {
        **payload,
        "inspection_id": row["inspection_id"],
        "event_id": row["event_id"],
        "tenant_id": row["tenant_id"],
        "tenant_name": row["tenant_name"],
        "facility": row["facility"],
        "department": row["department"],
        "instrument_name": row["instrument_name"],
        "instrument_category": row["instrument_category"],
        "vendor": row["vendor"],
        "tray_name": row["tray_name"],
        "finding_type": row["finding_type"],
        "finding_detail": row["finding_detail"],
        "evidence_url": row["evidence_url"],
        "inspector": row["inspector"],
        "classification": row["classification"],
        "risk_level": row["risk_level"],
        "recommended_routing": row["recommended_routing"],
        "recommended_containment": row["recommended_containment"],
        "capa_required": bool(row["capa_required"]),
        "vendor_escalation_recommended": bool(row["vendor_escalation_recommended"]),
        "ip_review_recommended": bool(row["ip_review_recommended"]),
        "capa_id": row["capa_id"] or "",
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "audit_trail": deserialize_json(row["audit_trail"]),
    }

    return record


def save_inspection(record: Dict) -> Dict:
    init_inspection_db()

    payload_json = json.dumps(record, ensure_ascii=False)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO inspections (
                inspection_id, event_id, tenant_id, tenant_name, facility,
                department, instrument_name, instrument_category, vendor,
                tray_name, finding_type, finding_detail, evidence_url, inspector,
                classification, risk_level, recommended_routing,
                recommended_containment, capa_required,
                vendor_escalation_recommended, ip_review_recommended,
                capa_id, status, created_at, updated_at, audit_trail, payload_json
            )
            VALUES (
                :inspection_id, :event_id, :tenant_id, :tenant_name, :facility,
                :department, :instrument_name, :instrument_category, :vendor,
                :tray_name, :finding_type, :finding_detail, :evidence_url, :inspector,
                :classification, :risk_level, :recommended_routing,
                :recommended_containment, :capa_required,
                :vendor_escalation_recommended, :ip_review_recommended,
                :capa_id, :status, :created_at, :updated_at, :audit_trail, :payload_json
            )
            ON CONFLICT(inspection_id) DO UPDATE SET
                event_id = excluded.event_id,
                tenant_id = excluded.tenant_id,
                tenant_name = excluded.tenant_name,
                facility = excluded.facility,
                department = excluded.department,
                instrument_name = excluded.instrument_name,
                instrument_category = excluded.instrument_category,
                vendor = excluded.vendor,
                tray_name = excluded.tray_name,
                finding_type = excluded.finding_type,
                finding_detail = excluded.finding_detail,
                evidence_url = excluded.evidence_url,
                inspector = excluded.inspector,
                classification = excluded.classification,
                risk_level = excluded.risk_level,
                recommended_routing = excluded.recommended_routing,
                recommended_containment = excluded.recommended_containment,
                capa_required = excluded.capa_required,
                vendor_escalation_recommended = excluded.vendor_escalation_recommended,
                ip_review_recommended = excluded.ip_review_recommended,
                capa_id = excluded.capa_id,
                status = excluded.status,
                updated_at = excluded.updated_at,
                audit_trail = excluded.audit_trail,
                payload_json = excluded.payload_json
            """,
            {
                **record,
                "capa_required": 1 if record.get("capa_required") else 0,
                "vendor_escalation_recommended": 1 if record.get("vendor_escalation_recommended") else 0,
                "ip_review_recommended": 1 if record.get("ip_review_recommended") else 0,
                "audit_trail": serialize_json(record.get("audit_trail")),
                "payload_json": payload_json,
            },
        )
        connection.commit()

    return record


def get_inspection(inspection_id: str) -> Optional[Dict]:
    init_inspection_db()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM inspections WHERE inspection_id = ?",
            (inspection_id,),
        ).fetchone()

    return row_to_inspection(row)


def list_inspections(
    facility: Optional[str] = None,
    vendor: Optional[str] = None,
    risk_level: Optional[str] = None,
    capa_required: Optional[bool] = None,
) -> List[Dict]:
    init_inspection_db()

    query = "SELECT * FROM inspections WHERE 1=1"
    params = []

    if facility:
        query += " AND facility = ?"
        params.append(facility)

    if vendor:
        query += " AND vendor = ?"
        params.append(vendor)

    if risk_level:
        query += " AND risk_level = ?"
        params.append(risk_level)

    if capa_required is not None:
        query += " AND capa_required = ?"
        params.append(1 if capa_required else 0)

    query += " ORDER BY created_at DESC"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [row_to_inspection(row) for row in rows]
