"""Project Council, Section 4: Independent Specialist Assessments.

Each resolver below derives one specialist's Council-shaped assessment
directly from that specialist's own, already-built real service -- Council
never re-runs clinical or operational analysis itself. A resolver that has
no relevant real data for the case returns an honest "insufficient data"
conclusion rather than fabricating one.

Independence (Section 1's "agents must first assess independently before
seeing other agents' conclusions") is structural: every resolver reads
only the case's evidence package and that one specialist's own store --
never another specialist's `CouncilSpecialistAssessment` row. Submitted
assessments are immutable; a specialist that revises its conclusion after
seeing the rest of the Council gets a new row with `is_revision=True`
pointing back at the original via `supersedes_assessment_id`, and the
original is never edited or deleted.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    APPROVER_CLINICAL_QUALITY_GOVERNANCE,
    APPROVER_DIRECTOR,
    APPROVER_SPD_MANAGER,
    APPROVER_SUPERVISOR,
    SPECIALIST_AEGIS,
    SPECIALIST_APOLLO,
    SPECIALIST_ATHENA,
    SPECIALIST_MAESTRO,
    SPECIALIST_PHOENIX,
    SPECIALIST_PULSE,
    SPECIALIST_RESEARCH_AGENT,
    SPECIALIST_SAGE,
    SPECIALIST_SENTINELX,
    SPECIALIST_VERITAS,
    SPECIALIST_VULCAN,
    CouncilCase,
    CouncilSpecialistAssessment,
)

_INSUFFICIENT_DATA = "insufficient_data"


def _first(items_json: str) -> str | int | None:
    try:
        items = json.loads(items_json or "[]")
    except (TypeError, ValueError):
        return None
    return items[0] if items else None


def _base(conclusion: str, *, confidence="moderate", evidence_used=None, evidence_limitations="", significance="",
          recommended_action="", alternative_explanation="", urgency="routine",
          human_role_required=APPROVER_SUPERVISOR) -> dict:
    return {
        "conclusion": conclusion,
        "confidence": confidence,
        "evidence_used": evidence_used or {},
        "evidence_limitations": evidence_limitations,
        "significance": significance,
        "recommended_action": recommended_action,
        "alternative_explanation": alternative_explanation,
        "urgency": urgency,
        "human_role_required": human_role_required,
    }


def _assess_veritas(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.veritas_evidence_agent_service import run_evidence_assessment, to_dict

    inspection_id = _first(case.inspection_ids_json)
    if inspection_id is None:
        return _base(
            _INSUFFICIENT_DATA, confidence="low",
            evidence_limitations="No inspection is attached to this Council Case for Veritas to evaluate.",
        )
    try:
        row = run_evidence_assessment(db, tenant_id, int(inspection_id))
    except ValueError as exc:
        return _base(_INSUFFICIENT_DATA, confidence="low", evidence_limitations=str(exc))
    result = to_dict(row)
    return _base(
        f"Evidence readiness: {result['readiness_category']} ({result['readiness_score']}/100).",
        confidence="high" if result["readiness_score"] >= 70 else "moderate",
        evidence_used={"readiness_score": result["readiness_score"], "coverage_status": result["coverage_status"], "image_quality_status": result["image_quality_status"]},
        evidence_limitations="; ".join(result.get("limitations", []) if isinstance(result.get("limitations"), list) else []),
        significance=f"Match classification: {result['match_classification']}.",
        recommended_action=f"Recommended gate: {result['recommended_gate']}.",
        urgency="urgent" if result["readiness_category"] in ("insufficient", "poor") else "routine",
        human_role_required=APPROVER_SUPERVISOR,
    )


def _assess_aegis(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.vulcan_aegis_integration_service import compute_process_variation_signal

    instrument_identity = _first(case.instrument_ids_json)
    if instrument_identity is None:
        return _base(
            _INSUFFICIENT_DATA, confidence="low",
            evidence_limitations="No instrument is attached to this Council Case for Aegis's process-variation check.",
        )
    signal = compute_process_variation_signal(db, tenant_id, str(instrument_identity))
    return _base(
        signal["narrative"] or "No strong process pattern detected.",
        confidence="moderate" if signal["sample_size"] >= 5 else "low",
        evidence_used=signal,
        significance="Process variation detected." if signal["process_variation_detected"] else "No enterprise process pattern found.",
        recommended_action="Review technician-specific technique." if signal["process_variation_detected"] else "No process-focused action indicated.",
        urgency="routine",
    )


def _assess_vulcan(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.vulcan_reliability_agent_service import run_reliability_assessment, to_dict

    instrument_identity = _first(case.instrument_ids_json)
    if instrument_identity is None:
        return _base(
            _INSUFFICIENT_DATA, confidence="low",
            evidence_limitations="No instrument is attached to this Council Case for Vulcan to assess.",
        )
    row = run_reliability_assessment(db, tenant_id, str(instrument_identity))
    result = to_dict(row)
    return _base(
        f"Reliability: {result.get('reliability_category')} ({result.get('reliability_score')}/100), progression: {result.get('progression')}.",
        confidence=result.get("confidence", "moderate"),
        evidence_used={"score_breakdown": result.get("score_breakdown"), "recurrence_count": result.get("recurrence_count")},
        significance=result.get("combined_conclusion", ""),
        recommended_action=result.get("recommended_disposition", ""),
        alternative_explanation="; ".join(
            c.get("probable_cause", "") for c in result.get("probable_causes", []) if isinstance(c, dict)
        ),
        urgency="urgent" if result.get("progression") == "worsening" else "routine",
        human_role_required=APPROVER_SPD_MANAGER,
    )


def _assess_sage(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.sage_knowledge_gap_service import list_gaps

    gaps = list_gaps(db, tenant_id, status="open")
    if not gaps:
        return _base(
            "No open competency gaps identified.", confidence="moderate",
            recommended_action="No education action indicated at this time.",
        )
    top = max(gaps, key=lambda g: g["occurrence_count"])
    return _base(
        top["narrative"] or f"Recurring knowledge gap in {top['competency_domain']}.",
        confidence=top.get("confidence", "moderate"),
        evidence_used={"occurrence_count": top["occurrence_count"], "competency_domain": top["competency_domain"]},
        significance=f"Scope: {top['scope_type']} / {top['scope_value']}.",
        recommended_action=top.get("recommended_education", "Schedule targeted competency review."),
        urgency="routine",
        human_role_required=APPROVER_SUPERVISOR,
    )


def _assess_sentinelx(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.sentinelx_risk_agent_service import run_risk_assessment, to_dict

    instrument_identity = _first(case.instrument_ids_json)
    if instrument_identity is None:
        return _base(
            _INSUFFICIENT_DATA, confidence="low",
            evidence_limitations="No instrument is attached to this Council Case for Sentinel-X to risk-score.",
        )
    inspection_id = _first(case.inspection_ids_json)
    try:
        row = run_risk_assessment(
            db, tenant_id, str(instrument_identity),
            inspection_id=int(inspection_id) if inspection_id is not None else None,
        )
    except ValueError as exc:
        return _base(_INSUFFICIENT_DATA, confidence="low", evidence_limitations=str(exc))
    result = to_dict(row)
    return _base(
        f"Clinical risk: {result['risk_level']} ({result['risk_score']}/100).",
        confidence="high" if result["risk_score"] >= 70 or result["risk_score"] <= 20 else "moderate",
        evidence_used={"risk_categories": result.get("risk_categories"), "score_breakdown": result.get("score_breakdown")},
        significance=result.get("reasoning_narrative", ""),
        recommended_action="Escalate for supervisor review." if result["risk_level"] in ("high", "critical") else "Continue standard monitoring.",
        urgency="urgent" if result["risk_level"] in ("high", "critical") else "routine",
        human_role_required=APPROVER_SPD_MANAGER if result["risk_level"] in ("high", "critical") else APPROVER_SUPERVISOR,
    )


def _assess_apollo(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.apollo_capa_engine_service import capa_engine_summary

    summary = capa_engine_summary(db, tenant_id)
    return _base(
        f"{summary['total_open_or_active']} open/active CAPA(s); {summary['pending_suggestion_count']} pending suggestion(s).",
        confidence="moderate",
        evidence_used={"lifecycle_counts": summary["lifecycle_counts"], "open_complaint_count": summary["open_complaint_count"]},
        significance="Quality/CAPA backlog may be relevant to this case." if summary["total_open_or_active"] else "No open CAPA backlog pressure identified.",
        recommended_action="Consider a CAPA draft if this case reflects a recurring pattern." if summary["pending_suggestion_count"] else "No new CAPA indicated.",
        urgency="routine",
    )


def _assess_athena(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.athena_search_service import organizational_search

    query = case.source_event or str(_first(case.instrument_ids_json) or case.case_type)
    result = organizational_search(db, tenant_id, query)
    knowledge_hits = len(result.get("knowledge_articles", []))
    playbook_hits = len(result.get("playbooks", []))
    return _base(
        f"Institutional knowledge search found {knowledge_hits} related article(s) and {playbook_hits} related playbook(s).",
        confidence="moderate" if (knowledge_hits or playbook_hits) else "low",
        evidence_used={"query": query, "knowledge_articles": result.get("knowledge_articles", [])[:5], "playbooks": result.get("playbooks", [])[:5]},
        significance="Prior institutional guidance may apply." if (knowledge_hits or playbook_hits) else "No directly related institutional guidance found.",
        recommended_action="Review linked institutional knowledge before finalizing disposition." if knowledge_hits else "",
        urgency="routine",
    )


def _assess_pulse(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.pulse_command_center_service import pulse_command_center

    summary = pulse_command_center(db, tenant_id)
    supervisor_backlog = summary["supervisor_queue"]["backlog"]
    repair_open = summary["repair_queue"]["open"]
    return _base(
        f"Live operations: supervisor backlog {supervisor_backlog}, open repairs {repair_open}.",
        confidence="moderate",
        evidence_used={"supervisor_queue": summary["supervisor_queue"], "repair_queue": summary["repair_queue"], "inspection_queue": summary["inspection_queue"]},
        significance="Elevated operational load may affect response time." if supervisor_backlog > 5 else "Operational load is within normal range.",
        recommended_action="Consider staffing/workflow adjustment." if supervisor_backlog > 5 else "",
        urgency="urgent" if supervisor_backlog > 10 else "routine",
        human_role_required=APPROVER_SPD_MANAGER,
    )


def _assess_phoenix(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.phoenix_maturity_index_service import compute_platform_maturity_index

    maturity = compute_platform_maturity_index(db, tenant_id)
    return _base(
        f"Platform maturity overall score: {maturity['overall_score']}.",
        confidence="moderate",
        evidence_used={"scores": maturity["scores"]},
        significance="Reflects enterprise-wide improvement trajectory, not this case specifically.",
        recommended_action="",
        urgency="routine",
        human_role_required=APPROVER_DIRECTOR,
    )


def _assess_maestro(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.maestro_priority_engine_service import latest_priorities

    priorities = latest_priorities(db, tenant_id)
    instrument_identity = _first(case.instrument_ids_json)
    match = next((p for p in priorities if instrument_identity and str(instrument_identity) in p["subject"]), None)
    top = match or (priorities[0] if priorities else None)
    if top is None:
        return _base(
            _INSUFFICIENT_DATA, confidence="low",
            evidence_limitations="No current operational priority ranking is available for Maestro to reference.",
        )
    return _base(
        f"Ranked priority: {top['subject']} (#{top['rank']}, category {top['category']}).",
        confidence="moderate",
        evidence_used={"priority_score": top["priority_score"], "category": top["category"]},
        significance=top["rationale"],
        recommended_action="Coordinate with the operational priority already identified for this issue." if match else "",
        urgency="routine",
        human_role_required=APPROVER_SPD_MANAGER,
    )


def _assess_research_agent(db: Session, tenant_id: str, case: CouncilCase) -> dict:
    from app.services.horizon_research_portal_service import research_portal_summary

    summary = research_portal_summary(db)
    study_count = len(summary.get("research_studies", []))
    return _base(
        f"{study_count} active/published network research study(ies) available for reference.",
        confidence="low",
        evidence_used={"research_study_count": study_count, "published_knowledge_count": len(summary.get("published_knowledge", []))},
        significance="Network research context is read-only reference; it does not constitute site-specific evidence for this case.",
        recommended_action="Consider a research/pilot proposal if this case reveals a novel pattern." if case.case_type == "innovation_proposal" else "",
        urgency="routine",
        human_role_required=APPROVER_CLINICAL_QUALITY_GOVERNANCE,
    )


_ASSESSORS = {
    SPECIALIST_VERITAS: _assess_veritas,
    SPECIALIST_AEGIS: _assess_aegis,
    SPECIALIST_VULCAN: _assess_vulcan,
    SPECIALIST_SAGE: _assess_sage,
    SPECIALIST_SENTINELX: _assess_sentinelx,
    SPECIALIST_APOLLO: _assess_apollo,
    SPECIALIST_ATHENA: _assess_athena,
    SPECIALIST_PULSE: _assess_pulse,
    SPECIALIST_PHOENIX: _assess_phoenix,
    SPECIALIST_MAESTRO: _assess_maestro,
    SPECIALIST_RESEARCH_AGENT: _assess_research_agent,
}


def _to_dict(row: CouncilSpecialistAssessment) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "council_case_id": row.council_case_id,
        "specialist_key": row.specialist_key,
        "conclusion": row.conclusion,
        "confidence": row.confidence,
        "evidence_used": json.loads(row.evidence_used_json or "{}"),
        "evidence_limitations": row.evidence_limitations,
        "significance": row.significance,
        "recommended_action": row.recommended_action,
        "alternative_explanation": row.alternative_explanation,
        "urgency": row.urgency,
        "human_role_required": row.human_role_required,
        "is_revision": row.is_revision,
        "supersedes_assessment_id": row.supersedes_assessment_id,
    }


def submit_assessment(
    db: Session, tenant_id: str, council_case_id: int, specialist_key: str, fields: dict, *, is_revision: bool = False,
) -> CouncilSpecialistAssessment:
    """Persists one specialist assessment. Never updates a prior row --
    assessments are immutable once submitted."""
    supersedes_id = None
    if is_revision:
        prior = (
            db.query(CouncilSpecialistAssessment)
            .filter(
                CouncilSpecialistAssessment.tenant_id == tenant_id,
                CouncilSpecialistAssessment.council_case_id == council_case_id,
                CouncilSpecialistAssessment.specialist_key == specialist_key,
            )
            .order_by(CouncilSpecialistAssessment.created_at.desc())
            .first()
        )
        supersedes_id = prior.id if prior else None

    row = CouncilSpecialistAssessment(
        tenant_id=tenant_id,
        council_case_id=council_case_id,
        specialist_key=specialist_key,
        conclusion=fields["conclusion"],
        confidence=fields.get("confidence", "moderate"),
        evidence_used_json=json.dumps(fields.get("evidence_used", {})),
        evidence_limitations=fields.get("evidence_limitations", ""),
        significance=fields.get("significance", ""),
        recommended_action=fields.get("recommended_action", ""),
        alternative_explanation=fields.get("alternative_explanation", ""),
        urgency=fields.get("urgency", "routine"),
        human_role_required=fields.get("human_role_required", APPROVER_SUPERVISOR),
        is_revision=is_revision,
        supersedes_assessment_id=supersedes_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_independent_assessments(db: Session, tenant_id: str, case: CouncilCase, specialists: list[str]) -> list[CouncilSpecialistAssessment]:
    """Runs each named specialist's resolver against its own real store
    and submits one fresh, independent assessment per specialist --
    resolvers never see each other's Council conclusions."""
    rows = []
    for specialist_key in specialists:
        resolver = _ASSESSORS.get(specialist_key)
        if resolver is None:
            continue
        fields = resolver(db, tenant_id, case)
        rows.append(submit_assessment(db, tenant_id, case.id, specialist_key, fields))
    return rows


def submit_revision(db: Session, tenant_id: str, case: CouncilCase, specialist_key: str, fields: dict) -> CouncilSpecialistAssessment:
    """A specialist revising its conclusion after seeing the rest of the
    Council -- the original assessment is preserved, never overwritten."""
    return submit_assessment(db, tenant_id, case.id, specialist_key, fields, is_revision=True)


def assessments_for_case(db: Session, tenant_id: str, council_case_id: int) -> list[dict]:
    rows = (
        db.query(CouncilSpecialistAssessment)
        .filter(CouncilSpecialistAssessment.tenant_id == tenant_id, CouncilSpecialistAssessment.council_case_id == council_case_id)
        .order_by(CouncilSpecialistAssessment.created_at.asc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def latest_assessments_for_case(db: Session, tenant_id: str, council_case_id: int) -> list[dict]:
    """One assessment per specialist -- the most recent (post-revision if
    any), for consensus/dissent/agreement-map computation."""
    all_rows = assessments_for_case(db, tenant_id, council_case_id)
    latest: dict[str, dict] = {}
    for row in all_rows:
        latest[row["specialist_key"]] = row
    return list(latest.values())
