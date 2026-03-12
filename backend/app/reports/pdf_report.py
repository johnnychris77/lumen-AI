from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


REPORT_DIR = Path("/app/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def generate_report(inspection) -> str:
    output_path = REPORT_DIR / f"inspection_{inspection.id}.pdf"

    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "LumenAI Inspection Report")

    y -= 40
    c.setFont("Helvetica", 11)
    rows = [
        ("Inspection ID", inspection.id),
        ("File Name", inspection.file_name),
        ("Status", inspection.status),
        ("Stain Detected", inspection.stain_detected),
        ("Confidence", inspection.confidence),
        ("Material Type", inspection.material_type),
        ("Model Name", inspection.model_name),
        ("Model Version", inspection.model_version),
        ("Inference Timestamp", inspection.inference_timestamp),
        ("Created At", inspection.created_at),
    ]

    for label, value in rows:
        c.drawString(50, y, f"{label}: {value}")
        y -= 22

    c.save()
    return str(output_path)
