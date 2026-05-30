from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

OUTPUT = "docs/investor/LumenAI_Enterprise_Governance_Suite_Executive_One_Pager_v1.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=letter,
    rightMargin=0.55 * inch,
    leftMargin=0.55 * inch,
    topMargin=0.45 * inch,
    bottomMargin=0.45 * inch,
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleStyle",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=colors.HexColor("#0f172a"),
    alignment=TA_CENTER,
    spaceAfter=8,
)

subtitle_style = ParagraphStyle(
    "SubtitleStyle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=12,
    textColor=colors.HexColor("#334155"),
    alignment=TA_CENTER,
    spaceAfter=10,
)

section_style = ParagraphStyle(
    "SectionStyle",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11.5,
    leading=14,
    textColor=colors.HexColor("#047857"),
    spaceBefore=7,
    spaceAfter=4,
)

body_style = ParagraphStyle(
    "BodyStyle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8.6,
    leading=11.2,
    textColor=colors.HexColor("#1e293b"),
    alignment=TA_LEFT,
)

small_style = ParagraphStyle(
    "SmallStyle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9.5,
    textColor=colors.HexColor("#334155"),
)

bold_style = ParagraphStyle(
    "BoldStyle",
    parent=body_style,
    fontName="Helvetica-Bold",
)

link_style = ParagraphStyle(
    "LinkStyle",
    parent=small_style,
    textColor=colors.HexColor("#2563eb"),
)

story = []

story.append(Paragraph("LumenAI Enterprise Governance Suite", title_style))
story.append(
    Paragraph(
        "Executive one-pager | Production validated quality intelligence for audit readiness, CAPA execution, and governance visibility",
        subtitle_style,
    )
)

metrics = [
    ["Suite Status", "READY", "Production validated"],
    ["Validated Modules", "3", "Audit, CAPA, Integration"],
    ["Audit Checks", "18/18", "0 failed / 0 warnings"],
    ["Audit Events", "696", "196 high-value events"],
]

metric_table_data = []
for label, value, helper in metrics:
    metric_table_data.append([
        Paragraph(f"<b>{label}</b><br/><font size='14'>{value}</font><br/><font size='7'>{helper}</font>", small_style)
    ])

metric_table = Table(
    [metric_table_data],
    colWidths=[1.75 * inch, 1.75 * inch, 1.75 * inch, 1.75 * inch],
)
metric_table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#a7f3d0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#a7f3d0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 7),
        ]
    )
)
story.append(metric_table)
story.append(Spacer(1, 6))

story.append(Paragraph("Problem", section_style))
story.append(
    Paragraph(
        "Healthcare quality and sterile processing teams often manage audit findings, quality signals, evidence packages, and corrective actions across fragmented systems. This makes executive visibility, audit readiness, CAPA follow-through, and Power BI-ready reporting difficult to sustain.",
        body_style,
    )
)

story.append(Paragraph("Solution", section_style))
story.append(
    Paragraph(
        "LumenAI connects frontline quality evidence to enterprise governance. The validated pathway is: <b>Audit Signal - High-Value Event - CAPA Trigger - Owner Assigned - Corrective Action - Preventive Action - Governance Summary.</b>",
        body_style,
    )
)

story.append(Paragraph("Validated Product Modules", section_style))

modules = [
    [
        Paragraph("<b>Audit Command Center</b>", body_style),
        Paragraph("Centralized audit visibility, health validation, high-value event tracking, PDF/CSV/Power BI exports, data dictionary, toolkit ZIP, and portfolio evidence page.", small_style),
    ],
    [
        Paragraph("<b>CAPA Workflow</b>", body_style),
        Paragraph("Converts audit signals into structured corrective and preventive action records with owner, due date, risk level, status, corrective action, and preventive action.", small_style),
    ],
    [
        Paragraph("<b>Audit-to-CAPA Integration</b>", body_style),
        Paragraph("Governance bridge connecting audit visibility to accountable CAPA execution and executive oversight.", small_style),
    ],
]

module_table = Table(modules, colWidths=[1.65 * inch, 5.35 * inch])
module_table.setStyle(
    TableStyle(
        [
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]
    )
)
story.append(module_table)

story.append(Paragraph("Production Proof Points", section_style))
proof = [
    "Audit Command Center: healthy, 18/18 checks passed, 0 failed, 0 warnings.",
    "Audit activity: 696 audit events and 196 high-value events.",
    "CAPA Workflow: health endpoint validated, CAPA creation from audit signal validated, CAPA list/governance summary validated.",
    "Portfolio assets: Audit evidence page, CAPA evidence page, Governance Hub, Governance Summary page, Evidence Index, Release Notes, and Demo Readiness Locks.",
]
story.append(Paragraph("<br/>".join([f"- {item}" for item in proof]), body_style))

story.append(Paragraph("Business Value", section_style))
business_value = [
    ["Audit readiness", "Quality governance visibility", "Corrective action follow-through"],
    ["Preventive action tracking", "Executive reporting", "Power BI-ready evidence"],
    ["Vendor accountability", "High-value event monitoring", "Operational risk visibility"],
]
bv_table = Table([[Paragraph(x, small_style) for x in row] for row in business_value], colWidths=[2.33 * inch] * 3)
bv_table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]
    )
)
story.append(bv_table)

story.append(Paragraph("Differentiation", section_style))
story.append(
    Paragraph(
        "LumenAI is differentiated by connecting sterile processing quality evidence to enterprise governance workflows. It does not stop at inspection or reporting; it creates a traceable path from signal detection to CAPA execution and leadership-ready evidence packaging.",
        body_style,
    )
)

story.append(Paragraph("Demo Links", section_style))
links = [
    ("Main App", "https://lumen-ai-1.onrender.com"),
    ("Governance Hub", "https://lumen-ai-1.onrender.com/portfolio/governance-hub"),
    ("Governance Summary", "https://lumen-ai-1.onrender.com/portfolio/governance-summary"),
    ("Audit Evidence", "https://lumen-ai-1.onrender.com/portfolio/audit-command-center"),
    ("CAPA Evidence", "https://lumen-ai-1.onrender.com/portfolio/capa-workflow"),
    ("Audit-to-CAPA Summary", "https://lumen-ai-53u4.onrender.com/api/enterprise/audit-to-capa/summary"),
]
link_rows = [[Paragraph(f"<b>{name}</b>", small_style), Paragraph(url, link_style)] for name, url in links]
link_table = Table(link_rows, colWidths=[1.8 * inch, 5.2 * inch])
link_table.setStyle(
    TableStyle(
        [
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )
)
story.append(link_table)

story.append(Paragraph("Roadmap", section_style))
story.append(
    Paragraph(
        "Persist CAPA records in database; add CAPA status updates, overdue escalation, Power BI CAPA export, governance scorecard, vendor-specific CAPA analytics, Infection Prevention linkage, executive PDF summary, and role-based access.",
        body_style,
    )
)

story.append(Spacer(1, 6))
story.append(
    Paragraph(
        "<b>Final statement:</b> LumenAI Enterprise Governance Suite v1.0.0 is production validated, evidence backed, portfolio ready, demo ready, stakeholder ready, and investor ready.",
        body_style,
    )
)

doc.build(story)
print(f"Created {OUTPUT}")
