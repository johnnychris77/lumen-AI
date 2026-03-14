import os
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

REPORT_DIR = Path("/app/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def generate_report(inspection) -> str:
    output_path = REPORT_DIR / f"inspection_{inspection.id}.pdf"

    org_name = os.getenv("LUMENAI_REPORT_ORG", "LumenAI")
    subtitle = os.getenv("LUMENAI_REPORT_SUBTITLE", "AI Surgical Instrument Inspection Report")
    website = os.getenv("LUMENAI_REPORT_WEBSITE", "www.lumenai.health")
    contact = os.getenv("LUMENAI_REPORT_CONTACT", "info@lumenai.health")
    segment = os.getenv("LUMENAI_REPORT_SEGMENT", "Healthcare SPD / Vendor QA")

    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, org_name)

    y -= 22
    c.setFont("Helvetica", 11)
    c.drawString(50, y, subtitle)

    y -= 16
    c.drawString(50, y, f"Segment: {segment}")
    y -= 16
    c.drawString(50, y, f"Website: {website}")
    y -= 16
    c.drawString(50, y, f"Contact: {contact}")

    y -= 30
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "Inspection Summary")

    y -= 24
    c.setFont("Helvetica", 11)
    rows = [
        ("Inspection ID", inspection.id),
        ("File Name", inspection.file_name),
        ("Status", inspection.status),
        ("Stain Detected", inspection.stain_detected),
        ("Confidence", inspection.confidence),
        ("Material Type", inspection.material_type),
        ("Instrument Type", inspection.instrument_type),
        ("Detected Issue", inspection.detected_issue),
        ("Inference Mode", inspection.inference_mode),
        ("Model Name", inspection.model_name),
        ("Model Version", inspection.model_version),
        ("Inference Timestamp", inspection.inference_timestamp),
        ("Created At", inspection.created_at),
    ]

    for label, value in rows:
        c.drawString(50, y, f"{label}: {value}")
        y -= 20

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Recommended Review")

    y -= 20
    c.setFont("Helvetica", 10)
    if str(inspection.detected_issue).lower() in {"debris", "stain", "corrosion"}:
        recommendation = "Escalate to manual QA review and reprocessing verification before reuse."
    else:
        recommendation = "No critical issue flagged by automated inspection. Continue standard QA workflow."

    c.drawString(50, y, recommendation)

    y -= 35
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(
        50,
        y,
        "This report supports operational review and does not replace validated clinical or manufacturer decision-making."
    )

    c.save()
    return str(output_path)
