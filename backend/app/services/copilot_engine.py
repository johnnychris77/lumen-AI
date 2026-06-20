"""P9: Autonomous Inspection Copilot — core engine."""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.copilot import (
    CopilotRecommendation,
    EscalationEvent,
    InspectionProtocol,
    InspectionSession,
    InspectionStep,
)
from app.schemas.copilot import (
    CopilotDashboard,
    CopilotRecommendationResult,
    EscalationEventResult,
    InspectionSessionResult,
    InspectionStepResult,
    ProtocolResult,
)

# ── Protocol templates ───────────────────────────────────────────────────────

PROTOCOL_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "scissors": [
        {"step_number": 1, "step_type": "visual", "step_title": "Visual Surface Inspection", "step_instructions": "Inspect all surfaces under magnification for visible contamination, discoloration, or debris. Focus on box locks and serrations."},
        {"step_number": 2, "step_type": "contamination", "step_title": "Stain & Residue Check", "step_instructions": "Check blade edges and box lock for blood, bone, or tissue residue. Use lighted magnifier."},
        {"step_number": 3, "step_type": "structural", "step_title": "Structural Integrity", "step_instructions": "Open and close scissors 3 times. Check for smooth action, alignment, and tension. Inspect for cracks or corrosion at hinge."},
        {"step_number": 4, "step_type": "functional", "step_title": "Functional Test", "step_instructions": "Cut a single sheet of test gauze. Scissors must cut cleanly from tip to heel without tearing."},
        {"step_number": 5, "step_type": "documentation", "step_title": "Documentation & Release", "step_instructions": "Record all findings. Affix instrument tracking label. Mark pass/fail and route accordingly."},
    ],
    "forceps": [
        {"step_number": 1, "step_type": "visual", "step_title": "Visual Surface Inspection", "step_instructions": "Inspect jaw surfaces, serrations, and box lock under magnification for contamination or debris."},
        {"step_number": 2, "step_type": "contamination", "step_title": "Tissue & Blood Residue Check", "step_instructions": "Examine jaw serrations under bright light for bone chips, tissue fragments, or dried blood."},
        {"step_number": 3, "step_type": "structural", "step_title": "Jaw Alignment Check", "step_instructions": "Close forceps and hold to light. Jaws must meet evenly with no gaps. Check for bent tips."},
        {"step_number": 4, "step_type": "functional", "step_title": "Ratchet & Tension Test", "step_instructions": "Engage ratchet at each position. Check for smooth engagement without slipping. Test tension spring."},
        {"step_number": 5, "step_type": "documentation", "step_title": "Documentation & Release", "step_instructions": "Record findings. Apply tracking label. Route to appropriate sterile processing queue."},
    ],
    "retractor": [
        {"step_number": 1, "step_type": "visual", "step_title": "Frame Visual Inspection", "step_instructions": "Inspect frame, blades, and attachment points for contamination, cracks, or bent components."},
        {"step_number": 2, "step_type": "contamination", "step_title": "Deep Contamination Check", "step_instructions": "Inspect all crevices, attachment slots, and blade surfaces for residue. Use lighted probe if needed."},
        {"step_number": 3, "step_type": "structural", "step_title": "Mechanical Integrity", "step_instructions": "Test all articulating joints and blade-locking mechanisms. Check frame for cracks or deformation."},
        {"step_number": 4, "step_type": "documentation", "step_title": "Documentation & Release", "step_instructions": "Record all findings with photographic documentation if deficiencies found. Route appropriately."},
    ],
    "scope": [
        {"step_number": 1, "step_type": "visual", "step_title": "External Surface Check", "step_instructions": "Inspect scope body, insertion tube, and connectors for damage, scratches, or contamination."},
        {"step_number": 2, "step_type": "structural", "step_title": "Bending Section Integrity", "step_instructions": "Slowly flex insertion tube through full range of motion. Check for kinks, deformation, or resistance."},
        {"step_number": 3, "step_type": "functional", "step_title": "Leak Test", "step_instructions": "Perform pressure leak test per manufacturer protocol. Submerge distal end and check for bubbles."},
        {"step_number": 4, "step_type": "contamination", "step_title": "Channel Patency Check", "step_instructions": "Flush all channels and confirm flow. Check for blockage or discoloration in effluent."},
        {"step_number": 5, "step_type": "documentation", "step_title": "Documentation & Release", "step_instructions": "Complete scope log. Record leak test result. Apply tracking sticker and route to storage or sterilization."},
    ],
    "default": [
        {"step_number": 1, "step_type": "visual", "step_title": "Visual Surface Inspection", "step_instructions": "Inspect all surfaces under adequate lighting and magnification for visible contamination or damage."},
        {"step_number": 2, "step_type": "contamination", "step_title": "Contamination Assessment", "step_instructions": "Check all surfaces and crevices for blood, bone, tissue residue, or other organic material."},
        {"step_number": 3, "step_type": "structural", "step_title": "Structural Integrity Check", "step_instructions": "Inspect for cracks, corrosion, deformation, or missing components. Test all moving parts."},
        {"step_number": 4, "step_type": "documentation", "step_title": "Documentation & Release", "step_instructions": "Record findings and route instrument to appropriate workflow queue."},
    ],
}

SEVERITY_RISK: dict[str, str] = {
    "none": "low",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
}

SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]

FINDING_RECOMMENDATIONS: dict[str, tuple[str, str, float]] = {
    "blood": ("warning", "Blood contamination detected. Instrument requires re-decontamination before proceeding. Document per infection control protocol.", 0.92),
    "bone": ("warning", "Bone chip residue identified. Manual brushing of serrations required. Do not proceed to sterilization.", 0.88),
    "tissue": ("warning", "Soft tissue residue present. Return to decontamination. Soak in enzymatic solution for 10 minutes.", 0.90),
    "crack": ("escalate", "Structural crack detected. Remove instrument from service immediately. Tag out-of-service and notify supervisor.", 0.95),
    "corrosion": ("escalate", "Active corrosion identified. Instrument must be quarantined. Assess for replacement per AAMI ST79 guidance.", 0.87),
    "insulation": ("escalate", "Insulation breach detected on powered instrument. Immediate removal from service required. Patient safety risk.", 0.98),
    "residue": ("action", "General residue identified. Additional cleaning step required. Re-inspect after cleaning.", 0.82),
    "baseline": ("action", "Instrument below baseline quality threshold. Additional inspection steps recommended.", 0.75),
}

# Findings that trigger escalation
ESCALATION_FINDINGS = {"crack", "corrosion", "insulation"}
ESCALATION_SEVERITIES = {"high", "critical"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed(s: str) -> random.Random:
    seed = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(seed, 16))


def _infer_instrument_category(instrument_name: str) -> str:
    name_lower = instrument_name.lower()
    if "scissor" in name_lower:
        return "scissors"
    if "forcep" in name_lower:
        return "forceps"
    if "retract" in name_lower:
        return "retractor"
    if "scope" in name_lower or "endoscope" in name_lower:
        return "scope"
    return "default"


def _fmt_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _session_to_result(
    session: InspectionSession,
    steps: list[InspectionStep],
    recommendations: list[CopilotRecommendation],
    data_source: str = "real",
) -> InspectionSessionResult:
    step_results = [
        InspectionStepResult(
            id=s.id,
            session_id=s.session_id,
            step_number=s.step_number,
            step_type=s.step_type,
            step_title=s.step_title,
            step_instructions=s.step_instructions,
            ai_recommendation=s.ai_recommendation,
            technician_response=s.technician_response,
            finding_category=s.finding_category,
            severity=s.severity,
            confidence=s.confidence,
            completed_at=_fmt_dt(s.completed_at),
            notes=s.notes,
        )
        for s in steps
    ]
    rec_results = [
        CopilotRecommendationResult(
            id=r.id,
            session_id=r.session_id,
            step_id=r.step_id,
            recommendation_type=r.recommendation_type,
            message=r.message,
            confidence=r.confidence,
            evidence=_parse_json_list(r.evidence),
            acted_on=r.acted_on,
            technician_decision=r.technician_decision,
            created_at=_fmt_dt(r.created_at) or "",
        )
        for r in recommendations
    ]
    return InspectionSessionResult(
        id=session.id,
        tenant_id=session.tenant_id,
        facility_id=session.facility_id,
        technician_id=session.technician_id,
        instrument_name=session.instrument_name,
        instrument_id=session.instrument_id,
        session_status=session.session_status,
        started_at=_fmt_dt(session.started_at) or "",
        completed_at=_fmt_dt(session.completed_at),
        total_steps=session.total_steps,
        completed_steps=session.completed_steps,
        copilot_mode=session.copilot_mode,
        risk_level=session.risk_level,
        session_notes=session.session_notes,
        escalation_reason=session.escalation_reason,
        steps=step_results,
        recommendations=rec_results,
        data_source=data_source,
    )


def _parse_json_list(val: str) -> list[dict]:
    try:
        parsed = json.loads(val or "[]")
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return []


def _worst_severity(severities: list[str]) -> str:
    best_idx = 0
    for sev in severities:
        idx = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else 0
        if idx > best_idx:
            best_idx = idx
    return SEVERITY_ORDER[best_idx]


# ── Engine functions ─────────────────────────────────────────────────────────

def start_inspection_session(
    tenant_id: str,
    facility_id: str,
    technician_id: str,
    instrument_name: str,
    instrument_id: str,
    copilot_mode: str,
    db: Session,
) -> InspectionSessionResult:
    """Create a new inspection session with steps from the matching protocol."""
    # Assess historical risk
    try:
        from app.models.cv_inference import CVInferenceRecord
        historical = (
            db.query(CVInferenceRecord)
            .filter(
                CVInferenceRecord.tenant_id == tenant_id,
                CVInferenceRecord.instrument_name == instrument_name,
            )
            .order_by(CVInferenceRecord.created_at.desc())
            .limit(10)
            .all()
        )
    except Exception:
        historical = []

    category = _infer_instrument_category(instrument_name)
    template_steps = PROTOCOL_TEMPLATES.get(category, PROTOCOL_TEMPLATES["default"])

    # Determine initial risk from history
    initial_risk = "low"
    if historical:
        avg_score = sum(r.overall_cleanliness_score for r in historical) / len(historical)
        if avg_score < 50:
            initial_risk = "high"
        elif avg_score < 75:
            initial_risk = "medium"

    session = InspectionSession(
        tenant_id=tenant_id,
        facility_id=facility_id,
        technician_id=technician_id,
        instrument_name=instrument_name,
        instrument_id=instrument_id,
        copilot_mode=copilot_mode,
        total_steps=len(template_steps),
        completed_steps=0,
        session_status="active",
        risk_level=initial_risk,
    )
    db.add(session)
    db.flush()

    steps: list[InspectionStep] = []
    for tpl in template_steps:
        step = InspectionStep(
            session_id=session.id,
            step_number=tpl["step_number"],
            step_type=tpl["step_type"],
            step_title=tpl["step_title"],
            step_instructions=tpl["step_instructions"],
            ai_recommendation=_initial_step_recommendation(tpl["step_type"], initial_risk),
        )
        db.add(step)
        steps.append(step)

    db.flush()

    # Generate initial recommendations based on history
    recommendations: list[CopilotRecommendation] = []
    if historical:
        low_scores = [r for r in historical if r.overall_cleanliness_score < 75]
        if low_scores:
            rec = CopilotRecommendation(
                session_id=session.id,
                step_id=None,
                recommendation_type="warning",
                message=f"Historical records show {len(low_scores)} of last {len(historical)} inspections below quality threshold. Heightened vigilance recommended.",
                confidence=0.85,
                evidence=json.dumps([{"source": "historical", "count": len(low_scores), "total": len(historical)}]),
            )
            db.add(rec)
            recommendations.append(rec)

    db.commit()
    db.refresh(session)
    for s in steps:
        db.refresh(s)
    for r in recommendations:
        db.refresh(r)

    return _session_to_result(session, steps, recommendations)


def _initial_step_recommendation(step_type: str, risk_level: str) -> str:
    base = {
        "visual": "Perform systematic visual scan under proper lighting.",
        "contamination": "Use magnification and adequate lighting to detect organic residue.",
        "structural": "Apply consistent pressure when testing moving components.",
        "functional": "Test all functions per manufacturer specifications.",
        "documentation": "Complete all required fields accurately before release.",
    }
    msg = base.get(step_type, "Follow facility SOP for this step.")
    if risk_level in ("high", "critical"):
        msg += " Note: this instrument has a history of quality issues — extra scrutiny required."
    return msg


def get_session(session_id: int, tenant_id: str, db: Session) -> InspectionSessionResult:
    session = db.query(InspectionSession).filter_by(id=session_id, tenant_id=tenant_id).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found.")
    steps = db.query(InspectionStep).filter_by(session_id=session_id).order_by(InspectionStep.step_number).all()
    recommendations = db.query(CopilotRecommendation).filter_by(session_id=session_id).all()
    return _session_to_result(session, steps, recommendations)


def respond_to_step(
    session_id: int,
    step_id: int,
    technician_response: str,
    finding_category: str,
    notes: str,
    tenant_id: str,
    db: Session,
) -> InspectionSessionResult:
    """Record technician's response to a step and trigger AI logic."""
    session = db.query(InspectionSession).filter_by(id=session_id, tenant_id=tenant_id).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found.")

    step = db.query(InspectionStep).filter_by(id=step_id, session_id=session_id).first()
    if not step:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Step not found.")

    # Determine severity from finding
    severity = "none"
    if finding_category:
        if finding_category in ("crack", "corrosion", "insulation"):
            severity = "critical"
        elif finding_category in ("blood", "bone", "tissue"):
            severity = "high"
        elif finding_category in ("residue", "baseline"):
            severity = "medium"
        else:
            severity = "low"

    if technician_response == "fail" and severity == "none":
        severity = "medium"
    elif technician_response == "escalate":
        severity = "critical"

    step.technician_response = technician_response
    step.finding_category = finding_category
    step.severity = severity
    step.notes = notes
    step.completed_at = datetime.now(timezone.utc)

    if finding_category or technician_response in ("fail", "escalate"):
        rec_type, msg, conf = generate_ai_recommendation(session, step, finding_category, db)
        step.ai_recommendation = msg
        step.confidence = conf
        rec = CopilotRecommendation(
            session_id=session_id,
            step_id=step_id,
            recommendation_type=rec_type,
            message=msg,
            confidence=conf,
            evidence=json.dumps([{"trigger": finding_category or technician_response, "step": step.step_number}]),
        )
        db.add(rec)

        # Create escalation if needed
        if rec_type == "escalate" or severity in ESCALATION_SEVERITIES or finding_category in ESCALATION_FINDINGS:
            escalation_type = _determine_escalation_type(finding_category, technician_response)
            esc = EscalationEvent(
                session_id=session_id,
                tenant_id=tenant_id,
                escalation_type=escalation_type,
                severity=severity,
                description=f"Escalation triggered at step {step.step_number} ({step.step_title}): {msg}",
                auto_generated=True,
            )
            db.add(esc)
            session.session_status = "escalated"
            session.escalation_reason = f"Step {step.step_number}: {finding_category or technician_response}"

    # Update session risk_level (worst severity across all completed steps)
    all_steps = db.query(InspectionStep).filter_by(session_id=session_id).all()
    severities = [s.severity for s in all_steps if s.severity and s.severity != "none"]
    if severities:
        worst = _worst_severity(severities)
        session.risk_level = SEVERITY_RISK.get(worst, "low")

    # Update completed_steps
    completed = sum(1 for s in all_steps if s.technician_response)
    session.completed_steps = completed

    # Auto-complete if all steps done
    if completed >= session.total_steps and session.session_status == "active":
        session.session_status = "completed"
        session.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)

    steps = db.query(InspectionStep).filter_by(session_id=session_id).order_by(InspectionStep.step_number).all()
    recommendations = db.query(CopilotRecommendation).filter_by(session_id=session_id).all()
    return _session_to_result(session, steps, recommendations)


def generate_ai_recommendation(
    session: InspectionSession,
    step: InspectionStep,
    finding_category: str,
    db: Session,
) -> tuple[str, str, float]:
    """Returns (recommendation_type, message, confidence)."""
    if finding_category and finding_category in FINDING_RECOMMENDATIONS:
        return FINDING_RECOMMENDATIONS[finding_category]

    # Generic approve if no specific finding
    rng = _seed(f"{session.tenant_id}-{session.instrument_name}-{step.step_number}")
    confidence = round(rng.uniform(0.70, 0.95), 2)
    return ("approve", "Step completed within normal parameters. No significant findings detected.", confidence)


def _determine_escalation_type(finding_category: str, technician_response: str) -> str:
    mapping = {
        "crack": "structural",
        "corrosion": "structural",
        "insulation": "structural",
        "blood": "contamination",
        "bone": "contamination",
        "tissue": "contamination",
        "residue": "contamination",
    }
    if finding_category in mapping:
        return mapping[finding_category]
    if technician_response == "escalate":
        return "protocol_deviation"
    return "contamination"


def complete_session(session_id: int, tenant_id: str, db: Session) -> InspectionSessionResult:
    """Manually mark a session as completed."""
    session = db.query(InspectionSession).filter_by(id=session_id, tenant_id=tenant_id).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.session_status not in ("completed", "escalated"):
        session.session_status = "completed"
        session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    steps = db.query(InspectionStep).filter_by(session_id=session_id).order_by(InspectionStep.step_number).all()
    recommendations = db.query(CopilotRecommendation).filter_by(session_id=session_id).all()
    return _session_to_result(session, steps, recommendations)


def get_active_sessions(tenant_id: str, facility_id: str, db: Session) -> list[InspectionSessionResult]:
    q = db.query(InspectionSession).filter(
        InspectionSession.tenant_id == tenant_id,
        InspectionSession.session_status == "active",
    )
    if facility_id:
        q = q.filter(InspectionSession.facility_id == facility_id)
    sessions = q.all()
    results = []
    for session in sessions:
        steps = db.query(InspectionStep).filter_by(session_id=session.id).order_by(InspectionStep.step_number).all()
        recs = db.query(CopilotRecommendation).filter_by(session_id=session.id).all()
        results.append(_session_to_result(session, steps, recs))
    return results


def get_escalations(tenant_id: str, db: Session) -> list[EscalationEventResult]:
    events = (
        db.query(EscalationEvent)
        .filter_by(tenant_id=tenant_id, resolved=False)
        .order_by(EscalationEvent.created_at.desc())
        .all()
    )
    return [_esc_to_result(e) for e in events]


def _esc_to_result(e: EscalationEvent) -> EscalationEventResult:
    return EscalationEventResult(
        id=e.id,
        session_id=e.session_id,
        tenant_id=e.tenant_id,
        escalation_type=e.escalation_type,
        severity=e.severity,
        description=e.description,
        auto_generated=e.auto_generated,
        notified_supervisor=e.notified_supervisor,
        resolved=e.resolved,
        resolved_by=e.resolved_by,
        resolved_at=_fmt_dt(e.resolved_at),
        created_at=_fmt_dt(e.created_at) or "",
    )


def resolve_escalation(
    escalation_id: int,
    resolved_by: str,
    notes: str,
    tenant_id: str,
    db: Session,
) -> EscalationEventResult:
    esc = db.query(EscalationEvent).filter_by(id=escalation_id, tenant_id=tenant_id).first()
    if not esc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Escalation not found.")
    esc.resolved = True
    esc.resolved_by = resolved_by
    esc.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(esc)
    return _esc_to_result(esc)


def compute_copilot_dashboard(tenant_id: str, facility_id: str, db: Session) -> CopilotDashboard:
    """Aggregate session stats. Falls back to seeded mock when DB has no data."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    q_base = db.query(InspectionSession).filter(InspectionSession.tenant_id == tenant_id)
    if facility_id:
        q_base = q_base.filter(InspectionSession.facility_id == facility_id)

    all_sessions = q_base.all()

    if not all_sessions:
        return _mock_dashboard(tenant_id, facility_id)

    data_source = "real"
    active = sum(1 for s in all_sessions if s.session_status == "active")
    completed_today = sum(
        1 for s in all_sessions
        if s.session_status in ("completed", "escalated")
        and s.completed_at and s.completed_at.replace(tzinfo=timezone.utc) >= today_start
    )

    escs = db.query(EscalationEvent).filter(EscalationEvent.tenant_id == tenant_id)
    esc_open = escs.filter_by(resolved=False).count()
    esc_resolved = escs.filter_by(resolved=True).count()

    # Avg duration
    durations = []
    for s in all_sessions:
        if s.completed_at and s.started_at:
            start = s.started_at.replace(tzinfo=timezone.utc) if s.started_at.tzinfo is None else s.started_at
            end = s.completed_at.replace(tzinfo=timezone.utc) if s.completed_at.tzinfo is None else s.completed_at
            diff = (end - start).total_seconds() / 60
            durations.append(diff)
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

    # Pass rate
    all_steps = db.query(InspectionStep).filter(
        InspectionStep.session_id.in_([s.id for s in all_sessions])
    ).all()
    responded = [s for s in all_steps if s.technician_response]
    passed = [s for s in responded if s.technician_response == "pass"]
    pass_rate = round(len(passed) / len(responded) * 100, 1) if responded else 0.0

    # High risk instruments
    high_risk = list({s.instrument_name for s in all_sessions if s.risk_level in ("high", "critical")})

    # Top findings
    finding_counts: dict[str, int] = {}
    for step in responded:
        if step.finding_category:
            finding_counts[step.finding_category] = finding_counts.get(step.finding_category, 0) + 1
    total_findings = sum(finding_counts.values()) or 1
    top_findings = sorted(
        [{"category": k, "count": v, "pct": round(v / total_findings * 100, 1)} for k, v in finding_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    # Protocol compliance
    compliance = round(len(passed) / max(len(responded), 1) * 100, 1)

    # Technician performance
    tech_map: dict[str, dict] = {}
    for s in all_sessions:
        t = s.technician_id
        if t not in tech_map:
            tech_map[t] = {"sessions": 0, "pass_steps": 0, "total_steps": 0}
        tech_map[t]["sessions"] += 1
    for step in responded:
        # find session
        sess = next((s for s in all_sessions if s.id == step.session_id), None)
        if sess and sess.technician_id in tech_map:
            tech_map[sess.technician_id]["total_steps"] += 1
            if step.technician_response == "pass":
                tech_map[sess.technician_id]["pass_steps"] += 1
    tech_perf = [
        {
            "technician_id": t,
            "sessions": v["sessions"],
            "pass_rate": round(v["pass_steps"] / max(v["total_steps"], 1) * 100, 1),
        }
        for t, v in tech_map.items()
    ]

    return CopilotDashboard(
        tenant_id=tenant_id,
        facility_id=facility_id,
        generated_at=now.isoformat(),
        data_source=data_source,
        active_sessions=active,
        completed_today=completed_today,
        escalations_open=esc_open,
        escalations_resolved=esc_resolved,
        avg_session_duration_minutes=avg_duration,
        pass_rate_pct=pass_rate,
        high_risk_instruments=high_risk,
        top_finding_categories=top_findings,
        protocol_compliance_pct=compliance,
        technician_performance=tech_perf,
    )


def _mock_dashboard(tenant_id: str, facility_id: str) -> CopilotDashboard:
    rng = _seed(f"dashboard-{tenant_id}-{facility_id}")
    now = datetime.now(timezone.utc)
    return CopilotDashboard(
        tenant_id=tenant_id,
        facility_id=facility_id,
        generated_at=now.isoformat(),
        data_source="mock",
        active_sessions=rng.randint(2, 8),
        completed_today=rng.randint(10, 40),
        escalations_open=rng.randint(0, 5),
        escalations_resolved=rng.randint(5, 20),
        avg_session_duration_minutes=round(rng.uniform(8.0, 25.0), 1),
        pass_rate_pct=round(rng.uniform(78.0, 96.0), 1),
        high_risk_instruments=rng.sample(
            ["Metzenbaum Scissors", "DeBakey Forceps", "Bookwalter Retractor", "Laparoscope", "Needle Holder"],
            k=rng.randint(1, 3),
        ),
        top_finding_categories=[
            {"category": "residue", "count": rng.randint(5, 20), "pct": round(rng.uniform(30, 50), 1)},
            {"category": "blood", "count": rng.randint(2, 10), "pct": round(rng.uniform(15, 30), 1)},
            {"category": "bone", "count": rng.randint(1, 5), "pct": round(rng.uniform(5, 15), 1)},
        ],
        protocol_compliance_pct=round(rng.uniform(85.0, 98.0), 1),
        technician_performance=[
            {"technician_id": "tech-001", "sessions": rng.randint(5, 20), "pass_rate": round(rng.uniform(80, 98), 1)},
            {"technician_id": "tech-002", "sessions": rng.randint(3, 15), "pass_rate": round(rng.uniform(75, 95), 1)},
        ],
    )


def get_protocols(tenant_id: str, db: Session) -> list[ProtocolResult]:
    """Return DB protocols + built-in templates."""
    db_protocols = db.query(InspectionProtocol).filter_by(tenant_id=tenant_id, is_active=True).all()
    results: list[ProtocolResult] = [
        ProtocolResult(
            id=p.id,
            tenant_id=p.tenant_id,
            protocol_name=p.protocol_name,
            instrument_category=p.instrument_category,
            steps=_parse_json_list(p.steps_json),
            is_active=p.is_active,
            version=p.version,
            created_by=p.created_by,
        )
        for p in db_protocols
    ]

    # Synthetic IDs for built-in templates
    synthetic_id_base = 10000
    for idx, (category, steps) in enumerate(PROTOCOL_TEMPLATES.items()):
        results.append(
            ProtocolResult(
                id=synthetic_id_base + idx,
                tenant_id="system",
                protocol_name=f"Standard {category.title()} Inspection Protocol",
                instrument_category=category,
                steps=steps,
                is_active=True,
                version=1,
                created_by="system",
            )
        )
    return results
