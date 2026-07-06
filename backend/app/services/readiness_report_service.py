"""v1.6 — Exportable Clinical Readiness Report (Deliverable 10).

Builds the JSON payload (for the timeline export and API consumers) and a
printable PDF, reusing the existing clinical_report_pdf.py's style/table
helpers rather than re-implementing PDF layout.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.clinical_report_pdf import _kv_table, _styles
from app.services.disposition_evidence_service import build_evidence_panel
from app.services.readiness_engine import get_primary_finding_type
from app.services.readiness_timeline_service import build_timeline
from app.services.risk_stratification_service import stratify_risk


def build_readiness_report_payload(db, tenant_id: str, insp) -> dict:
    """The full JSON report: instrument details, evidence, coverage, findings,
    clinical reasoning, disposition recommendation, supervisor approval, and
    audit metadata."""
    evidence = build_evidence_panel(db, tenant_id, insp)
    timeline = build_timeline(db, tenant_id, insp)
    risk = stratify_risk(insp, primary_finding_type=get_primary_finding_type(db, insp))

    return {
        "instrument": {
            "instrument_type": insp.instrument_type,
            "instrument_identity": evidence["instrument_identity"],
            "facility_name": insp.facility_name or insp.site_name,
            "department": insp.department,
        },
        "evidence": evidence,
        "timeline": timeline,
        "risk_stratification": risk,
        "audit_metadata": {
            "inspection_id": insp.id,
            "tenant_id": tenant_id,
            "technician": insp.technician,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def build_readiness_report_pdf(db, tenant_id: str, insp) -> bytes:
    payload = build_readiness_report_payload(db, tenant_id, insp)
    evidence = payload["evidence"]
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        title=f"LumenAI Clinical Readiness Report — Inspection {insp.id}",
    )
    story: list[Any] = []

    story.append(Paragraph("LumenAI — Clinical Service Readiness Report", ss["Title"]))
    story.append(Paragraph("Pre-sterilization decision support (pilot — advisory, human review required)", ss["Small"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#94a3b8")))
    story.append(Spacer(1, 6))

    story.append(Paragraph(f"<b>Recommended Disposition: {evidence['recommended_disposition']}</b>", ss["Heading2"]))
    story.append(Paragraph(evidence["clinical_rationale"], ss["Normal"]))

    story.append(Paragraph("Instrument Details", ss["H"]))
    story.append(_kv_table([
        ("Instrument", payload["instrument"]["instrument_type"]),
        ("Identity", payload["instrument"]["instrument_identity"]),
        ("Facility", payload["instrument"]["facility_name"] or "—"),
        ("Department", payload["instrument"]["department"] or "—"),
    ]))

    story.append(Paragraph("Inspection Evidence", ss["H"]))
    story.append(_kv_table([
        ("Inspection Coverage", f"{evidence['inspection_coverage_pct']}%" if evidence["inspection_coverage_pct"] is not None else "Not assessed"),
        ("Findings", evidence["detected_issue"] or "None"),
        ("Severity", evidence["severity"] or "—"),
        ("Baseline Used", evidence["baseline_used"] or "—"),
        ("Supervisor Status", evidence["supervisor_status"]),
        ("Readiness Score", str(evidence["readiness_score"]) if evidence["readiness_score"] is not None else "—"),
        ("Readiness Status", evidence["readiness_status"]),
    ]))

    story.append(Paragraph("Risk Stratification", ss["H"]))
    story.append(_kv_table([
        ("Risk Tier", payload["risk_stratification"]["risk_tier"]),
        ("Contributing Factors", "; ".join(payload["risk_stratification"]["reasons"]) or "None"),
    ]))

    story.append(Paragraph("Readiness Timeline", ss["H"]))
    timeline_rows = [["Step", "Completed", "Timestamp"]]
    for step in payload["timeline"]["steps"]:
        timeline_rows.append([
            step["step"], "Yes" if step["completed"] else "No", step.get("timestamp") or "—",
        ])
    t = Table(timeline_rows, colWidths=[2.2 * inch, 1.0 * inch, 2.8 * inch])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t)

    story.append(Paragraph("Audit Metadata", ss["H"]))
    story.append(_kv_table([
        ("Inspection ID", str(payload["audit_metadata"]["inspection_id"])),
        ("Technician", payload["audit_metadata"]["technician"] or "—"),
        ("Generated", payload["audit_metadata"]["generated_at"]),
    ]))

    story.append(Spacer(1, 18))
    sig = Table([
        ["Technician: ______________________", "Supervisor: ______________________"],
        ["Date: __________________________", "Date: __________________________"],
    ], colWidths=[3.0 * inch, 3.0 * inch])
    sig.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 10)]))
    story.append(sig)

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Pilot advisory output. Not validated for production diagnostic accuracy; no FDA clearance is claimed. "
        "Qualified human review is required before any disposition.",
        ss["Small"],
    ))

    doc.build(story)
    return buf.getvalue()
