"""Phase 23 §8 — Clinical Readiness Certificate.

A printable Pre-Sterilization Clinical Readiness Certificate. This is
explicitly NOT a sterilization certificate — it documents the clinical
inspection that happens before packaging and sterilization, consistent
with the pre-sterilization boundary
(docs/architecture/pre-sterilization-boundary.md).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.cios.decision_ledger import list_decisions
from app.cios.governance import governance_snapshot


def build_certificate(db, inspection, tenant_id: str, cios_result: dict) -> dict:
    ctx = cios_result["clinical_context"]
    decisions = list_decisions(db, tenant_id, inspection.id)

    return {
        "certificate_type": "pre_sterilization_clinical_readiness_certificate",
        "not_a_sterilization_certificate": True,
        "disclaimer": (
            "This certificate documents the clinical inspection performed before packaging "
            "and sterilization. It is not a sterilization certificate, a biological indicator "
            "record, or a sterilizer performance validation of any kind."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inspection_id": inspection.id,
        "instrument": {
            "instrument_type": ctx["instrument_type"],
            "manufacturer": ctx["manufacturer"] or "not specified",
            "model": ctx["model"] or "not specified",
            "instrument_family": ctx["instrument_family"],
        },
        "inspection_date": inspection.created_at.isoformat() if inspection.created_at else None,
        "clinical_decision": cios_result["agent_result"]["recommendation_context"],
        "inspection_coverage": ctx["coverage"],
        "baseline_used": ctx["baseline"],
        "findings": ctx["findings"],
        "clinical_reasoning": ctx["knowledge_graph_links"]["reasoning_chain"],
        "recommendation": ctx["recommendation"],
        "supervisor_approval": ctx["supervisor_review"],
        "audit_ids": {
            "inspection_id": inspection.id,
            "decision_ledger_entry_ids": [d["id"] for d in decisions],
        },
        "governance_versions": governance_snapshot(),
        "digital_signature_placeholder": {
            "signed": False,
            "note": "Digital signature capture is not yet implemented — this is a structural placeholder for a future e-signature integration.",
        },
        "human_review_required": True,
    }


def render_certificate_pdf(certificate: dict) -> bytes:
    """Render the certificate to a simple, printable PDF."""
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=50)
    story = []

    story.append(Paragraph("Pre-Sterilization Clinical Readiness Certificate", styles["Title"]))
    story.append(Paragraph(certificate["disclaimer"], styles["Italic"]))
    story.append(Spacer(1, 12))

    instrument = certificate["instrument"]
    rows = [
        ["Inspection ID", str(certificate["inspection_id"])],
        ["Instrument", instrument["instrument_type"]],
        ["Manufacturer", instrument["manufacturer"]],
        ["Model", instrument["model"]],
        ["Instrument Family", instrument["instrument_family"]],
        ["Inspection Date", certificate["inspection_date"] or "—"],
        ["Recommendation", certificate["recommendation"].get("readiness_state", "—")],
    ]
    table = Table(rows, colWidths=[160, 320])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Clinical Reasoning", styles["Heading3"]))
    for step in certificate["clinical_reasoning"]:
        story.append(Paragraph(f"{step['node']}: {step['value']}", styles["Normal"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Governance Versions", styles["Heading3"]))
    for key, value in certificate["governance_versions"].items():
        story.append(Paragraph(f"{key}: {value}", styles["Normal"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph(
        f"Digital signature: {'signed' if certificate['digital_signature_placeholder']['signed'] else 'not signed — placeholder only'}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This is not a sterilization certificate. Human supervisor review is required before this "
        "instrument proceeds to packaging and sterilization.",
        styles["Italic"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
