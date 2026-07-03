"""Phase 14 — Clinical Mentor content engine.

Turns an inspection analysis into teaching-grade explanation: finding-specific
clinical interpretation, "why this matters", expanded next-action checklists,
summarized standards guidance (no copyrighted text), learning-mode education,
separated contamination vs integrity risk, and the AI Mentor synthesis.

All narrative is derived from the actual findings — no generic filler. Standards
references are paraphrased summaries of accepted sterile-processing practice, not
quotations of AAMI/AORN copyrighted material.
"""
from __future__ import annotations

from app.services.baseline_comparison_scoring_service import (
    CLEANING_KPIS,
    INTEGRITY_KPIS,
    KPI_LABELS,
    _STRUCTURAL_KPIS,
)

# ── Per-finding education (Phase 14.2 "Why this matters" + 14.5 Learning Mode) ─
# Concise, accurate SPD knowledge. Advisory/educational — not device-specific IFU.
FINDING_EDUCATION: dict[str, dict] = {
    "blood": {
        "why_it_matters": (
            "Visible blood indicates incomplete cleaning and represents retained "
            "organic contamination. Residual blood may interfere with sterilization "
            "effectiveness and requires reprocessing."
        ),
        "definition": "Retained red/brown organic residue from patient blood.",
        "typical_causes": "Insufficient point-of-use treatment, delayed cleaning, or inadequate lumen brushing.",
        "clinical_significance": "Organic soil can shield microorganisms from the sterilant, undermining sterility assurance.",
        "spd_response": "Return for complete cleaning and re-inspect before sterilization.",
        "supervisor_tips": "Check lumens, box locks, and serrations where blood commonly persists.",
    },
    "tissue": {
        "why_it_matters": (
            "Tissue or protein residue indicates incomplete cleaning. It can protect "
            "microorganisms during sterilization and must be removed by reprocessing."
        ),
        "definition": "Soft-tissue or protein residue adhering to the instrument surface or lumen.",
        "typical_causes": "Dried soil, missed manual cleaning steps, or ineffective enzymatic treatment.",
        "clinical_significance": "Protein soil is a recognized barrier to effective sterilization.",
        "spd_response": "Reprocess with attention to enzymatic soak and mechanical cleaning.",
        "supervisor_tips": "Verify enzymatic detergent contact time and water quality.",
    },
    "other_organic_residue": {
        "why_it_matters": (
            "Organic residue indicates cleaning was not fully effective and may harbor "
            "microorganisms; the instrument should be reprocessed."
        ),
        "definition": "Non-specific biological soil not otherwise classified.",
        "typical_causes": "Biofilm, dried bioburden, or detergent residue.",
        "clinical_significance": "Any retained organic soil compromises pre-sterilization cleaning assurance.",
        "spd_response": "Return for complete cleaning; consider biofilm-directed protocols.",
        "supervisor_tips": "Biofilm may require extended contact time or ultrasonic cleaning.",
    },
    "bone": {
        "why_it_matters": (
            "Bone or calcified debris is a hard organic residue that can lodge in "
            "cannulations and shield contamination; reprocessing is indicated."
        ),
        "definition": "Calcified fragment or bone dust, often in cannulated shafts.",
        "typical_causes": "Orthopedic procedures with inadequate channel flushing.",
        "clinical_significance": "Calcified debris can obstruct channels and protect soil.",
        "spd_response": "Flush and brush cannulations; reprocess and re-inspect.",
        "supervisor_tips": "Use correct-diameter brushes for cannulated instruments.",
    },
    "debris": {
        "why_it_matters": (
            "Debris or particulate indicates residual soil. It should be removed and "
            "the instrument re-inspected before release."
        ),
        "definition": "Non-specific particulate matter on the surface or in channels.",
        "typical_causes": "Lint, packaging fragments, brush bristles, or mineral deposits.",
        "clinical_significance": "Particulate can carry microorganisms and impede sterilant contact.",
        "spd_response": "Re-clean and inspect; identify and remove the particulate source.",
        "supervisor_tips": "Rule out lint from wipes and degraded brushes.",
    },
    "rust": {
        "why_it_matters": (
            "Rust may indicate corrosion of the instrument surface. Corrosion can damage "
            "protective finishes, create rough surfaces, and increase cleaning difficulty."
        ),
        "definition": "Iron-oxide staining or surface corrosion on stainless steel.",
        "typical_causes": "Moisture retention, chloride exposure, or damaged passivation layer.",
        "clinical_significance": "Rough corroded surfaces are harder to clean and can trap soil.",
        "spd_response": "Assess severity; light staining may be monitored, heavy rust needs evaluation.",
        "supervisor_tips": "Distinguish true rust from transferable stains (which wipe off).",
    },
    "corrosion": {
        "why_it_matters": (
            "Corrosion degrades the instrument surface and can create pits and rough "
            "areas that trap contamination and complicate cleaning."
        ),
        "definition": "Progressive surface degradation of the metal.",
        "typical_causes": "Chloride/detergent exposure, galvanic contact, or aging.",
        "clinical_significance": "Severe corrosion can compromise both cleaning and instrument function.",
        "spd_response": "Moderate: supervisor review; severe: remove from service for evaluation.",
        "supervisor_tips": "Check hinges and box locks where corrosion often begins.",
    },
    "discoloration": {
        "why_it_matters": (
            "Minor cosmetic discoloration alone does not necessarily indicate instrument "
            "failure. Distinguish cosmetic variation from corrosion-associated discoloration."
        ),
        "definition": "Color change from heat tint, detergent, or mineral staining.",
        "typical_causes": "Water quality, detergent residue, or passivation color.",
        "clinical_significance": "Cosmetic only unless associated with corrosion or soil.",
        "spd_response": "Monitor; investigate if progressive or paired with corrosion.",
        "supervisor_tips": "Recurrent staining often points to water-quality issues.",
    },
    "pitting": {
        "why_it_matters": (
            "Pitting is localized surface wear that can create micro-cavities where "
            "contamination may persist and cleaning becomes less reliable."
        ),
        "definition": "Small surface cavities from wear or corrosion.",
        "typical_causes": "Chloride pitting corrosion or mechanical wear.",
        "clinical_significance": "Pits can shelter soil and progress to structural weakness.",
        "spd_response": "Monitor minor pitting; evaluate if extensive.",
        "supervisor_tips": "Track pitting over time on the instrument passport.",
    },
    "crack": {
        "why_it_matters": (
            "Cracks may harbor contamination that cannot be reliably removed. Structural "
            "defects may also affect instrument performance and patient safety."
        ),
        "definition": "A fracture or fissure in the instrument body or jaws.",
        "typical_causes": "Fatigue, mechanical stress, or manufacturing defect.",
        "clinical_significance": "Cracks create protected surfaces where microorganisms may persist after sterilization.",
        "spd_response": "Remove from service and evaluate for repair or replacement.",
        "supervisor_tips": "Inspect stress points — jaws, ratchets, and welds.",
    },
    "insulation_damage": {
        "why_it_matters": (
            "Insulation damage on electrosurgical instruments can cause stray energy and "
            "harbor contamination; the instrument should be removed from service."
        ),
        "definition": "Breach in the insulating coating of a monopolar/bipolar instrument.",
        "typical_causes": "Wear, arcing, or handling damage.",
        "clinical_significance": "Insulation failure is a patient-safety burn hazard and a soil trap.",
        "spd_response": "Remove from service; test and repair or replace.",
        "supervisor_tips": "Consider routine insulation integrity testing for electrosurgical items.",
    },
    "missing_component": {
        "why_it_matters": (
            "A missing component means the instrument is incomplete, may not function as "
            "intended, and the missing part may be retained in a prior field."
        ),
        "definition": "An absent screw, insert, or removable part.",
        "typical_causes": "Loss during use or reprocessing; incomplete reassembly.",
        "clinical_significance": "Incomplete instruments are a functional and retained-item risk.",
        "spd_response": "Remove from service; complete assembly or replace.",
        "supervisor_tips": "Verify against the tray content list and instrument photo.",
    },
}

# ── Expanded next-action checklists (Phase 14.3) ─────────────────────────────
NEXT_ACTIONS: dict[str, list[str]] = {
    "PASS": ["Routine processing."],
    "MONITOR": ["Continue surveillance during future inspections."],
    "SUPERVISOR REVIEW": [
        "Hold instrument.",
        "Notify SPD supervisor.",
        "Review manufacturer IFU.",
    ],
    "REPROCESS": [
        "Return instrument for complete cleaning.",
        "Repeat inspection after reprocessing.",
    ],
    "REMOVE FROM SERVICE": [
        "Remove instrument from circulation.",
        "Generate repair work order.",
        "Notify supervisor.",
        "Document serial number.",
        "Track instrument in Instrument Passport.",
    ],
}

# ── Standards & guidance summaries (Phase 14.4) — paraphrased, not quoted ─────
STANDARDS_GUIDANCE: dict[str, str] = {
    "PASS": (
        "Consistent with accepted sterile-processing practice: instruments meeting the "
        "approved baseline with no actionable findings proceed through routine "
        "processing. Follow the manufacturer IFU for the specific device."
    ),
    "MONITOR": (
        "Accepted practice supports releasing instruments with minor cosmetic variation "
        "while tracking the finding over time so any progression is caught early. "
        "Reference the manufacturer IFU and internal policy for surveillance intervals."
    ),
    "SUPERVISOR REVIEW": (
        "When cleanliness or condition is uncertain, general guidance is to hold the "
        "item and escalate for a qualified second review before release, consulting the "
        "manufacturer IFU. This aligns with quality-review expectations in AAMI ST79 and "
        "AORN guidance for questionable instruments."
    ),
    "REPROCESS": (
        "Retained soil should be fully removed before sterilization; standard practice is "
        "to return the instrument for complete cleaning and re-inspect. Effective cleaning "
        "prior to sterilization is a foundational sterile-processing principle (AAMI ST79)."
    ),
    "REMOVE FROM SERVICE": (
        "Instruments with structural defects or damage that could harbor contamination or "
        "impair function should be taken out of service and evaluated for repair or "
        "replacement, per manufacturer IFU and accepted quality practice (AAMI ST79 / AORN)."
    ),
}


def _sev(result: dict, kpi: str) -> int:
    for f in result.get("predicted_findings", []):
        if f["type"] == kpi:
            return f["severity_index"]
    return 0


def _present_findings(result: dict) -> list[str]:
    """Clinically actionable findings: moderate+ (idx>=2) anywhere, OR trace+
    contamination (idx>=1) in a HIGH-retention zone — so that anything which
    escalates the disposition is also surfaced in the explanation."""
    from app.services.instrument_zones import is_high_retention
    out = []
    for f in result.get("predicted_findings", []):
        idx = f["severity_index"]
        if idx >= 2:
            out.append(f["type"])
        elif (idx >= 1 and f["type"] in _CONTAMINATION_TYPES
              and is_high_retention(f.get("instrument_zone", ""))):
            out.append(f["type"])
    return out


_CONTAMINATION_TYPES = {"blood", "tissue", "other_organic_residue", "debris", "bone"}


def _band(level: str) -> str:
    return level


def contamination_risk(result: dict) -> str:
    """Contamination-only risk dimension: Low / Medium / High / Critical."""
    if result.get("analysis_status") != "completed":
        return "Low"
    if _sev(result, "blood") >= 2 or _sev(result, "tissue") >= 2 or _sev(result, "other_organic_residue") >= 2:
        return "Critical"
    if _sev(result, "debris") >= 2 or _sev(result, "bone") >= 2:
        return "High"
    if any(_sev(result, k) == 1 for k in CLEANING_KPIS):
        return "Medium"
    return "Low"


def integrity_risk(result: dict) -> str:
    """Structural-integrity-only risk dimension: Low / Medium / High / Critical."""
    if result.get("analysis_status") != "completed":
        return "Low"
    if any(_sev(result, k) >= 2 for k in _STRUCTURAL_KPIS) or _sev(result, "corrosion") >= 3 or _sev(result, "rust") >= 3:
        return "Critical"
    if _sev(result, "corrosion") == 2 or _sev(result, "rust") == 2 or _sev(result, "pitting") >= 2:
        return "High"
    if any(_sev(result, k) == 1 for k in INTEGRITY_KPIS):
        return "Medium"
    return "Low"


def detailed_interpretation(result: dict, overall: str) -> list[str]:
    """Finding-specific clinical interpretation (Phase 14.1)."""
    if result.get("analysis_status") != "completed":
        return [
            "No approved baseline was available, so a final interpretation is withheld.",
            "A supervisor should review this instrument before release.",
        ]
    present = _present_findings(result)
    match = result.get("baseline_match_score")
    findings_by_kpi = {f["type"]: f for f in result.get("predicted_findings", [])}
    lines: list[str] = []
    if match is not None:
        lines.append(f"The instrument matched its approved baseline at {round(match * 100)}%.")

    def _zone_phrase(kpi: str) -> str:
        f = findings_by_kpi.get(kpi, {})
        zone = f.get("instrument_zone")
        if not zone or zone in ("unspecified region", "surface discoloration area"):
            return ""
        from app.services.instrument_zones import is_high_retention
        tag = ", a high-retention zone" if is_high_retention(zone) else ""
        return f" in the {zone} region{tag}"

    structural = [k for k in present if k in _STRUCTURAL_KPIS or (k == "corrosion" and _sev(result, k) >= 3)]
    contamination = [k for k in present if k in CLEANING_KPIS]

    if structural:
        primary = structural[0]
        edu = FINDING_EDUCATION.get(primary, {})
        lines.append(f"A structural finding consistent with {KPI_LABELS.get(primary, primary)} was detected{_zone_phrase(primary)}.")
        if not contamination:
            lines.append("Although contamination was not detected, the structural integrity of the instrument may be compromised.")
        if edu.get("clinical_significance"):
            lines.append(edu["clinical_significance"])
        lines.append("This instrument should not be returned to clinical use until evaluated.")
    elif contamination:
        primary = contamination[0]
        edu = FINDING_EDUCATION.get(primary, {})
        lines.append(f"{KPI_LABELS.get(primary, primary).capitalize()} indicators were detected{_zone_phrase(primary)}.")
        if edu.get("clinical_significance"):
            lines.append(edu["clinical_significance"])
        lines.append("The instrument should be returned for cleaning and re-inspected before release.")
    elif overall == "MONITOR":
        lines.append("Only minor cosmetic variation was observed, which does not require intervention now.")
        lines.append("Continue to monitor the instrument during future inspections.")
    else:
        lines.append("No contamination or structural defect requiring intervention was identified.")
        lines.append("The observed characteristics are consistent with the approved baseline.")
    return lines


def why_this_matters(result: dict) -> list[dict]:
    """Educational 'why this matters' for each actionable finding (Phase 14.2)."""
    out = []
    for kpi in _present_findings(result):
        edu = FINDING_EDUCATION.get(kpi)
        if edu:
            out.append({"finding": KPI_LABELS.get(kpi, kpi), "why_it_matters": edu["why_it_matters"]})
    return out


def learning_content(result: dict) -> list[dict]:
    """Learning-mode education for every reported KPI (Phase 14.5)."""
    out = []
    for f in result.get("predicted_findings", []):
        edu = FINDING_EDUCATION.get(f["type"])
        if not edu:
            continue
        out.append({
            "finding": KPI_LABELS.get(f["type"], f["type"]),
            "detected": f["severity_index"] >= 2,
            "definition": edu["definition"],
            "typical_causes": edu["typical_causes"],
            "clinical_significance": edu["clinical_significance"],
            "spd_response": edu["spd_response"],
            "supervisor_tips": edu["supervisor_tips"],
            "example_images_note": "Example images will be added in a future computer vision release.",
        })
    return out


def ai_mentor(result: dict, overall: str) -> dict:
    """AI Mentor synthesis (Phase 14.14): what / why / confidence / standard / next."""
    present = _present_findings(result)
    what = (
        [KPI_LABELS.get(k, k) for k in present]
        if present else ["No actionable findings detected."]
    )
    primary = present[0] if present else None
    why = (
        FINDING_EDUCATION.get(primary, {}).get("why_it_matters", "")
        if primary else
        "The instrument is consistent with its approved baseline; routine handling applies."
    )
    conf = result.get("confidence_level")
    conf_pct = round((result.get("confidence") or 0) * 100)

    # Zone-specific reasoning (Phase 15 §8): where + why the zone is high-risk.
    findings_by_kpi = {f["type"]: f for f in result.get("predicted_findings", [])}
    where_detected = ""
    why_zone_high_risk = ""
    verify_manually = ""
    if primary:
        pf = findings_by_kpi.get(primary, {})
        zone = pf.get("instrument_zone")
        if zone and zone not in ("unspecified region", "surface discoloration area"):
            where_detected = f"In the {zone}."
            why_zone_high_risk = pf.get("zone_reason", "")
            verify_manually = pf.get("recommended_manual_check", "")

    return {
        "what_was_detected": what,
        "where_was_it_detected": where_detected or "No specific high-risk zone implicated.",
        "why_it_matters": why,
        "why_this_zone_is_high_risk": why_zone_high_risk,
        "verify_manually": verify_manually,
        "how_confident": f"{conf or 'n/a'} ({conf_pct}%)" if result.get("confidence") is not None else "n/a",
        "standard_practice": STANDARDS_GUIDANCE.get(overall, ""),
        "what_should_happen_next": NEXT_ACTIONS.get(overall, []),
    }


def build_mentor(result: dict, overall: str) -> dict:
    """Assemble the full Phase-14 mentor payload."""
    return {
        "clinical_interpretation": detailed_interpretation(result, overall),
        "why_this_matters": why_this_matters(result),
        "next_actions": NEXT_ACTIONS.get(overall, []),
        "standards_guidance": STANDARDS_GUIDANCE.get(overall, ""),
        "learning_mode": learning_content(result),
        "contamination_risk": contamination_risk(result),
        "integrity_risk": integrity_risk(result),
        "ai_mentor": ai_mentor(result, overall),
    }
