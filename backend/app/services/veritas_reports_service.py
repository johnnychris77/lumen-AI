"""Project Veritas, Section 19: Evidence Assurance Reports.

Reuses this codebase's existing report-generation libraries (reportlab for
PDF -- see `report_pdf.py`/`vanguard_board_reporting_service.py` -- and
openpyxl for Excel) rather than introducing a new export dependency. CSV
uses the stdlib, the same pattern as `audit_export_service.py`.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import BytesIO, StringIO

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.services.veritas_data_quality_service import data_quality_summary
from app.services.veritas_evidence_agent_service import to_dict as assessment_to_dict
from app.services.veritas_training_dataset_service import list_dataset_entries
from app.services.veritas_workspace_service import workspace_summary


def _flatten(content: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for key, value in content.items():
        if isinstance(value, (dict, list)):
            rows.append((key, json.dumps(value, default=str)[:300]))
        else:
            rows.append((key, str(value)))
    return rows


def build_report_pdf_bytes(title: str, content: dict) -> bytes:
    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title)
    y -= 22
    c.setFont("Helvetica", 9)
    c.drawString(50, y, f"Generated: {datetime.now(timezone.utc).isoformat()}")
    y -= 20

    c.setFont("Helvetica", 9)
    for key, value in _flatten(content):
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, f"{key}: {value}"[:110])
        y -= 13

    c.showPage()
    c.save()
    return bio.getvalue()


def build_report_csv_bytes(content: dict) -> bytes:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Key", "Value"])
    for key, value in _flatten(content):
        writer.writerow([key, value])
    return buf.getvalue().encode("utf-8")


def build_report_xlsx_bytes(title: str, content: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31] or "Report"
    ws.append(["Key", "Value"])
    for key, value in _flatten(content):
        ws.append([key, value])
    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def inspection_evidence_package(db: Session, tenant_id: str, assessment) -> dict:
    return {"title": "Inspection Evidence Package", "content": assessment_to_dict(assessment)}


def baseline_governance_report(db: Session, tenant_id: str) -> dict:
    return {"title": "Baseline Governance Report", "content": workspace_summary(db, tenant_id)}


def evidence_readiness_report(db: Session, tenant_id: str) -> dict:
    return {"title": "Evidence Readiness Report", "content": workspace_summary(db, tenant_id)}


def training_dataset_assurance_report(db: Session, tenant_id: str) -> dict:
    entries = list_dataset_entries(db, tenant_id)
    statuses: dict[str, int] = {}
    for e in entries:
        statuses[e["dataset_status"]] = statuses.get(e["dataset_status"], 0) + 1
    return {"title": "Training Dataset Assurance Report", "content": {"total_entries": len(entries), "by_status": statuses}}


def provenance_audit_report(db: Session, tenant_id: str) -> dict:
    from app.services.veritas_provenance_service import list_provenance
    entries = list_provenance(db, tenant_id)
    return {"title": "Provenance Audit Report", "content": {"total_records": len(entries), "records": entries[:50]}}


def baseline_review_aging_report(db: Session, tenant_id: str) -> dict:
    from app.services.veritas_watchlist_service import baseline_review_overdue
    return {"title": "Baseline Review Aging Report", "content": {"overdue": baseline_review_overdue(db, tenant_id)}}


def data_quality_trend_report(db: Session, tenant_id: str) -> dict:
    return {"title": "Data Quality Trend Report", "content": data_quality_summary(db, tenant_id)}


REPORTS = {
    "baseline_governance": baseline_governance_report,
    "evidence_readiness": evidence_readiness_report,
    "training_dataset_assurance": training_dataset_assurance_report,
    "provenance_audit": provenance_audit_report,
    "baseline_review_aging": baseline_review_aging_report,
    "data_quality_trend": data_quality_trend_report,
}


def build_named_report(db: Session, tenant_id: str, name: str) -> dict | None:
    fn = REPORTS.get(name)
    return fn(db, tenant_id) if fn else None
