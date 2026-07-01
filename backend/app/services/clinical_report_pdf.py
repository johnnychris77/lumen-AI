"""Phase 13.8 — Clinical Report Generator (printable PDF).

Renders an inspection's Explainable-AI Clinical Decision Support output as a
printable PDF for the quality record: decision, score breakdown, cleaning +
integrity assessments, clinical reasoning, recommendation, evidence, audit
trail, and signature lines.

Advisory pilot output — the report carries the pilot-model label and the
human-review requirement; no FDA/production-accuracy claims.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H", parent=ss["Heading2"], spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#0f172a")))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=8, textColor=colors.HexColor("#64748b")))
    return ss


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    t = Table([[k, v] for k, v in rows], colWidths=[2.1 * inch, 4.0 * inch])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _findings_table(items: list[dict], integrity: bool) -> Table:
    header = ["Finding", "Detected", "Prob", "Severity", "Confidence", "SPD Risk"]
    data = [header]
    for it in items:
        data.append([
            it["label"],
            "yes" if it.get("detected") else "no",
            f"{it['probability_pct']}%",
            it["severity"],
            f"{it['confidence_pct']}%",
            it.get("spd_risk_impact", "Clear"),
        ])
    t = Table(data, colWidths=[1.6 * inch, 0.7 * inch, 0.6 * inch, 1.4 * inch, 0.9 * inch, 0.9 * inch])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


_RESULT_COLOR = {
    "PASS": "#059669", "MONITOR": "#d97706",
    "SUPERVISOR REVIEW": "#ea580c", "REMOVE FROM SERVICE": "#dc2626",
}


def build_clinical_report_pdf(row: Any, analysis: dict) -> bytes:
    """Return the PDF bytes for an inspection + its analysis payload."""
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        title=f"LumenAI Clinical Report — Inspection {getattr(row, 'id', '')}",
    )
    cd = analysis.get("clinical_decision", {})
    summary = cd.get("summary", {})
    story: list[Any] = []

    story.append(Paragraph("LumenAI — Clinical Inspection Report", ss["Title"]))
    story.append(Paragraph("Explainable AI Clinical Decision Support (pilot — advisory, human review required)", ss["Small"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#94a3b8")))
    story.append(Spacer(1, 6))

    result = cd.get("overall_result", "SUPERVISOR REVIEW")
    story.append(Paragraph(
        f'<font color="{_RESULT_COLOR.get(result, "#334155")}"><b>Overall Result: {result}</b></font>',
        ss["Heading2"],
    ))

    # Identity / context
    story.append(Paragraph("Inspection", ss["H"]))
    story.append(_kv_table([
        ("Facility", getattr(row, "facility_name", None) or getattr(row, "site_name", "") or "—"),
        ("Inspection ID", str(getattr(row, "id", "—"))),
        ("Instrument", getattr(row, "instrument_type", "—")),
        ("Barcode / UDI", getattr(row, "instrument_barcode", None) or getattr(row, "instrument_udi", None) or "—"),
        ("Baseline Source", str(summary.get("baseline_source") or "—")),
        ("Inspection Date", (getattr(row, "created_at", None) or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")),
    ]))

    # Decision summary
    story.append(Paragraph("Clinical Decision Summary", ss["H"]))
    story.append(_kv_table([
        ("Inspection Score", f"{summary.get('inspection_score', '—')} / 100"),
        ("Cleaning Assessment", str(summary.get("cleaning_assessment") or "—")),
        ("Integrity Assessment", str(summary.get("integrity_assessment") or "—")),
        ("Overall Risk", str(summary.get("overall_risk") or "—")),
        ("Confidence", f"{summary.get('confidence') or '—'} ({summary.get('confidence_pct', 0)}%)"),
    ]))

    # Cleaning + integrity tables
    cleaning = cd.get("cleaning", {})
    if cleaning.get("items"):
        story.append(Paragraph(f"Cleaning Assessment — {cleaning.get('overall_status', '—')}", ss["H"]))
        story.append(_findings_table(cleaning["items"], integrity=False))
    integrity = cd.get("integrity", {})
    if integrity.get("items"):
        story.append(Paragraph(f"Instrument Integrity — {integrity.get('overall_status', '—')}", ss["H"]))
        story.append(_findings_table(integrity["items"], integrity=True))

    # Reasoning
    story.append(Paragraph("Clinical Reasoning", ss["H"]))
    for line in cd.get("clinical_reasoning", []):
        story.append(Paragraph(f"• {line}", ss["Normal"]))

    # Recommendation
    rec = cd.get("recommendation", {})
    story.append(Paragraph("Recommendation", ss["H"]))
    story.append(Paragraph(f"<b>{rec.get('result', result)}</b> — {rec.get('action', '')}", ss["Normal"]))

    # Evidence
    ev = cd.get("evidence", {})
    story.append(Paragraph("Evidence Used", ss["H"]))
    story.append(_kv_table([
        ("Baseline", str(ev.get("baseline_comparison_label") or ev.get("baseline_source") or "—")),
        ("Baseline Match", f"{ev.get('baseline_match_pct', '—')}%"),
        ("Highest Risk Drivers", ", ".join(ev.get("highest_risk_drivers", []) or ["—"])),
        ("Confidence", str(ev.get("confidence") or "—")),
    ]))
    story.append(Paragraph(ev.get("image_evidence_note", ""), ss["Small"]))

    # Audit
    audit = cd.get("audit", {})
    story.append(Paragraph("Audit Trail", ss["H"]))
    story.append(_kv_table([
        ("AI Model", f"{audit.get('model_label', '')} ({audit.get('model_version', '')})"),
        ("Baseline Version", str(audit.get("baseline_version") or "—")),
        ("Recommendation", str(audit.get("recommendation") or "—")),
        ("Human Review Required", "Yes" if audit.get("human_review_required", True) else "No"),
        ("Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
    ]))

    # Signatures
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
