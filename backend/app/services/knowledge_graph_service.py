"""Phase 21 — SPD Clinical Knowledge Graph & Clinical Reasoning Engine.

Represents the SPD clinical ontology as queryable nodes/edges built from
real, existing structured knowledge (instrument anatomy, zone taxonomy,
per-finding clinical education, cleaning knowledge, family profiles) plus
real database rows (Inspection, SupervisorReview, BaselineLibraryEntry,
InstrumentKnowledge) — not a separate graph database.
Every traversal is deterministic and grounded; nothing here is a trained
model or a black box.

The chain this module reasons over (see
docs/architecture/lumenai-clinical-ontology.md for the platform-wide
version this specializes):

Instrument -> Manufacturer -> Instrument Family -> Model -> Anatomy ->
Inspection Zone -> Retention Risk -> Cleaning Method -> Typical
Contamination -> Typical Damage -> Clinical Meaning -> Recommended Action
-> Supervisor Validation -> Learning
"""
from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.services.baseline_comparison_scoring_service import _ACTION_TEXT
from app.services.cleaning_knowledge import get_cleaning_knowledge
from app.services.clinical_mentor import FINDING_EDUCATION
from app.services.instrument_anatomy import anatomy_profile, resolve_family
from app.services.instrument_family_profiles import get_family_profile, list_family_profiles
from app.services.instrument_zones import ZONE_INFO, is_high_retention, zone_fields

# ---------------------------------------------------------------------------
# Section 1 — Node / relationship taxonomy
# ---------------------------------------------------------------------------

NODE_TYPES = [
    "Instrument", "Manufacturer", "InstrumentFamily", "Model", "AnatomyZone",
    "InspectionZone", "Finding", "Severity", "SPDRisk", "CleaningMethod",
    "BrushType", "IFU", "RepairRecommendation", "ReplacementRecommendation",
    "SupervisorDecision", "ClinicalRecommendation", "TrainingDataset",
]

RELATIONSHIP_TYPES = [
    "Instrument HAS Anatomy",
    "Anatomy HAS Zone",
    "Zone HAS Retention Risk",
    "Zone HAS Cleaning Method",
    "Zone HAS Common Findings",
    "Finding HAS Clinical Meaning",
    "Finding HAS Severity",
    "Finding REQUIRES Action",
    "Supervisor VALIDATES Finding",
    "Inspection CREATES Learning Signal",
]

_CONTAMINATION_FINDINGS = {"blood", "bone", "tissue", "debris", "other", "other_organic_residue"}
_STRUCTURAL_FINDINGS = {"crack", "corrosion", "insulation_damage", "pitting", "rust", "missing_component", "discoloration"}

# The 8 families that predate the v1.10 anatomy expansion — the legacy pilot
# zone-assignment taxonomy (instrument_zones.py) was hand-written against
# these specific 8 and is exercised by existing tests that accept its zone
# names as-is even where they differ from instrument_anatomy.py's own zone
# vocabulary for the same family (e.g. scissors: legacy "hinge" vs. anatomy
# "box lock"/"cutting edge" for the same mechanical pivot). The v1.10
# expansion's 104 new families were never given legacy rules of their own,
# so a legacy keyword match for one of them (e.g. "clamp" catching "towel
# clamp") is coincidental, not a deliberate mapping — only for those is a
# legacy zone name that the resolved family doesn't declare a real bug
# worth substituting away.
_LEGACY_TAXONOMY_FAMILIES = frozenset({
    "flexible_endoscope", "rigid_scope", "drill_bit", "kerrison_rongeur",
    "scissors", "needle_holder", "laparoscopic", "general_forceps",
})


def graph_schema() -> dict:
    """The node/relationship taxonomy itself — Section 1 deliverable."""
    return {
        "node_types": NODE_TYPES,
        "relationship_types": RELATIONSHIP_TYPES,
        "chain": [
            "Instrument", "Manufacturer", "Instrument Family", "Model", "Anatomy",
            "Inspection Zone", "Retention Risk", "Cleaning Method",
            "Typical Contamination", "Typical Damage", "Clinical Meaning",
            "Recommended Action", "Supervisor Validation", "Learning",
        ],
    }


# ---------------------------------------------------------------------------
# Section 2/5/6 — Clinical Reasoning Chain + Explainability Graph
# ---------------------------------------------------------------------------

def _finding_label(finding_type: str) -> str:
    return (finding_type or "").replace("_", " ").strip() or "an unspecified finding"


def _recommended_action_text(finding_type: str, zone: str) -> tuple[str, str]:
    """Generic (severity-unaware) recommended action + outcome key for the
    knowledge-graph explorer, where no scored inspection exists yet."""
    finding = (finding_type or "").strip().lower()
    if finding in _CONTAMINATION_FINDINGS:
        outcome = "REPROCESS"
        action = "recleaning, repeat inspection, and supervisor verification"
    elif finding in {"crack", "missing_component"} or (finding == "corrosion" and is_high_retention(zone)):
        outcome = "REMOVE FROM SERVICE"
        action = "removal from service pending repair evaluation and supervisor review"
    elif finding in _STRUCTURAL_FINDINGS:
        outcome = "SUPERVISOR REVIEW"
        action = "supervisor review and structural evaluation"
    else:
        outcome = "PASS"
        action = "routine processing"
    return outcome, action


def reasoning_chain(instrument_type: str, finding_type: str, manufacturer: str = "", model: str = "") -> dict:
    """The traceable Instrument -> ... -> Recommendation chain (generic,
    severity-unaware) used by the Knowledge Graph Explorer. For a specific
    scored inspection, use `explain_inspection` instead."""
    profile = anatomy_profile(instrument_type, manufacturer=manufacturer, model=model)
    family = profile["instrument_family"]
    zinfo = zone_fields(instrument_type, finding_type)
    zone = zinfo["instrument_zone"]
    zone_risk = zinfo["zone_risk"]
    zone_reason = zinfo["zone_reason"]

    declared_zones = profile.get("anatomy_zones") or []
    if profile["profile_found"] and family not in _LEGACY_TAXONOMY_FAMILIES and zone not in declared_zones:
        # The legacy pilot zone-assignment taxonomy (instrument_zones.py,
        # written before the v1.10 anatomy-family expansion) doesn't have a
        # rule for every new family, so it can hand back a generic zone
        # name (e.g. "serrations") that this specific family never
        # declares — reporting a zone the instrument doesn't actually have.
        # Fall back to a zone the resolved family's own registry declares,
        # preferring its highest-risk zone so the chain stays clinically
        # meaningful.
        candidates = profile.get("high_risk_zones") or declared_zones
        if candidates:
            zone = candidates[0]
            zone_risk = zinfo["zone_risk"]  # no more-specific real-zone risk is tracked separately here
            zone_reason = profile.get("zone_descriptions", {}).get(zone, zone_reason)

    cleaning = get_cleaning_knowledge(zone)
    education = FINDING_EDUCATION.get((finding_type or "").strip().lower(), {})
    outcome, action_phrase = _recommended_action_text(finding_type, zone)
    finding_label = _finding_label(finding_type)

    steps = [
        {"node": "Instrument", "value": instrument_type},
        {"node": "Manufacturer", "value": manufacturer or "not specified"},
        {"node": "Instrument Family", "value": family},
        {"node": "Model", "value": model or "not specified"},
        {"node": "Anatomy Zone", "value": zone, "note": profile.get("warning")},
        {"node": "Inspection Zone", "value": zone},
        {"node": "Retention Risk", "value": zone_risk},
        {"node": "Cleaning Method", "value": cleaning["cleaning_method"]},
        {"node": "Typical Contamination", "value": profile.get("contamination_risks", {}).get(zone, [])},
        {"node": "Typical Damage", "value": profile.get("condition_risks", {}).get(zone, [])},
        {"node": "Clinical Meaning", "value": education.get("clinical_significance") or education.get("why_it_matters", "")},
        {"node": "Recommended Action", "value": _ACTION_TEXT.get(outcome, action_phrase), "outcome": outcome},
        {"node": "Supervisor Validation", "value": "Required before disposition — routed to the Supervisor Review Queue."},
        {"node": "Learning", "value": "A confirmed or corrected supervisor review becomes a Phase 18 ground-truth training label."},
    ]

    narrative = (
        f"I detected probable {finding_label} in the {instrument_type} {zone}. "
        f"{zone_reason} "
        f"Based on SPD best practices and the {family.replace('_', ' ')} instrument profile, "
        f"{action_phrase} are recommended before the instrument proceeds to packaging."
    )

    return {
        "instrument_type": instrument_type,
        "manufacturer": manufacturer,
        "model": model,
        "finding_type": finding_type,
        "chain": steps,
        "narrative": narrative,
        "human_review_required": True,
    }


def explain_inspection(db: Session, inspection) -> dict:
    """Section 6 — Explainability graph for one real, scored inspection.
    Uses the inspection's actual persisted recommended_action/risk_score
    rather than the generic (severity-unaware) reasoning_chain estimate."""
    zinfo = zone_fields(inspection.instrument_type, inspection.detected_issue)
    zone = zinfo["instrument_zone"]
    education = FINDING_EDUCATION.get((inspection.detected_issue or "").strip().lower(), {})
    cleaning = get_cleaning_knowledge(zone)
    family = resolve_family(inspection.instrument_type)

    return {
        "inspection_id": inspection.id,
        "why": [
            {"node": "Finding", "value": inspection.detected_issue, "detail": "AI-detected finding on this inspection."},
            {"node": "Zone", "value": zone, "detail": zinfo["zone_reason"]},
            {"node": "Clinical Significance", "value": education.get("clinical_significance", "")},
            {"node": "SPD Rule", "value": cleaning["cleaning_method"]},
            {"node": "Recommendation", "value": inspection.recommended_action or "Pending analysis."},
        ],
        "instrument_family": family,
        "risk_score": inspection.risk_score,
        "human_review_required": True,
    }


# ---------------------------------------------------------------------------
# Section 3 — Instrument Family Intelligence (thin wrapper)
# ---------------------------------------------------------------------------

def get_instrument_family_intelligence(family_key: str) -> dict | None:
    return get_family_profile(family_key)


def list_instrument_family_intelligence() -> list[dict]:
    return list_family_profiles()


# ---------------------------------------------------------------------------
# Section 7 — Knowledge Graph Explorer
# ---------------------------------------------------------------------------

def explore(db: Session, tenant_id: str, category: str, query: str = "") -> dict:
    """Search the knowledge graph by category. Every result is backed by
    real data — no fabricated node ever appears here."""
    from app.db import models
    from app.models.baseline_library import BaselineLibraryEntry
    from app.models.instrument_knowledge import InstrumentKnowledge
    from app.models.supervisor_review import SupervisorReview

    q = (query or "").strip().lower()
    category = (category or "").strip().lower()

    if category == "manufacturer":
        rows = db.query(models.Inspection.vendor_name, models.Inspection.id).filter(
            models.Inspection.tenant_id == tenant_id
        ).all()
        counts: dict[str, int] = defaultdict(int)
        for vendor, _ in rows:
            name = (vendor or "unknown").strip()
            if q and q not in name.lower():
                continue
            counts[name] += 1
        return {"category": "manufacturer", "results": [{"manufacturer": k, "inspection_count": v} for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]}

    if category == "instrument":
        rows = db.query(models.Inspection.instrument_type).filter(models.Inspection.tenant_id == tenant_id).distinct().all()
        results = []
        for (itype,) in rows:
            if q and q not in (itype or "").lower():
                continue
            results.append({"instrument_type": itype, "instrument_family": resolve_family(itype)})
        return {"category": "instrument", "results": results}

    if category == "model":
        rows = db.query(BaselineLibraryEntry.model_name, BaselineLibraryEntry.manufacturer_name, BaselineLibraryEntry.instrument_category).all()
        results = []
        for model_name, manufacturer_name, category_name in rows:
            if q and q not in (model_name or "").lower():
                continue
            results.append({"model": model_name, "manufacturer": manufacturer_name, "instrument_category": category_name})
        return {"category": "model", "results": results}

    if category == "finding":
        results = []
        for finding, info in FINDING_EDUCATION.items():
            if q and q not in finding.lower():
                continue
            results.append({"finding": finding, "why_it_matters": info.get("why_it_matters"), "clinical_significance": info.get("clinical_significance")})
        return {"category": "finding", "results": results}

    if category == "zone":
        results = []
        for zone, info in ZONE_INFO.items():
            if q and q not in zone.lower():
                continue
            results.append({"zone": zone, **info, "cleaning": get_cleaning_knowledge(zone)})
        return {"category": "zone", "results": results}

    if category == "failure_mode":
        rows = db.query(InstrumentKnowledge).filter(InstrumentKnowledge.tenant_id == tenant_id).all()
        results = []
        for r in rows:
            try:
                modes = json.loads(r.known_failure_modes or "[]")
            except (TypeError, ValueError):
                modes = []
            for m in modes:
                if q and q not in str(m).lower():
                    continue
                results.append({"manufacturer": r.manufacturer, "model": r.model, "instrument_family": r.instrument_family, "failure_mode": m})
        return {"category": "failure_mode", "results": results}

    if category == "instrument_family":
        from app.services.instrument_anatomy import list_anatomy_families

        results = []
        for fam in list_anatomy_families():
            if q and q not in fam["family"].lower() and q not in fam["category"].lower():
                continue
            results.append(fam)
        return {"category": "instrument_family", "results": results, "total_families": len(results)}

    if category == "recommendation":
        results = [{"outcome": k, "action_text": v} for k, v in _ACTION_TEXT.items() if not q or q in k.lower() or q in v.lower()]
        return {"category": "recommendation", "results": results}

    if category == "supervisor_learning":
        rows = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
        total = len(rows)
        agree = sum(1 for r in rows if r.agreement == "agree")
        corrections = [r.corrected_zone for r in rows if r.corrected_zone]
        return {
            "category": "supervisor_learning",
            "results": {
                "total_reviews": total,
                "agreement_rate": round(agree / total, 4) if total else None,
                "common_zone_corrections": sorted(set(corrections)),
            },
        }

    return {"category": category, "results": [], "error": "Unknown category. Use one of: manufacturer, instrument, model, finding, zone, failure_mode, recommendation, supervisor_learning, instrument_family."}


# ---------------------------------------------------------------------------
# Section 8 — Enterprise Knowledge Analytics
# ---------------------------------------------------------------------------

def enterprise_knowledge_analytics(db: Session, tenant_id: str) -> dict:
    from app.db import models
    from app.models.supervisor_review import SupervisorReview
    from app.services.ml.pilot_validation import zone_performance as compute_zone_performance
    from app.services.pre_sterilization_command_center_service import REQUIRES_REPAIR, classify_readiness

    inspections = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).all()
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()

    def _top(counter: dict, n: int = 5) -> list[dict]:
        return [{"key": k, "count": v} for k, v in sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:n]]

    findings_by_manufacturer: dict[str, int] = defaultdict(int)
    findings_by_zone: dict[str, int] = defaultdict(int)
    contamination_counts: dict[str, int] = defaultdict(int)
    repair_reasons: dict[str, int] = defaultdict(int)
    family_disagreements: dict[str, int] = defaultdict(int)

    for insp in inspections:
        issue = (insp.detected_issue or "").strip().lower()
        if issue and issue not in ("none", "unknown"):
            findings_by_manufacturer[f"{insp.vendor_name or 'unknown'}:{issue}"] += 1
            zone = zone_fields(insp.instrument_type, issue)["instrument_zone"]
            findings_by_zone[f"{zone}:{issue}"] += 1
            if issue in _CONTAMINATION_FINDINGS:
                contamination_counts[issue] += 1
        classified = classify_readiness(insp)
        if classified["readiness_state"] == REQUIRES_REPAIR:
            repair_reasons[issue] += 1

    for r in reviews:
        key = r.corrected_instrument_family or "unspecified"
        if r.agreement != "agree" or r.override_action:
            family_disagreements[key] += 1

    override_counts: dict[str, int] = defaultdict(int)
    for r in reviews:
        if r.override_action:
            override_counts[r.override_action] += 1

    # Zone-level miss/override performance, derived directly from real
    # supervisor reviews (ground_truth is computed at review-submit time) —
    # not a separate training-case table.
    zp = compute_zone_performance(reviews)
    most_missed_zones = [
        {"zone": z["zone"], "missed_count": z["missed"], "case_count": zp["by_zone"][z["zone"]]["n"]}
        for z in zp["most_common_missed_zones"][:5]
    ]
    highest_risk_zone = most_missed_zones[0]["zone"] if most_missed_zones else None

    reviews_by_family_total: dict[str, int] = defaultdict(int)
    for r in reviews:
        reviews_by_family_total[r.corrected_instrument_family or "unspecified"] += 1
    most_difficult_family = None
    if family_disagreements:
        candidates = {
            fam: round(cnt / reviews_by_family_total[fam], 4)
            for fam, cnt in family_disagreements.items() if reviews_by_family_total.get(fam)
        }
        if candidates:
            most_difficult_family = max(candidates, key=lambda k: candidates[k])

    return {
        "most_common_findings_by_manufacturer": _top(findings_by_manufacturer),
        "most_common_findings_by_anatomy": _top(findings_by_zone),
        "highest_risk_anatomy_zone": highest_risk_zone,
        "most_common_repair_reason": _top(repair_reasons, n=3),
        "most_common_supervisor_override": _top(override_counts, n=3),
        "most_difficult_instrument_family": most_difficult_family,
        "most_missed_anatomy_zones": most_missed_zones,
        "most_common_contamination_type": _top(contamination_counts, n=5),
        "human_review_required": True,
    }


# ---------------------------------------------------------------------------
# Section 9 — Continuous Knowledge Learning (confidence, computed live)
# ---------------------------------------------------------------------------

def learning_confidence(db: Session, tenant_id: str) -> dict:
    """Confidence signals derived from real supervisor reviews and ground
    truth — updated every time a review is submitted, never mutated by a
    background process, never fabricated. Ground truth is read from
    SupervisorReview.ground_truth itself (derived at submit time), not a
    separate training-case table."""
    from app.models.supervisor_review import SupervisorReview

    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()

    def _rate(n, d):
        return round(n / d, 4) if d else None

    n = len(reviews)
    agree = sum(1 for r in reviews if r.agreement == "agree")
    finding_correct = [r for r in reviews if r.finding_correct is not None]
    zone_correct = [r for r in reviews if r.zone_correct is not None]

    adjudicated = [r for r in reviews if r.ground_truth in ("true_positive", "true_negative", "false_positive", "false_negative")]
    reasoning_correct = sum(1 for r in adjudicated if r.ground_truth in ("true_positive", "true_negative"))

    per_family: dict[str, dict] = {}
    by_family_reviews: dict[str, list] = defaultdict(list)
    for r in reviews:
        key = r.corrected_instrument_family or "unspecified"
        by_family_reviews[key].append(r)
    for fam, fam_reviews in by_family_reviews.items():
        correct = [r for r in fam_reviews if r.instrument_family_correct is not False]
        per_family[fam] = {"review_count": len(fam_reviews), "instrument_profile_confidence": _rate(len(correct), len(fam_reviews))}

    return {
        "knowledge_confidence": _rate(agree, n),
        "reasoning_confidence": _rate(reasoning_correct, len(adjudicated)),
        "clinical_recommendation_confidence": _rate(sum(1 for r in finding_correct if r.finding_correct), len(finding_correct)),
        "zone_confidence": _rate(sum(1 for r in zone_correct if r.zone_correct), len(zone_correct)),
        "instrument_profile_confidence_by_family": per_family,
        "sample_sizes": {"supervisor_reviews": n, "adjudicated_ground_truth_cases": len(adjudicated)},
        "human_review_required": True,
        "note": "Confidence is recomputed from real supervisor reviews on every request — it improves as more reviews accumulate, it is not a mutated/persisted model state.",
    }
