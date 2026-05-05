import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "lumenai_visual_inspections.db"
DB_PATH = Path(os.getenv("LUMENAI_VISUAL_INSPECTION_DB", str(DEFAULT_DB_PATH)))


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_visual_inspection_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS visual_inspection_reviews (
                review_id TEXT PRIMARY KEY,
                inspection_id TEXT,
                event_id TEXT,
                facility TEXT,
                department TEXT,
                instrument_name TEXT,
                instrument_category TEXT,
                vendor TEXT,
                tray_name TEXT,
                evidence_url TEXT,
                suspected_debris_type TEXT,
                quality_issue_type TEXT,
                severity_score INTEGER,
                confidence_score INTEGER,
                recommended_disposition TEXT,
                reclean_required INTEGER,
                second_inspection_required INTEGER,
                quarantine_required INTEGER,
                ip_review_recommended INTEGER,
                vendor_escalation_recommended INTEGER,
                capa_recommended INTEGER,
                technician_decision TEXT,
                override_reason TEXT,
                review_status TEXT,
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


def row_to_review(row) -> Optional[Dict]:
    if not row:
        return None

    payload = {}
    try:
        if row["payload_json"]:
            payload = json.loads(row["payload_json"])
    except Exception:
        payload = {}

    review = {
        **payload,
        "review_id": row["review_id"],
        "inspection_id": row["inspection_id"],
        "event_id": row["event_id"],
        "facility": row["facility"],
        "department": row["department"],
        "instrument_name": row["instrument_name"],
        "instrument_category": row["instrument_category"],
        "vendor": row["vendor"],
        "tray_name": row["tray_name"],
        "evidence_url": row["evidence_url"],
        "suspected_debris_type": row["suspected_debris_type"],
        "quality_issue_type": row["quality_issue_type"],
        "severity_score": row["severity_score"],
        "confidence_score": row["confidence_score"],
        "recommended_disposition": row["recommended_disposition"],
        "reclean_required": bool(row["reclean_required"]),
        "second_inspection_required": bool(row["second_inspection_required"]),
        "quarantine_required": bool(row["quarantine_required"]),
        "ip_review_recommended": bool(row["ip_review_recommended"]),
        "vendor_escalation_recommended": bool(row["vendor_escalation_recommended"]),
        "capa_recommended": bool(row["capa_recommended"]),
        "technician_decision": row["technician_decision"] or "",
        "override_reason": row["override_reason"] or "",
        "review_status": row["review_status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "audit_trail": deserialize_json(row["audit_trail"]),
    }

    return review


def save_visual_review(review: Dict) -> Dict:
    init_visual_inspection_db()
    payload_json = json.dumps(review, ensure_ascii=False)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO visual_inspection_reviews (
                review_id, inspection_id, event_id, facility, department,
                instrument_name, instrument_category, vendor, tray_name,
                evidence_url, suspected_debris_type, quality_issue_type,
                severity_score, confidence_score, recommended_disposition,
                reclean_required, second_inspection_required, quarantine_required,
                ip_review_recommended, vendor_escalation_recommended,
                capa_recommended, technician_decision, override_reason,
                review_status, created_at, updated_at, audit_trail, payload_json
            )
            VALUES (
                :review_id, :inspection_id, :event_id, :facility, :department,
                :instrument_name, :instrument_category, :vendor, :tray_name,
                :evidence_url, :suspected_debris_type, :quality_issue_type,
                :severity_score, :confidence_score, :recommended_disposition,
                :reclean_required, :second_inspection_required, :quarantine_required,
                :ip_review_recommended, :vendor_escalation_recommended,
                :capa_recommended, :technician_decision, :override_reason,
                :review_status, :created_at, :updated_at, :audit_trail, :payload_json
            )
            ON CONFLICT(review_id) DO UPDATE SET
                inspection_id = excluded.inspection_id,
                event_id = excluded.event_id,
                facility = excluded.facility,
                department = excluded.department,
                instrument_name = excluded.instrument_name,
                instrument_category = excluded.instrument_category,
                vendor = excluded.vendor,
                tray_name = excluded.tray_name,
                evidence_url = excluded.evidence_url,
                suspected_debris_type = excluded.suspected_debris_type,
                quality_issue_type = excluded.quality_issue_type,
                severity_score = excluded.severity_score,
                confidence_score = excluded.confidence_score,
                recommended_disposition = excluded.recommended_disposition,
                reclean_required = excluded.reclean_required,
                second_inspection_required = excluded.second_inspection_required,
                quarantine_required = excluded.quarantine_required,
                ip_review_recommended = excluded.ip_review_recommended,
                vendor_escalation_recommended = excluded.vendor_escalation_recommended,
                capa_recommended = excluded.capa_recommended,
                technician_decision = excluded.technician_decision,
                override_reason = excluded.override_reason,
                review_status = excluded.review_status,
                updated_at = excluded.updated_at,
                audit_trail = excluded.audit_trail,
                payload_json = excluded.payload_json
            """,
            {
                **review,
                "reclean_required": 1 if review.get("reclean_required") else 0,
                "second_inspection_required": 1 if review.get("second_inspection_required") else 0,
                "quarantine_required": 1 if review.get("quarantine_required") else 0,
                "ip_review_recommended": 1 if review.get("ip_review_recommended") else 0,
                "vendor_escalation_recommended": 1 if review.get("vendor_escalation_recommended") else 0,
                "capa_recommended": 1 if review.get("capa_recommended") else 0,
                "audit_trail": serialize_json(review.get("audit_trail")),
                "payload_json": payload_json,
            },
        )
        connection.commit()

    return review


def get_visual_review(review_id: str) -> Optional[Dict]:
    init_visual_inspection_db()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM visual_inspection_reviews WHERE review_id = ?",
            (review_id,),
        ).fetchone()

    return row_to_review(row)


def list_visual_reviews() -> List[Dict]:
    init_visual_inspection_db()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM visual_inspection_reviews ORDER BY created_at DESC"
        ).fetchall()

    return [row_to_review(row) for row in rows]
