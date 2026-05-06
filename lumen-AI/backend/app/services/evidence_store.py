import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
EVIDENCE_DIR = DATA_DIR / "evidence"
DEFAULT_DB_PATH = DATA_DIR / "lumenai_evidence.db"
DB_PATH = Path(os.getenv("LUMENAI_EVIDENCE_DB", str(DEFAULT_DB_PATH)))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_evidence_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                original_filename TEXT,
                stored_filename TEXT,
                file_path TEXT,
                file_url TEXT,
                mime_type TEXT,
                evidence_type TEXT,
                facility TEXT,
                instrument_name TEXT,
                vendor TEXT,
                finding_category TEXT,
                linked_visual_review_id TEXT,
                linked_inspection_id TEXT,
                linked_capa_id TEXT,
                ai_review_status TEXT,
                human_review_status TEXT,
                created_at TEXT,
                updated_at TEXT,
                metadata_json TEXT
            )
            """
        )
        connection.commit()


def row_to_evidence(row) -> Optional[Dict]:
    if not row:
        return None

    metadata = {}
    try:
        metadata = json.loads(row["metadata_json"] or "{}")
    except Exception:
        metadata = {}

    return {
        "evidence_id": row["evidence_id"],
        "original_filename": row["original_filename"],
        "stored_filename": row["stored_filename"],
        "file_path": row["file_path"],
        "file_url": row["file_url"],
        "mime_type": row["mime_type"],
        "evidence_type": row["evidence_type"],
        "facility": row["facility"],
        "instrument_name": row["instrument_name"],
        "vendor": row["vendor"],
        "finding_category": row["finding_category"],
        "linked_visual_review_id": row["linked_visual_review_id"] or "",
        "linked_inspection_id": row["linked_inspection_id"] or "",
        "linked_capa_id": row["linked_capa_id"] or "",
        "ai_review_status": row["ai_review_status"],
        "human_review_status": row["human_review_status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "metadata": metadata,
    }


def save_evidence(record: Dict) -> Dict:
    init_evidence_db()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO evidence (
                evidence_id, original_filename, stored_filename, file_path, file_url,
                mime_type, evidence_type, facility, instrument_name, vendor,
                finding_category, linked_visual_review_id, linked_inspection_id,
                linked_capa_id, ai_review_status, human_review_status,
                created_at, updated_at, metadata_json
            )
            VALUES (
                :evidence_id, :original_filename, :stored_filename, :file_path, :file_url,
                :mime_type, :evidence_type, :facility, :instrument_name, :vendor,
                :finding_category, :linked_visual_review_id, :linked_inspection_id,
                :linked_capa_id, :ai_review_status, :human_review_status,
                :created_at, :updated_at, :metadata_json
            )
            ON CONFLICT(evidence_id) DO UPDATE SET
                original_filename = excluded.original_filename,
                stored_filename = excluded.stored_filename,
                file_path = excluded.file_path,
                file_url = excluded.file_url,
                mime_type = excluded.mime_type,
                evidence_type = excluded.evidence_type,
                facility = excluded.facility,
                instrument_name = excluded.instrument_name,
                vendor = excluded.vendor,
                finding_category = excluded.finding_category,
                linked_visual_review_id = excluded.linked_visual_review_id,
                linked_inspection_id = excluded.linked_inspection_id,
                linked_capa_id = excluded.linked_capa_id,
                ai_review_status = excluded.ai_review_status,
                human_review_status = excluded.human_review_status,
                updated_at = excluded.updated_at,
                metadata_json = excluded.metadata_json
            """,
            {
                **record,
                "metadata_json": json.dumps(record.get("metadata", {}), ensure_ascii=False),
            },
        )
        connection.commit()

    return record


def get_evidence(evidence_id: str) -> Optional[Dict]:
    init_evidence_db()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()

    return row_to_evidence(row)


def list_evidence() -> List[Dict]:
    init_evidence_db()

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM evidence ORDER BY created_at DESC"
        ).fetchall()

    return [row_to_evidence(row) for row in rows]


def create_evidence_record(
    file,
    evidence_type: str = "borescope_image",
    facility: str = "",
    instrument_name: str = "",
    vendor: str = "",
    finding_category: str = "",
) -> Dict:
    init_evidence_db()

    now = utc_now_iso()
    evidence_id = f"EVID-{uuid4()}"

    original_filename = file.filename or "uploaded-evidence"
    suffix = Path(original_filename).suffix or ".bin"
    stored_filename = f"{evidence_id}{suffix}"
    destination = EVIDENCE_DIR / stored_filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "evidence_id": evidence_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_path": str(destination),
        "file_url": f"/api/evidence/{evidence_id}/file",
        "mime_type": file.content_type or "application/octet-stream",
        "evidence_type": evidence_type,
        "facility": facility,
        "instrument_name": instrument_name,
        "vendor": vendor,
        "finding_category": finding_category,
        "linked_visual_review_id": "",
        "linked_inspection_id": "",
        "linked_capa_id": "",
        "ai_review_status": "Not Reviewed",
        "human_review_status": "Pending Review",
        "created_at": now,
        "updated_at": now,
        "metadata": {
            "upload_source": "LumenAI dashboard",
            "ai_ready": True,
        },
    }


def link_evidence(evidence_id: str, field: str, value: str) -> Dict:
    record = get_evidence(evidence_id)

    if not record:
        raise ValueError("Evidence not found.")

    record[field] = value
    record["updated_at"] = utc_now_iso()
    return save_evidence(record)
