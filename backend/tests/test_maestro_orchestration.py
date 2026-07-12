"""LumenAI AI Specialist — Project Maestro: Operational Orchestration &
Decision Intelligence tests.

Covers the 7 named scenarios from the sprint brief's Section 11
(orchestration; priority ranking; leadership recommendations; operational
health; decision journal; daily brief generation; specialist
coordination), plus a route smoke test. Maestro is a pure
read-and-synthesize layer over already-built specialists -- see
`app/models/maestro_orchestration.py` for the naming disambiguation from
Phase 22's `app.agents.orchestrator` and Nova's
`nova_orchestration_service.py`, neither of which this file touches.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.inspection_finding import InspectionFinding
from app.models.maestro_orchestration import (
    BRIEF_TYPES,
    DECISION_STATUS_PENDING,
    RECOMMENDATION_GENERATE_CAPA_DRAFT,
    RECOMMENDATION_SCHEDULE_COMPETENCY,
)
from app.models.or_connect import REPAIR_PENDING, RepairRequest
from app.models.patient_safety import ExecutiveRiskSignal
from app.models.sage_education import SageKnowledgeGap
from app.models.sentinelx_risk import SentinelXRiskAssessment
from app.models.vulcan_reliability import VulcanReliabilityAssessment
from app.services import (
    maestro_daily_brief_service,
    maestro_decision_journal_service,
    maestro_orchestration_service,
    maestro_priority_engine_service,
    maestro_recommendation_engine_service,
)
from app.services.maestro_health_index_service import compute_operational_health

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _seed_sentinelx_assessments(db, tenant_id: str) -> None:
    for identity, score in (("barcode:LOW1", 30.0), ("barcode:HIGH1", 85.0)):
        db.add(SentinelXRiskAssessment(
            tenant_id=tenant_id, instrument_identity=identity, anatomy_zone="jaw serration",
            facility_name="Main OR", risk_score=score, risk_level="high" if score > 50 else "low",
        ))
    db.commit()


def _seed_vulcan_equipment(db, tenant_id: str) -> None:
    db.add(VulcanReliabilityAssessment(
        tenant_id=tenant_id, instrument_identity="barcode:WORST1", instrument_family="kerrison rongeur",
        reliability_score=20.0, reliability_category="corrosion_concern", recommended_disposition="review",
    ))
    db.commit()


def _seed_sage_gap(db, tenant_id: str) -> None:
    db.add(SageKnowledgeGap(
        tenant_id=tenant_id, competency_domain="brushing_technique", scope_type="technician",
        scope_value="tech-1", occurrence_count=5, narrative="Recurring brushing technique gap observed.",
        status="open",
    ))
    db.commit()


def _seed_capa_pattern(db, tenant_id: str) -> list[int]:
    ids = []
    for _ in range(3):
        insp = models.Inspection(tenant_id=tenant_id, file_name="t.jpg", instrument_type="kerrison rongeur", created_at=datetime.now(timezone.utc))
        db.add(insp)
        db.commit()
        db.refresh(insp)
        f = InspectionFinding(tenant_id=tenant_id, inspection_id=insp.id, finding_type="rust", zone="jaw serration", severity_index=2)
        db.add(f)
        db.commit()
        ids.append(insp.id)
    return ids


def _seed_repair_backlog(db, tenant_id: str) -> None:
    db.add(RepairRequest(
        tenant_id=tenant_id, inspection_id=1, instrument_identity="barcode:REPAIR1", vendor_name="Acme Repair",
        repair_type="sharpening", status=REPAIR_PENDING, created_at=datetime.now(timezone.utc) - timedelta(days=20),
    ))
    db.commit()


def _seed_executive_risk(db, tenant_id: str) -> None:
    db.add(ExecutiveRiskSignal(
        tenant_id=tenant_id, event_source="vendor_registry", event_type="high_risk_vendor",
        risk_tier="critical", confidence_score=0.9, human_review_status="pending",
        association_reason="Vendor has an unresolved recall exposure.",
    ))
    db.commit()


def _seed_all(db, tenant_id: str) -> None:
    _seed_sentinelx_assessments(db, tenant_id)
    _seed_vulcan_equipment(db, tenant_id)
    _seed_sage_gap(db, tenant_id)
    _seed_capa_pattern(db, tenant_id)
    _seed_repair_backlog(db, tenant_id)
    _seed_executive_risk(db, tenant_id)


# ── 1. orchestration runs end-to-end from real specialist signals ────────

def test_orchestration_runs_end_to_end():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_all(db, tenant_id)
        result = maestro_orchestration_service.run_daily_orchestration(db, tenant_id)
        assert result["priority_item_count"] > 0
        assert result["recommendation_count"] > 0
        assert result["operational_health"]["human_review_required"] is True
        assert result["daily_brief"]["narrative"]
        assert result["human_review_required"] is True
    finally:
        db.close()


# ── 2. priority engine ranks categories by real signal strength ──────────

def test_priority_ranking_orders_by_score():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_sentinelx_assessments(db, tenant_id)
        _seed_vulcan_equipment(db, tenant_id)
        rows = maestro_priority_engine_service.compute_priorities(db, tenant_id)
        assert len(rows) >= 2
        scores = [r.priority_score for r in rows]
        assert scores == sorted(scores, reverse=True)
        ranks = [r.rank for r in rows]
        assert ranks == list(range(1, len(rows) + 1))
    finally:
        db.close()


# ── 3. leadership recommendations cite real evidence ──────────────────────

def test_leadership_recommendations_cite_evidence():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_sage_gap(db, tenant_id)
        _seed_capa_pattern(db, tenant_id)
        recommendations = maestro_recommendation_engine_service.generate_recommendations(db, tenant_id)
        assert recommendations
        for rec in recommendations:
            assert rec.rationale
            assert rec.evidence_json and rec.evidence_json != "{}"
            assert rec.human_review_required is True
        types = {r.recommendation_type for r in recommendations}
        assert RECOMMENDATION_SCHEDULE_COMPETENCY in types or RECOMMENDATION_GENERATE_CAPA_DRAFT in types
    finally:
        db.close()


# ── 4. operational health composes a real cross-specialist index ─────────

def test_operational_health_computes_composite():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_vulcan_equipment(db, tenant_id)
        snapshot = compute_operational_health(db, tenant_id)
        assert snapshot.equipment_score is not None
        assert snapshot.human_review_required is True
        breakdown = snapshot.breakdown_json
        assert breakdown and breakdown != "{}"
    finally:
        db.close()


# ── 5. decision journal requires a real leader decision and advances status ──

def test_decision_journal_records_and_advances_status():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_sage_gap(db, tenant_id)
        recommendations = maestro_recommendation_engine_service.generate_recommendations(db, tenant_id)
        assert recommendations
        rec = recommendations[0]
        assert rec.status == DECISION_STATUS_PENDING

        raised = False
        try:
            maestro_decision_journal_service.record_decision(
                db, tenant_id, rec.id, leader_decision="", decided_by="manager@local.dev",
            )
        except ValueError:
            raised = True
        assert raised

        entry = maestro_decision_journal_service.record_decision(
            db, tenant_id, rec.id, leader_decision="Approved and assigned to SPD lead.",
            decided_by="manager@local.dev", decided_role="spd_manager", new_status="completed",
        )
        assert entry.leader_decision
        assert entry.evidence_json == rec.evidence_json

        db.refresh(rec)
        assert rec.status == "completed"
    finally:
        db.close()


# ── 6. daily brief generation produces a narrative per brief type ────────

def test_daily_brief_generation_produces_narrative_per_type():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_all(db, tenant_id)
        maestro_priority_engine_service.compute_priorities(db, tenant_id)
        for brief_type in BRIEF_TYPES:
            row = maestro_daily_brief_service.generate_brief(db, tenant_id, brief_type)
            assert row.narrative
            assert row.content_json and row.content_json != "{}"
    finally:
        db.close()


# ── 7. specialist coordination composes real, non-fabricated signals ─────

def test_specialist_coordination_composes_real_signals():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_all(db, tenant_id)
        rows = maestro_priority_engine_service.compute_priorities(db, tenant_id)
        specialists = {r.source_specialist for r in rows}
        assert specialists.issubset({
            "sentinelx", "sage", "vulcan", "capa_suggestion_service", "or_connect", "executive_risk_signal",
        })
        assert specialists  # never empty when real data exists across categories

        workspace = maestro_orchestration_service.leadership_workspace_summary(db, tenant_id)
        assert "enterprise_status" in workspace
        assert "shift_readiness" in workspace
        assert workspace["human_review_required"] is True
    finally:
        db.close()


# ── Route smoke test ──────────────────────────────────────────────────────

def test_orchestration_and_workspace_routes():
    tenant_id = uid("maestro-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        _seed_all(db, tenant_id)
    finally:
        db.close()

    r = client.post("/api/maestro/run", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert body["priority_item_count"] > 0
    assert body["human_review_required"] is True

    r2 = client.get("/api/maestro/workspace", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert "top_priorities" in r2.json()

    r3 = client.get("/api/maestro/priorities", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200

    r4 = client.get("/api/maestro/recommendations", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200

    r5 = client.get("/api/maestro/timeline", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r5.status_code == 200
    assert "horizons" in r5.json()
