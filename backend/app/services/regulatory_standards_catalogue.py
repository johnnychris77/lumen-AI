"""P8: Built-in regulatory standards catalogue and finding→clause mappings.

Standards covered:
- Joint Commission (EC, IC, LD standards relevant to SPD/sterile processing)
- AAMI ST79 (comprehensive guide to steam sterilization)
- FDA 21 CFR Part 820 (Quality System Regulation)
- CMS Conditions of Participation
- ISO 17664 (sterilization of health-care products)
- v4.7 Project Apollo additions: AAMI ST91 (flexible/semi-rigid endoscope
  reprocessing — distinct body code `aami_st91` from ST79's `aami`), AORN
  (perioperative practice standards), DNV (accreditation body, alternative
  to Joint Commission).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class StandardDef:
    code: str
    body: str
    title: str
    description: str
    category: str
    applicability: str = "SPD"


@dataclass
class MappingDef:
    finding_category: str
    standard_code: str
    severity_threshold: str
    citation_text: str
    remediation_guidance: str
    auto_capa_required: bool = False


STANDARDS: list[StandardDef] = [
    # Joint Commission — Environment of Care / Infection Control
    StandardDef("JC-IC.02.02.01", "joint_commission",
        "Reduces the risk of infections associated with medical equipment, devices, and supplies",
        "The hospital reduces the risk of infections associated with medical equipment, devices, and supplies by cleaning and performing low-level disinfection, intermediate-level disinfection, or sterilization based on the Spaulding classification system.",
        "infection_control", "SPD,OR"),
    StandardDef("JC-IC.02.02.03", "joint_commission",
        "Sterilization performed in accordance with law and regulation and manufacturer instructions",
        "The hospital performs sterilization activities in accordance with law and regulation and manufacturer instructions for use.",
        "sterilization", "SPD"),
    StandardDef("JC-EC.02.04.03", "joint_commission",
        "Medical equipment maintenance and testing",
        "The hospital inspects, tests, and maintains medical equipment. Includes requirements for documenting equipment maintenance and tracking findings.",
        "equipment_maintenance", "SPD,Biomedical"),
    StandardDef("JC-LD.04.01.01", "joint_commission",
        "Leaders establish a culture of safety and quality improvement",
        "Leaders develop and implement plans to identify and manage risks to the safety and quality of care.",
        "leadership", "Enterprise"),
    StandardDef("JC-MM.01.01.03", "joint_commission",
        "Medication management — tracking high-alert medications",
        "The hospital identifies and manages high-alert medications. (Referenced for instrument trays containing medication delivery devices.)",
        "medication_management", "SPD,Pharmacy"),

    # AAMI ST79
    StandardDef("AAMI-ST79-4", "aami",
        "ST79 Section 4: Receiving, inspection, and decontamination",
        "Instruments shall be inspected for cleanliness, damage, and functionality prior to sterilization. Blood, bone, and tissue residue indicate decontamination failure.",
        "decontamination", "SPD"),
    StandardDef("AAMI-ST79-5", "aami",
        "ST79 Section 5: Preparation and packaging",
        "Instruments with visible defects (cracks, corrosion, insulation damage) shall not be sterilized and packaged until repaired or replaced.",
        "preparation", "SPD"),
    StandardDef("AAMI-ST79-8", "aami",
        "ST79 Section 8: Sterilization process monitoring",
        "Chemical, biological, and mechanical indicators must be used to verify sterilization efficacy. Failed indicators require quarantine and re-processing.",
        "sterilization_monitoring", "SPD"),
    StandardDef("AAMI-ST79-10", "aami",
        "ST79 Section 10: Event-related sterility",
        "Sterility is event-related. Instruments showing contamination at point of use indicate a sterile packaging or storage failure.",
        "sterility_maintenance", "SPD,OR"),

    # FDA
    StandardDef("FDA-21CFR820.70", "fda",
        "21 CFR 820.70 — Production and Process Controls",
        "Manufacturers shall develop, conduct, control, and monitor production processes to ensure a device conforms to its specifications.",
        "manufacturing_controls", "SPD,Quality"),
    StandardDef("FDA-21CFR820.80", "fda",
        "21 CFR 820.80 — Receiving, In-Process, and Finished Device Acceptance",
        "Incoming devices shall be inspected, tested, or otherwise verified as conforming to specified requirements. Records shall be maintained.",
        "acceptance_activities", "SPD,Quality"),
    StandardDef("FDA-MDR-803", "fda",
        "21 CFR 803 — Medical Device Reporting (MDR)",
        "Device failures that could cause or contribute to serious injury must be reported to FDA within 30 days.",
        "adverse_event_reporting", "Quality,Risk"),

    # CMS
    StandardDef("CMS-482.42", "cms",
        "CMS CoP §482.42 — Infection Control",
        "The hospital must provide a sanitary environment to avoid sources and transmission of infections and communicable diseases. The infection control officer must develop a system to identify, report, investigate, and control infections.",
        "infection_control", "SPD,Nursing,Quality"),
    StandardDef("CMS-482.13", "cms",
        "CMS CoP §482.13 — Patient Rights",
        "Patients have the right to receive care in a safe setting. Instrument contamination events may constitute a patient rights violation.",
        "patient_rights", "Enterprise"),

    # ISO
    StandardDef("ISO-17664-1", "iso",
        "ISO 17664-1: Sterilization — IFU for medical devices",
        "Manufacturers shall provide instructions for use (IFU) that describe validated decontamination and sterilization processes. Deviations from IFU are non-conformances.",
        "ifu_compliance", "SPD,Quality"),

    # v4.7 Project Apollo — AAMI ST91 (flexible/semi-rigid endoscope
    # reprocessing). Distinct body code from ST79's "aami".
    StandardDef("AAMI-ST91-6", "aami_st91",
        "ST91 Section 6: Point-of-use treatment and transport of flexible endoscopes",
        "Flexible endoscopes shall receive point-of-use treatment immediately after the procedure and be transported in a manner that prevents drying of soil.",
        "endoscope_reprocessing", "SPD,GI/Endo"),
    StandardDef("AAMI-ST91-9", "aami_st91",
        "ST91 Section 9: Manual cleaning and leak testing of flexible endoscopes",
        "Flexible endoscopes shall undergo leak testing before manual cleaning; a failed leak test indicates internal damage and requires removal from service.",
        "endoscope_reprocessing", "SPD,GI/Endo"),

    # v4.7 Project Apollo — AORN perioperative practice standards.
    StandardDef("AORN-INSTR-01", "aorn",
        "AORN Guideline for Care and Cleaning of Surgical Instruments",
        "Perioperative team members should collaborate with SPD on point-of-use treatment, transport, and instrument tray assembly to reduce the risk of instrument damage and contamination.",
        "instrument_handling", "OR,SPD"),
    StandardDef("AORN-COUNT-01", "aorn",
        "AORN Guideline for Sharps Safety and Surgical Counts",
        "Instrument, sponge, and sharps counts should be performed and documented per facility policy to prevent retained surgical items.",
        "surgical_counts", "OR"),

    # v4.7 Project Apollo — DNV accreditation standards (alternative to
    # Joint Commission).
    StandardDef("DNV-QM.3", "dnv",
        "DNV NIAHO Quality Management System Standard QM.3",
        "The organization shall establish a quality management system that identifies, monitors, and corrects nonconformances, including those affecting instrument reprocessing.",
        "quality_management", "Enterprise,Quality"),
    StandardDef("DNV-IC.4", "dnv",
        "DNV NIAHO Infection Control Standard IC.4",
        "The organization shall have a documented process for high-level disinfection and sterilization of reusable medical devices consistent with manufacturer IFU.",
        "infection_control", "SPD,Quality"),
]


FINDING_MAPPINGS: list[MappingDef] = [
    # Blood residue
    MappingDef("blood", "JC-IC.02.02.01", "any",
        "Blood residue detected post-decontamination constitutes a Spaulding classification failure — critical items must be sterile.",
        "Re-decontaminate immediately. Review enzymatic pre-soak protocol. Audit IFU compliance. CAPA required if recurrent.",
        auto_capa_required=True),
    MappingDef("blood", "AAMI-ST79-4", "any",
        "Visible blood residue indicates decontamination failure per AAMI ST79 Section 4.",
        "Instrument must not proceed to sterilization. Manual inspection and re-decontamination required."),
    MappingDef("blood", "CMS-482.42", "high",
        "Blood contamination post-decontamination represents an infection control failure under CMS CoP §482.42.",
        "Notify infection control officer. Document in infection control log. Initiate root cause analysis.",
        auto_capa_required=True),

    # Bone debris
    MappingDef("bone", "AAMI-ST79-4", "any",
        "Bone debris post-decontamination indicates inadequate manual cleaning or insufficient enzymatic action.",
        "Extend enzymatic soak per IFU. Add ultrasonic cleaning step for orthopedic instruments."),
    MappingDef("bone", "JC-IC.02.02.01", "high",
        "Bone debris on critical instruments represents a Spaulding classification violation.",
        "CAPA required. Review decontamination SOP for orthopedic instrument sets.",
        auto_capa_required=True),

    # Tissue residue
    MappingDef("tissue", "AAMI-ST79-4", "any",
        "Soft tissue residue indicates incomplete decontamination per AAMI ST79 Section 4.",
        "Re-decontaminate. Evaluate cleaning chemistry concentration and temperature compliance."),
    MappingDef("tissue", "JC-IC.02.02.01", "high",
        "Tissue contamination on sterile field instruments violates Joint Commission infection control standard.",
        "Immediate quarantine of instrument set. Notify OR and infection control.",
        auto_capa_required=True),

    # Crack / structural damage
    MappingDef("crack", "AAMI-ST79-5", "any",
        "Cracked instruments must not be sterilized. Cracks harbor biofilm and prevent sterilant penetration.",
        "Remove from service. Tag for repair evaluation. Document in instrument lifecycle record."),
    MappingDef("crack", "JC-EC.02.04.03", "any",
        "Structural defects constitute a maintenance finding under JC EC.02.04.03.",
        "Submit to biomedical engineering for assessment. Do not return to service without inspection clearance."),

    # Corrosion
    MappingDef("corrosion", "AAMI-ST79-5", "any",
        "Corrosion compromises instrument integrity and may harbor microorganisms per AAMI ST79 Section 5.",
        "Assess severity. Minor surface pitting: monitor and escalate. Active corrosion: remove from service."),
    MappingDef("corrosion", "ISO-17664-1", "high",
        "Corrosion may indicate IFU non-compliance (e.g. incorrect cleaning chemistry, improper drying).",
        "Review IFU. Audit chemistry concentrations and drying cycle compliance."),

    # Insulation damage
    MappingDef("insulation", "AAMI-ST79-5", "any",
        "Insulation breaches on electrosurgical instruments are a patient safety hazard.",
        "Perform dielectric leakage test. Instrument must pass 100% before return to service."),
    MappingDef("insulation", "JC-EC.02.04.03", "critical",
        "Insulation failure on electrosurgical instruments requires immediate maintenance action.",
        "Pull from service. Notify biomedical engineering and OR. Document in equipment maintenance log.",
        auto_capa_required=True),

    # Residue / bioburden
    MappingDef("residue", "AAMI-ST79-4", "any",
        "Residue indicates incomplete decontamination.",
        "Inspect and re-decontaminate. Review cleaning agent efficacy."),
    MappingDef("residue", "FDA-21CFR820.80", "high",
        "Residue at point-of-use inspection indicates acceptance activity failure.",
        "Investigate root cause. Update incoming inspection procedures if systemic."),

    # Baseline deviation
    MappingDef("baseline mismatch", "AAMI-ST79-5", "any",
        "Baseline comparison failure indicates dimensional or cosmetic deviation from original specification.",
        "Compare against OEM baseline. Escalate to manufacturer if deviation exceeds tolerance."),
    MappingDef("baseline mismatch", "ISO-17664-1", "high",
        "Deviation from baseline may indicate IFU non-compliance or product degradation.",
        "Initiate supplier corrective action request (SCAR) if manufacturer defect suspected."),
]


def get_standards() -> list[StandardDef]:
    return STANDARDS


def get_mappings_for_finding(finding_category: str) -> list[MappingDef]:
    cat = finding_category.lower()
    return [m for m in FINDING_MAPPINGS if m.finding_category in cat or cat in m.finding_category]


def get_all_mappings() -> list[MappingDef]:
    return FINDING_MAPPINGS
