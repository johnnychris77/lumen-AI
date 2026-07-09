"""v3.1 — Project Atlas, Section 9: Executive Reports.

The first formally audience-typed report system in this codebase — every
other report generator (`board_reporting.py`, `benchmark_engine.
generate_board_report`, `portfolio_briefings.py`) uses a single fixed
shape or a free-text `audience`/`role` string with no validated set.
Reuses the export patterns already established rather than adding a new
library: CSV/XLSX via `csv`/`openpyxl` (`board_reporting.py`'s exact
pattern), PDF via `reportlab`'s low-level canvas (`app/reports/pdf_report.py`'s
pattern), all rendered to an in-memory buffer rather than a temp file.
"""
from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timezone
from io import BytesIO, StringIO

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models.atlas_enterprise import AUDIENCE_HOSPITAL_SUMMARY, AUDIENCE_MARKET_DIRECTOR, DISCLAIMER, REPORT_AUDIENCES, REPORT_CADENCES, ExecutiveReport
from app.services import atlas_benchmarking_service, atlas_dashboard_service, atlas_watchlist_service


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _period_label(cadence: str) -> str:
    now = datetime.now(timezone.utc)
    if cadence == "yearly" or cadence == "annual":
        return f"{now.year}"
    if cadence == "quarterly":
        return f"{now.year}-Q{(now.month - 1) // 3 + 1}"
    return f"{now.year}-{now.month:02d}"


def _build_summary(db: Session, system_id: str, audience: str, *, market_id: str = "", facility_id: str = "") -> dict:
    dashboard = atlas_dashboard_service.enterprise_dashboard(db, system_id)
    watchlist = atlas_watchlist_service.list_active_watchlist(db, system_id)
    benchmark = atlas_benchmarking_service.cross_facility_benchmark(db, system_id)

    if audience == AUDIENCE_MARKET_DIRECTOR and market_id:
        dashboard["facility_comparison"] = [f for f in dashboard["facility_comparison"] if f.get("market_id") == market_id]
        benchmark["facilities"] = [f for f in benchmark["facilities"] if f.get("market_id") == market_id]

    if audience == AUDIENCE_HOSPITAL_SUMMARY and facility_id:
        facility_snapshot = next((f for f in dashboard["facility_comparison"] if f["facility_id"] == facility_id), None)
        facility_benchmark = next((f for f in benchmark["facilities"] if f["facility_id"] == facility_id), None)
        return {
            "audience": audience, "facility_id": facility_id,
            "facility_intelligence": facility_snapshot, "facility_benchmark": facility_benchmark,
        }

    return {
        "audience": audience,
        "enterprise_quality_score": dashboard["enterprise_quality_score"],
        "enterprise_risk_score": dashboard["enterprise_risk_score"],
        "inspection_volume": dashboard["inspection_volume"],
        "pass_rate_pct": dashboard["pass_rate_pct"],
        "coverage_quality_pct": dashboard["coverage_quality_pct"],
        "supervisor_agreement_rate": dashboard["supervisor_agreement_rate"],
        "top_watchlist_entries": watchlist[:10],
        "facility_comparison": dashboard["facility_comparison"],
        "facility_benchmarks": benchmark["facilities"],
    }


def generate_executive_report(db: Session, system_id: str, *, audience: str, cadence: str, market_id: str = "", facility_id: str = "", generated_by: str = "system") -> dict:
    if audience not in REPORT_AUDIENCES:
        raise ValueError(f"audience must be one of {REPORT_AUDIENCES}")
    if cadence not in REPORT_CADENCES:
        raise ValueError(f"cadence must be one of {REPORT_CADENCES}")

    summary = _build_summary(db, system_id, audience, market_id=market_id, facility_id=facility_id)
    period_label = _period_label(cadence)

    row = ExecutiveReport(
        system_id=system_id, report_ref=f"ER-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}",
        audience=audience, cadence=cadence, period_label=period_label,
        title=f"{audience.replace('_', ' ').title()} {cadence.title()} Report — {period_label}",
        summary_json=json.dumps(summary, default=str), generated_by=generated_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _row_to_dict(row)
    result["summary"] = summary
    return result


def get_report(db: Session, system_id: str, report_id: int) -> dict | None:
    row = db.query(ExecutiveReport).filter(ExecutiveReport.id == report_id, ExecutiveReport.system_id == system_id).first()
    if row is None:
        return None
    result = _row_to_dict(row)
    result["summary"] = json.loads(row.summary_json)
    return result


def list_reports(db: Session, system_id: str, *, audience: str = "") -> list[dict]:
    q = db.query(ExecutiveReport).filter(ExecutiveReport.system_id == system_id)
    if audience:
        q = q.filter(ExecutiveReport.audience == audience)
    rows = q.order_by(ExecutiveReport.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def build_report_csv_bytes(report: dict) -> bytes:
    output = StringIO()
    facilities = report["summary"].get("facility_comparison") or []
    if facilities:
        writer = csv.DictWriter(output, fieldnames=list(facilities[0].keys()))
        writer.writeheader()
        writer.writerows(facilities)
    return output.getvalue().encode("utf-8")


def build_report_xlsx_bytes(report: dict) -> bytes:
    wb = Workbook()
    summary = report["summary"]

    ws = wb.active
    ws.title = "Summary"
    ws.append(["metric", "value"])
    for k, v in summary.items():
        if isinstance(v, (list, dict)):
            continue
        ws.append([k, v])

    ws2 = wb.create_sheet("Facility Comparison")
    facilities = summary.get("facility_comparison") or []
    if facilities:
        headers = list(facilities[0].keys())
        ws2.append(headers)
        for item in facilities:
            ws2.append([item.get(h, "") for h in headers])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue()


def build_report_pdf_bytes(report: dict) -> bytes:
    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, report["title"])
    y -= 26
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Period: {report['period_label']} · Audience: {report['audience']}")
    y -= 24

    summary = report["summary"]
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Enterprise Summary")
    y -= 18
    c.setFont("Helvetica", 10)
    for key in ("enterprise_quality_score", "enterprise_risk_score", "inspection_volume", "pass_rate_pct", "coverage_quality_pct", "supervisor_agreement_rate"):
        if key in summary:
            c.drawString(60, y, f"{key.replace('_', ' ').title()}: {summary[key]}")
            y -= 14

    y -= 10
    c.setFont("Helvetica-Oblique", 8)
    for line in [DISCLAIMER[i:i + 100] for i in range(0, len(DISCLAIMER), 100)]:
        c.drawString(50, y, line)
        y -= 10

    c.showPage()
    c.save()
    bio.seek(0)
    return bio.getvalue()
