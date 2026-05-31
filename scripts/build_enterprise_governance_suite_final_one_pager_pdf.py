from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "docs/investor/ENTERPRISE_GOVERNANCE_SUITE_FINAL_EXECUTIVE_ONE_PAGER_v1.pdf"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.55 * inch,
    leftMargin=0.55 * inch,
    topMargin=0.55 * inch,
    bottomMargin=0.5 * inch,
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleStyle",
    parent=styles["Title"],
    alignment=TA_CENTER,
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    textColor=colors.HexColor("#0f172a"),
    spaceAfter=6,
)

subtitle_style = ParagraphStyle(
    "SubtitleStyle",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    textColor=colors.HexColor("#166534"),
    spaceAfter=10,
)

section_style = ParagraphStyle(
    "SectionStyle",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    textColor=colors.HexColor("#1e293b"),
    spaceBefore=8,
    spaceAfter=5,
)

body_style = ParagraphStyle(
    "BodyStyle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8.6,
    leading=11.3,
    textColor=colors.HexColor("#334155"),
    spaceAfter=5,
)

small_style = ParagraphStyle(
    "SmallStyle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.3,
    leading=9.5,
    textColor=colors.HexColor("#475569"),
)

small_bold_style = ParagraphStyle(
    "SmallBoldStyle",
    parent=small_style,
    fontName="Helvetica-Bold",
    textColor=colors.HexColor("#0f172a"),
)

link_style = ParagraphStyle(
    "LinkStyle",
    parent=small_style,
    fontName="Helvetica",
    fontSize=6.8,
    leading=8.4,
    textColor=colors.HexColor("#0369a1"),
)

story = []

story.append(Paragraph("LumenAI Enterprise Governance Suite v1.0.0", title_style))
story.append(Paragraph("Final Executive One-Pager", subtitle_style))

status = (
    "Released - Production Validated - Evidence Backed - Portfolio Linked - "
    "Power BI Ready - GitHub Tagged - GitHub Released - Executive Governance Ready"
)
story.append(Paragraph(status, subtitle_style))

story.append(Paragraph("Executive Summary", section_style))
story.append(
    Paragraph(
        "LumenAI Enterprise Governance Suite v1.0.0 is a production-validated healthcare quality "
        "governance platform designed for sterile processing, surgical services, vendor accountability, "
        "audit readiness, CAPA oversight, and executive quality governance. The suite connects audit "
        "signals, CAPA governance, vendor governance, Power BI exports, public portfolio evidence, and "
        "an executive dashboard into one integrated leadership-facing governance layer.",
        body_style,
    )
)

story.append(Paragraph("Released Product Modules", section_style))

modules_data = [
    [
        Paragraph("<b>Module</b>", small_bold_style),
        Paragraph("<b>Capability</b>", small_bold_style),
        Paragraph("<b>Public Portfolio</b>", small_bold_style),
    ],
    [
        Paragraph("Enterprise Audit Command Center", small_bold_style),
        Paragraph("Audit readiness, audit health, high-value audit events, evidence exports.", small_style),
        Paragraph("lumen-ai-1.onrender.com/portfolio/audit-command-center", link_style),
    ],
    [
        Paragraph("CAPA Governance Scorecard", small_bold_style),
        Paragraph("CAPA workflow, status updates, overdue escalation, scorecard, Power BI export.", small_style),
        Paragraph("lumen-ai-1.onrender.com/portfolio/capa-workflow", link_style),
    ],
    [
        Paragraph("Vendor Governance Module", small_bold_style),
        Paragraph("Vendor quality signals, vendor risk, CAPA linkage, Vendor Power BI export.", small_style),
        Paragraph("lumen-ai-1.onrender.com/portfolio/vendor-governance", link_style),
    ],
    [
        Paragraph("Executive Governance Dashboard", small_bold_style),
        Paragraph("Unified executive view across Audit, CAPA, Vendor Governance, Power BI readiness.", small_style),
        Paragraph("lumen-ai-1.onrender.com/portfolio/executive-governance-dashboard", link_style),
    ],
]

modules_table = Table(modules_data, colWidths=[1.55 * inch, 3.05 * inch, 2.15 * inch])
modules_table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#14532d")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
)
story.append(modules_table)

story.append(Spacer(1, 6))

story.append(Paragraph("Final Suite Portfolio", section_style))
portfolio_data = [
    ["Final Suite Evidence Page", "https://lumen-ai-1.onrender.com/portfolio/enterprise-governance-suite-final"],
    ["Governance Hub", "https://lumen-ai-1.onrender.com/portfolio/governance-hub"],
    ["Governance Summary", "https://lumen-ai-1.onrender.com/portfolio/governance-summary"],
]
portfolio_table = Table(
    [[Paragraph(f"<b>{a}</b>", small_bold_style), Paragraph(b, link_style)] for a, b in portfolio_data],
    colWidths=[2.25 * inch, 4.5 * inch],
)
portfolio_table.setStyle(
    TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
)
story.append(portfolio_table)

story.append(Spacer(1, 4))

story.append(Paragraph("Power BI Export Layer", section_style))
powerbi_data = [
    [
        Paragraph("<b>Export</b>", small_bold_style),
        Paragraph("<b>Production URL</b>", small_bold_style),
        Paragraph("<b>Business Use</b>", small_bold_style),
    ],
    [
        Paragraph("CAPA Power BI CSV", small_bold_style),
        Paragraph("lumen-ai-53u4.onrender.com/api/capa/powerbi-csv?limit=500", link_style),
        Paragraph("CAPA status, overdue monitoring, high-risk reporting, closure tracking, executive scorecards.", small_style),
    ],
    [
        Paragraph("Vendor Governance Power BI CSV", small_bold_style),
        Paragraph("lumen-ai-53u4.onrender.com/api/enterprise/vendor-governance/powerbi-csv?limit=500", link_style),
        Paragraph("Vendor trend analytics, high-risk vendor reporting, CAPA linkage reporting, executive scorecards.", small_style),
    ],
]
powerbi_table = Table(powerbi_data, colWidths=[1.6 * inch, 2.7 * inch, 2.45 * inch])
powerbi_table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0c4a6e")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
)
story.append(powerbi_table)

story.append(Spacer(1, 4))

story.append(Paragraph("Release and Evidence Discipline", section_style))
story.append(
    Paragraph(
        "GitHub release tags, GitHub releases, release locks, final production validation packet, "
        "final public evidence page, master evidence index, investor portfolio packet, and executive one-pager are complete.",
        body_style,
    )
)

story.append(Paragraph("Release Tags", section_style))
story.append(
    Paragraph(
        "enterprise-governance-suite-v1.0.0 | enterprise-governance-suite-final-v1.0.0 | "
        "capa-governance-scorecard-v1.0.0 | vendor-governance-v1.0.0 | "
        "executive-governance-dashboard-v1.0.0",
        small_style,
    )
)

story.append(Paragraph("Strategic Positioning", section_style))
story.append(
    Paragraph(
        "LumenAI has expanded from a sterile processing inspection concept into an enterprise quality "
        "governance platform. The platform connects Audit Governance -> CAPA Governance -> Vendor Governance "
        "-> Power BI Analytics -> Portfolio Evidence -> Executive Interpretation.",
        body_style,
    )
)

story.append(Paragraph("Final Executive Statement", section_style))
story.append(
    Paragraph(
        "The LumenAI Enterprise Governance Suite v1.0.0 is released, production validated, evidence backed, "
        "portfolio linked, Power BI ready, GitHub tagged, GitHub released, and executive governance demonstration ready. "
        "This release represents a complete investor-ready milestone for LumenAI's enterprise healthcare quality governance platform.",
        body_style,
    )
)

doc.build(story)

print(f"✅ Created {OUTPUT}")
