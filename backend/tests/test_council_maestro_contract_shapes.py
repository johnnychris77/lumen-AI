"""Contract tests: pin the exact dict/list shapes that Council and Maestro
depend on from other specialists' real services.

Council (`council_specialist_assessment_service.py`) and Maestro
(`maestro_priority_engine_service.py`) both compose ~10 other specialists'
already-built services by reading specific keys out of plain dicts with no
schema enforcement anywhere in between. That coupling is real and
intentional (reuse over duplication), but it means a rename or shape
change in any of those specialist services can silently break Council or
Maestro at runtime with nothing catching it until a user hits the code
path.

This file is deliberately narrow: for each specialist function Council or
Maestro's own code accesses by key/attribute, assert those exact keys
exist with the expected type, using real seeded data (not mocks). If one
of these fails, the break is in the *specialist* module, not in Council or
Maestro -- but Council/Maestro's own code needs to be updated in lockstep.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from app.db import models
from app.db.session import SessionLocal
from app.models.inspection_finding import InspectionFinding
from app.models.sage_education import SageKnowledgeGap
from app.models.sentinelx_risk import SentinelXRiskAssessment
from app.models.vulcan_reliability import VulcanReliabilityAssessment

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _mk_inspection(db, tenant_id, *, barcode, instrument_type="kerrison rongeur"):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="t.jpg", instrument_type=instrument_type, instrument_barcode=barcode,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mk_finding(db, tenant_id, inspection_id, *, finding_type="corrosion", zone="jaw", severity_index=2):
    row = InspectionFinding(tenant_id=tenant_id, inspection_id=inspection_id, finding_type=finding_type, zone=zone, severity_index=severity_index)
    db.add(row)
    db.commit()
    return row


# ── Vulcan: vulcan_reliability_agent_service.to_dict ──────────────────────
# Consumed by: council_specialist_assessment_service._assess_vulcan,
# maestro_priority_engine_service._highest_risk_equipment (via row attributes).

def test_vulcan_reliability_to_dict_shape():
    from app.services.vulcan_reliability_agent_service import run_reliability_assessment, to_dict

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        row = run_reliability_assessment(db, tenant_id, uid("barcode"), instrument_type="kerrison rongeur")
        result = to_dict(row)
        for key in ("reliability_score", "reliability_category", "recommended_disposition", "confidence", "probable_causes"):
            assert key in result, f"vulcan to_dict missing '{key}'"
        assert isinstance(result["probable_causes"], list)
        if result["probable_causes"]:
            assert "probable_cause" in result["probable_causes"][0]
    finally:
        db.close()


# ── Veritas: veritas_evidence_agent_service.to_dict ───────────────────────
# Consumed by: council_specialist_assessment_service._assess_veritas.

def test_veritas_evidence_to_dict_shape():
    from app.services.veritas_evidence_agent_service import run_evidence_assessment, to_dict

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        insp = _mk_inspection(db, tenant_id, barcode=uid("BC"))
        row = run_evidence_assessment(db, tenant_id, insp.id)
        result = to_dict(row)
        for key in ("readiness_score", "readiness_category", "coverage_status", "image_quality_status", "match_classification", "recommended_gate", "limitations"):
            assert key in result, f"veritas to_dict missing '{key}'"
        assert isinstance(result["limitations"], list)
    finally:
        db.close()


# ── Sentinel-X: sentinelx_risk_agent_service.to_dict ──────────────────────
# Consumed by: council_specialist_assessment_service._assess_sentinelx.

def test_sentinelx_risk_to_dict_shape():
    from app.services.sentinelx_risk_agent_service import run_risk_assessment, to_dict

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        insp = _mk_inspection(db, tenant_id, barcode=uid("BC"))
        _mk_finding(db, tenant_id, insp.id)
        row = run_risk_assessment(db, tenant_id, f"barcode:{insp.instrument_barcode}", instrument_type="kerrison rongeur")
        result = to_dict(row)
        for key in ("risk_score", "risk_level", "risk_categories", "score_breakdown", "reasoning_narrative", "confidence"):
            assert key in result, f"sentinelx to_dict missing '{key}'"
    finally:
        db.close()


# ── Sage: sage_knowledge_gap_service.list_gaps ────────────────────────────
# Consumed by: council_specialist_assessment_service._assess_sage,
# maestro_priority_engine_service._highest_risk_technician_education_need.

def test_sage_list_gaps_shape():
    from app.services.sage_knowledge_gap_service import list_gaps

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        db.add(SageKnowledgeGap(
            tenant_id=tenant_id, competency_domain="brushing_technique", scope_type="technician",
            scope_value="tech-1", occurrence_count=5, narrative="Recurring gap.", status="open",
        ))
        db.commit()
        gaps = list_gaps(db, tenant_id, status="open")
        assert gaps
        for key in ("occurrence_count", "competency_domain", "scope_value", "scope_type", "narrative", "recommended_education", "confidence"):
            assert key in gaps[0], f"sage list_gaps item missing '{key}'"
    finally:
        db.close()


# ── Apollo: apollo_capa_engine_service.capa_engine_summary ────────────────
# Consumed by: council_specialist_assessment_service._assess_apollo.

def test_apollo_capa_engine_summary_shape():
    from app.services.apollo_capa_engine_service import capa_engine_summary

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        result = capa_engine_summary(db, tenant_id)
        for key in ("lifecycle_counts", "total_open_or_active", "pending_suggestions", "pending_suggestion_count", "open_complaint_count", "human_review_required"):
            assert key in result, f"apollo capa_engine_summary missing '{key}'"
    finally:
        db.close()


# ── Athena: athena_search_service.organizational_search ───────────────────
# Consumed by: council_specialist_assessment_service._assess_athena.

def test_athena_organizational_search_shape():
    from app.services.athena_search_service import organizational_search

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        result = organizational_search(db, tenant_id, "kerrison")
        for key in ("query", "knowledge_articles", "playbooks", "human_review_required"):
            assert key in result, f"athena organizational_search missing '{key}'"
    finally:
        db.close()


# ── Pulse: pulse_command_center_service.pulse_command_center ─────────────
# Consumed by: council_specialist_assessment_service._assess_pulse.

def test_pulse_command_center_shape():
    from app.services.pulse_command_center_service import pulse_command_center

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        result = pulse_command_center(db, tenant_id)
        assert "supervisor_queue" in result and "backlog" in result["supervisor_queue"]
        assert "repair_queue" in result and "open" in result["repair_queue"]
        assert "inspection_queue" in result
    finally:
        db.close()


# ── Phoenix: phoenix_maturity_index_service.compute_platform_maturity_index ──
# Consumed by: council_specialist_assessment_service._assess_phoenix,
# maestro_health_index_service.compute_operational_health.

def test_phoenix_maturity_index_shape():
    from app.services.phoenix_maturity_index_service import compute_platform_maturity_index

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        result = compute_platform_maturity_index(db, tenant_id)
        assert "scores" in result and isinstance(result["scores"], dict)
        assert "overall_score" in result
        assert "id" in result  # maestro_health_index_service traces back to this id
        for key in ("quality_score", "workflow_score", "education_score", "digital_twins_score", "knowledge_score", "executive_intelligence_score"):
            assert key in result["scores"], f"phoenix scores missing '{key}'"
    finally:
        db.close()


# ── Sentinel-X aggregates: supervisor_workspace_summary / risk_dashboard_summary ──
# Consumed by: maestro_priority_engine_service (4 resolvers).

def test_sentinelx_supervisor_workspace_summary_shape():
    from app.services.sentinelx_supervisor_workspace_service import supervisor_workspace_summary

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        db.add(SentinelXRiskAssessment(tenant_id=tenant_id, instrument_identity="barcode:X1", risk_score=80.0, risk_level="high"))
        db.commit()
        result = supervisor_workspace_summary(db, tenant_id, limit=1)
        for key in ("highest_risk_instruments", "highest_risk_inspections", "pending_reviews"):
            assert key in result, f"supervisor_workspace_summary missing '{key}'"
        assert result["highest_risk_instruments"]
        assert "instrument_identity" in result["highest_risk_instruments"][0]
        assert "average_risk_score" in result["highest_risk_instruments"][0]
        assert "assessment_count" in result["highest_risk_instruments"][0]
    finally:
        db.close()


def test_sentinelx_risk_dashboard_summary_shape():
    from app.services.sentinelx_dashboard_service import risk_dashboard_summary

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        db.add(SentinelXRiskAssessment(tenant_id=tenant_id, instrument_identity="barcode:X1", facility_name="Main OR", risk_score=80.0, risk_level="high"))
        db.commit()
        result = risk_dashboard_summary(db, tenant_id)
        for key in ("workflow_risk", "facility_risk", "enterprise_risk"):
            assert key in result, f"risk_dashboard_summary missing '{key}'"
        assert "process_variation_flagged_count" in result["workflow_risk"]
        assert result["facility_risk"]
        assert "key" in result["facility_risk"][0] and "average_risk_score" in result["facility_risk"][0] and "count" in result["facility_risk"][0]
    finally:
        db.close()


# ── Vulcan aggregate: VulcanReliabilityAssessment row attributes ──────────
# Consumed directly (as ORM attributes, not to_dict) by
# maestro_priority_engine_service._highest_risk_equipment.

def test_vulcan_reliability_assessment_row_attributes():
    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        row = VulcanReliabilityAssessment(
            tenant_id=tenant_id, instrument_identity="barcode:X1", reliability_score=50.0,
            reliability_category="monitor", recommended_disposition="review",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        for attr in ("instrument_identity", "reliability_score", "reliability_category", "instrument_family"):
            assert hasattr(row, attr), f"VulcanReliabilityAssessment missing attribute '{attr}'"
    finally:
        db.close()


# ── Maestro: maestro_priority_engine_service.to_dict / latest_priorities ──
# Consumed by: council_specialist_assessment_service._assess_maestro.

def test_maestro_priority_item_dict_shape():
    from app.services import maestro_priority_engine_service

    tenant_id = uid("contract-t")
    db = SessionLocal()
    try:
        db.add(SentinelXRiskAssessment(tenant_id=tenant_id, instrument_identity="barcode:X1", risk_score=80.0, risk_level="high"))
        db.commit()
        rows = maestro_priority_engine_service.compute_priorities(db, tenant_id)
        assert rows
        item = maestro_priority_engine_service.to_dict(rows[0])
        for key in ("subject", "priority_score", "rank", "category", "rationale"):
            assert key in item, f"maestro priority item to_dict missing '{key}'"
    finally:
        db.close()
