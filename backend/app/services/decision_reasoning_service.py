"""v2.5 — Clinical Decision Reasoning Engine (Project Cortex, Sections 2/3/4/6/8).

LumenAI's recommendations should "emerge from structured clinical reasoning
that combines vision, instrument intelligence, anatomy, clinical memory,
digital twin, knowledge graph, SPD rules, and supervisor knowledge" — this
module is that composition layer. It does not re-run AI scoring; every input
is read from already-computed/persisted data (the same governance convention
`disposition_evidence_service.py` and `clinical_memory_service.py` follow).

- `gather_evidence()` — Section 3/6: assembles the multi-source evidence
  bundle (finding, anatomy/zone risk, Clinical Memory, digital twin snapshot,
  knowledge articles, supervisor notes) that both rule engines match against.
- `build_explainable_decision()` — Section 2/4: evidence -> reasoning path ->
  applied rules (SPD Rule Library + supervisor rules) -> clinical rationale
  -> final recommendation, in one structured, replayable object.
- `compute_recommendation_confidence()` — Section 8: vision confidence,
  reasoning confidence, and overall clinical confidence, reported
  separately rather than collapsed into one number.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_finding import InspectionFinding
from app.models.supervisor_review import SupervisorReview
from app.services.clinical_memory_service import get_clinical_memory
from app.services.instrument_anatomy import anatomy_profile, resolve_family
from app.services.instrument_zones import is_high_retention
from app.services.knowledge_repository_service import list_articles
from app.services.pre_sterilization_command_center_service import _instrument_identity
from app.services.spd_rule_library import evaluate_rules
from app.services.supervisor_rule_service import evaluate_supervisor_rules

_LEVEL_RANK = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}


def _is_high_risk_zone(instrument_type: str, zone: str) -> bool:
    if not zone:
        return False
    if is_high_retention(zone):
        return True
    profile = anatomy_profile(instrument_type)
    return zone in (profile.get("high_risk_zones") or [])


def _digital_twin_snapshot(tenant_id: str, facility_id: str, db: Session) -> dict | None:
    """Best-effort tenant/facility-wide SPD workflow twin state — ambient
    operational context, not a per-instrument history (the platform's
    `digital_twin_engine` tracks station flow, not clinical findings).
    Omitted rather than fabricated when it can't be resolved."""
    if not facility_id:
        return None
    try:
        from app.services.digital_twin_engine import get_twin_state

        state = get_twin_state(tenant_id, facility_id, db)
        return {
            "facility_id": facility_id,
            "bottleneck_station": getattr(state, "bottleneck_station", None),
            "throughput_per_hour": getattr(state, "throughput_per_hour", None),
            "utilization_pct": getattr(state, "utilization_pct", None),
        }
    except Exception:
        return None


def gather_evidence(db: Session, tenant_id: str, insp: models.Inspection) -> dict:
    """Section 3/6 — Rule Composition & Knowledge Graph Integration: the
    multi-source evidence bundle every rule (SPD library + supervisor-
    authored) matches against."""
    primary_finding = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.inspection_id == insp.id)
        .order_by(InspectionFinding.severity_index.desc())
        .first()
    )
    finding_type = primary_finding.finding_type if primary_finding else (insp.detected_issue or "").strip().lower()
    zone = primary_finding.zone if primary_finding else ""
    vision_confidence = primary_finding.confidence if primary_finding else insp.ai_confidence

    identity = _instrument_identity(insp)
    clinical_memory = get_clinical_memory(db, tenant_id, identity) if not identity.startswith("untracked:") else None

    repeat_finding = False
    repeat_occurrences = 0
    if clinical_memory:
        repeat_occurrences = clinical_memory["recurring_issues"]["finding_counts"].get(finding_type, 0)
        repeat_finding = repeat_occurrences >= 1 and clinical_memory["condition_history"]["inspection_count"] > 1
    else:
        from app.services.prioritization_engine import has_repeat_findings

        repeat_finding = has_repeat_findings(db, tenant_id, insp)

    supervisor_notes = [
        r.rationale for r in (
            db.query(SupervisorReview)
            .filter(SupervisorReview.inspection_id == insp.id)
            .order_by(SupervisorReview.id.desc())
            .all()
        ) if r.rationale.strip()
    ]

    knowledge_articles = list_articles(db, tenant_id, instrument=insp.instrument_type, finding=finding_type)[:5]

    return {
        "inspection_id": insp.id,
        "instrument_identity": identity,
        "instrument_type": insp.instrument_type,
        "instrument_family": resolve_family(insp.instrument_type),
        "finding_type": finding_type,
        "zone": zone,
        "high_risk_zone": _is_high_risk_zone(insp.instrument_type, zone),
        "repeat_finding": repeat_finding,
        "repeat_occurrences": repeat_occurrences,
        "vision_confidence": vision_confidence,
        "clinical_memory": clinical_memory,
        "knowledge_articles": knowledge_articles,
        "supervisor_notes": supervisor_notes,
        "digital_twin": _digital_twin_snapshot(tenant_id, insp.facility_name or "", db),
    }


def _reasoning_path(evidence: dict) -> list[dict]:
    """Section 4 — the human-readable evidence -> reasoning steps, before
    rules are applied. Each step names which evidence source contributed and
    why, so the final recommendation is traceable back to real data."""
    path = [
        {"step": "Finding", "detail": f"{evidence['finding_type'] or 'no finding'} detected in {evidence['zone'] or 'an unspecified zone'}."},
        {"step": "Anatomy", "detail": f"Zone is {'a declared high-risk zone' if evidence['high_risk_zone'] else 'not flagged as high-risk'} for this instrument family."},
    ]
    if evidence["clinical_memory"]:
        cm = evidence["clinical_memory"]
        path.append({
            "step": "Clinical Memory",
            "detail": f"{cm['condition_history']['inspection_count']} prior inspections on record; condition trend is {cm['condition_history']['condition_trend']}.",
        })
    if evidence["repeat_finding"]:
        path.append({
            "step": "Repeat Finding",
            "detail": f"This finding type has occurred {evidence['repeat_occurrences']} time(s) before on this same instrument." if evidence["repeat_occurrences"] else "This instrument has a prior logged finding.",
        })
    if evidence["digital_twin"]:
        path.append({
            "step": "Digital Twin",
            "detail": f"Facility workflow snapshot: bottleneck at {evidence['digital_twin'].get('bottleneck_station') or 'no station'}, {evidence['digital_twin'].get('throughput_per_hour')} instruments/hr.",
        })
    if evidence["knowledge_articles"]:
        path.append({
            "step": "Knowledge Articles",
            "detail": f"{len(evidence['knowledge_articles'])} applicable knowledge article(s) on record for this instrument/finding.",
        })
    if evidence["supervisor_notes"]:
        path.append({
            "step": "Supervisor Notes",
            "detail": f"{len(evidence['supervisor_notes'])} prior supervisor note(s) on this inspection.",
        })
    return path


def build_explainable_decision(db: Session, tenant_id: str, insp: models.Inspection) -> dict:
    """Section 2/4 — the full Explainable Decision Tree: evidence ->
    reasoning path -> applied rules -> clinical rationale -> final
    recommendation. Rules never silently override each other — every rule
    whose conditions are met is reported, and the highest-severity rule's
    recommendation is surfaced as the final one."""
    evidence = gather_evidence(db, tenant_id, insp)
    reasoning_path = _reasoning_path(evidence)

    applied_rules = evaluate_rules(evidence) + evaluate_supervisor_rules(db, tenant_id, evidence)
    applied_rules.sort(key=lambda r: _LEVEL_RANK.get(r["spd_risk"], 0), reverse=True)

    if applied_rules:
        top_rule = applied_rules[0]
        final_recommendation = {
            "recommendation": list(top_rule["recommendation"]),
            "severity": top_rule["severity"],
            "spd_risk": top_rule["spd_risk"],
            "driven_by_rule": top_rule["title"],
        }
        clinical_rationale = (
            f"Rule '{top_rule['title']}' applied: {top_rule['description']}"
        )
    else:
        final_recommendation = {
            "recommendation": ["Routine processing — no matched clinical decision rule."],
            "severity": "Low", "spd_risk": "Low", "driven_by_rule": None,
        }
        clinical_rationale = "No SPD or supervisor-authored rule matched this evidence bundle."

    return {
        "inspection_id": insp.id,
        "evidence": evidence,
        "reasoning_path": reasoning_path,
        "applied_rules": applied_rules,
        "clinical_rationale": clinical_rationale,
        "final_recommendation": final_recommendation,
        "human_review_required": True,
    }


def compute_recommendation_confidence(evidence: dict, applied_rules: list[dict]) -> dict:
    """Section 8 — vision confidence, reasoning confidence, and overall
    clinical confidence, reported independently rather than collapsed into
    one opaque number."""
    vision_confidence = evidence.get("vision_confidence")

    # Reasoning confidence: how much corroborating evidence backs the
    # decision — more independent sources agreeing raises confidence that
    # the reasoning (not the vision detection itself) is sound.
    sources = 0
    if evidence.get("clinical_memory"):
        sources += 1
    if evidence.get("knowledge_articles"):
        sources += 1
    if evidence.get("supervisor_notes"):
        sources += 1
    if applied_rules:
        sources += 1
    reasoning_confidence = round(min(1.0, 0.4 + 0.15 * sources), 2)

    if vision_confidence is not None:
        overall_clinical_confidence = round((vision_confidence + reasoning_confidence) / 2, 2)
    else:
        overall_clinical_confidence = reasoning_confidence

    return {
        "vision_confidence": round(vision_confidence, 2) if vision_confidence is not None else None,
        "reasoning_confidence": reasoning_confidence,
        "overall_clinical_confidence": overall_clinical_confidence,
        "basis": (
            "Vision confidence is the scoring engine's own per-finding confidence. Reasoning "
            "confidence reflects how many independent evidence sources corroborate the decision "
            "(Clinical Memory, knowledge articles, supervisor notes, matched rules) — not a "
            "validated statistical measure. Overall clinical confidence averages the two when "
            "vision confidence is available."
        ),
    }
