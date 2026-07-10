"""v2.2 — Vision Session Engine ("Project Vision 360").

Analyzes every image captured for one inspection together, rather than in
isolation — the Image Timeline, Missing Anatomy Detection, Cross-Image
Reasoning, and Evidence Fusion the sprint asks for. Built entirely by
composing real, already-computed data (InspectionImageTag rows, the
scoring engine's zone-tagged predicted findings, the Coverage Engine,
SupervisorReview history, baseline resolution) — nothing here is a second,
parallel AI decision; it fuses the signals the platform already produces
per image/finding into one session-level view.
"""
from __future__ import annotations

from app.services.inspection_coverage import compute_coverage, missing_image_guidance

_CONTAMINATION_FINDINGS = {"blood", "bone", "tissue", "debris", "other_organic_residue"}


def tag_to_dict(t) -> dict:
    """One InspectionImageTag row -> the dict shape every session view uses."""
    return {
        "id": t.id,
        "anatomy_zone": t.anatomy_zone,
        "image_view": t.image_view,
        "instrument_family": t.instrument_family,
        "image_sha256": t.image_sha256,
        "capture_quality": t.capture_quality,
        "quality_score": t.quality_score,
        "quality_band": t.quality_band,
        "technician": t.technician,
        "sequence": t.sequence,
        "flagged": t.flagged,
        "flag_reason": t.flag_reason,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "notes": t.notes,
    }


def image_timeline(tag_dicts: list[dict]) -> list[dict]:
    """Objective 8 — Image Timeline: the inspection sequence, in capture
    order, each entry showing what was captured."""
    ordered = sorted(tag_dicts, key=lambda t: (t["sequence"] if t["sequence"] is not None else t["id"]))
    return [
        {
            "sequence": idx + 1,
            "tag_id": t["id"],
            "anatomy_zone": t["anatomy_zone"] or "unspecified",
            "image_view": t["image_view"],
            "captured": True,
            "quality_band": t["quality_band"],
            "flagged": t["flagged"],
        }
        for idx, t in enumerate(ordered)
    ]


def missing_anatomy_prompts(instrument_type: str, tag_dicts: list[dict]) -> dict:
    """Objective 5 — Missing Anatomy Detection: "You have not captured the
    O-ring." style prompts for every required zone with no image yet, plus
    one suggested next zone. Reuses the Coverage Engine's own required-zone
    list rather than re-deriving it."""
    captured_zones = [t["anatomy_zone"] for t in tag_dicts if t["anatomy_zone"]]
    coverage = compute_coverage(instrument_type, captured_zones)
    guidance = missing_image_guidance(instrument_type, captured_zones)
    prompts = [
        {"zone": zone, "message": f"You have not captured the {zone}."}
        for zone in coverage["missing"]
    ]
    return {
        "prompts": prompts,
        "suggested_next": coverage["missing"][0] if coverage["missing"] else None,
        "missing_image_guidance": guidance,
        "coverage": coverage,
    }


def cross_image_reasoning(predicted_findings: list[dict], tag_dicts: list[dict]) -> dict:
    """Objective 6 — Cross-Image Reasoning: correlate each predicted
    finding (already zone-tagged by
    baseline_comparison_scoring_service.analyze_inspection) with whichever
    captured image shares that anatomy zone, and produce one overall
    picture. A finding present in even one image is real for the whole
    instrument — a clean neighboring image never cancels it out."""
    tags_by_zone: dict[str, list[dict]] = {}
    for t in tag_dicts:
        if t["anatomy_zone"]:
            tags_by_zone.setdefault(t["anatomy_zone"], []).append(t)

    per_finding = []
    contamination_found = False
    structural_found = False
    for f in predicted_findings:
        zone = f.get("instrument_zone", "")
        matched = tags_by_zone.get(zone, [])
        present = f.get("status") in ("review", "escalate") or f.get("severity_index", 0) >= 2
        if present:
            if f.get("type") in _CONTAMINATION_FINDINGS:
                contamination_found = True
            else:
                structural_found = True
        per_finding.append({
            "finding_type": f.get("type"),
            "instrument_zone": zone,
            "matched_image_tag_ids": [t["id"] for t in matched],
            "present": present,
            "severity": f.get("severity"),
        })

    if contamination_found and structural_found:
        overall = "Instrument shows both retained contamination and a structural finding across captured images."
    elif contamination_found:
        overall = "Instrument contains retained contamination identified across captured images."
    elif structural_found:
        overall = "Instrument shows a structural finding identified across captured images."
    else:
        overall = "No contamination or structural finding identified across captured images."

    return {
        "per_finding": per_finding,
        "contamination_found": contamination_found,
        "structural_found": structural_found,
        "overall_result": overall,
    }


def evidence_fusion(
    *, predicted_findings: list[dict], tag_dicts: list[dict], coverage: dict,
    baseline_source: str | None, supervisor_reviews: list,
) -> dict:
    """Objective 7 — Evidence Fusion: combine image evidence, baseline
    comparison, anatomy/coverage, confidence, and supervisor history into
    one clinical recommendation. This reads the same signals
    `analyze_inspection()` already computed — it is not a second,
    independent AI decision."""
    reasoning = cross_image_reasoning(predicted_findings, tag_dicts)

    confidences = [f.get("confidence") for f in predicted_findings if f.get("confidence") is not None]
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else None

    agreements = [r.agreement for r in supervisor_reviews]
    agree_rate = (
        round(sum(1 for a in agreements if a == "agree") / len(agreements), 2)
        if agreements else None
    )

    factors = {
        "image_evidence": reasoning["overall_result"],
        "baseline_comparison": baseline_source or "none",
        "coverage": coverage.get("quality", "not_assessed"),
        "average_confidence": avg_confidence,
        "supervisor_agreement_rate": agree_rate,
        "supervisor_review_count": len(supervisor_reviews),
    }

    if reasoning["contamination_found"] and not reasoning["structural_found"]:
        recommendation = "REPROCESS"
    elif reasoning["contamination_found"] or reasoning["structural_found"]:
        recommendation = "SUPERVISOR REVIEW"
    elif coverage.get("quality") in ("incomplete", "insufficient", "not_assessed"):
        recommendation = "SUPERVISOR REVIEW"
    else:
        recommendation = "PASS"

    agreement_sentence = (
        f"Supervisor agreement rate on this instrument's history is {int(agree_rate * 100)}%. "
        if agree_rate is not None else ""
    )

    return {
        "recommendation": recommendation,
        "contributing_factors": factors,
        "narrative": (
            f"{reasoning['overall_result']} Coverage is {coverage.get('quality', 'not_assessed')} "
            f"across {len(tag_dicts)} captured image(s). {agreement_sentence}"
            "Human supervisor validation is required before final disposition."
        ),
        "human_review_required": True,
    }
