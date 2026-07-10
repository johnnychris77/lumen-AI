"""v4.6 — LumenAI OS: Project Vanguard — Healthcare Executive
Intelligence & Strategic Decision Platform tests.

Covers: executive dashboards, board reports, financial models, AI
advisor, benchmarking, strategic planning, and role permissions.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.enterprise_hierarchy import EnterpriseFacility
from app.models.vanguard_intelligence import BENCHMARK_TYPES, BOARD_PACKET_TYPES, SCORECARD_AUDIENCES
from app.services import (
    catalyst_query_engine,
    or_connect_service,
    vanguard_ai_advisor_service,
    vanguard_benchmarking_service,
    vanguard_board_reporting_service,
    vanguard_executive_intelligence_service,
    vanguard_financial_service,
    vanguard_operational_service,
    vanguard_scorecard_service,
    vanguard_strategy_service,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _make_facility(tenant_id: str, *, system_id: str, market_id: str = "market-1") -> None:
    db = SessionLocal()
    try:
        db.add(EnterpriseFacility(
            facility_id=f"fac-{tenant_id}", facility_name="Test Facility", region_id="region-1",
            market_id=market_id, system_id=system_id, tenant_id=tenant_id,
        ))
        db.commit()
    finally:
        db.close()


def _make_case(tenant_id: str, *, service_line: str = "orthopedics", hours_from_now: float = 48) -> int:
    db = SessionLocal()
    try:
        case = or_connect_service.create_case(
            db, tenant_id, procedure="Total Knee Replacement",
            scheduled_start=datetime.now(timezone.utc) + timedelta(hours=hours_from_now),
            service_line=service_line, surgeon="Dr. Test", facility_name="Main Hospital",
        )
        return case.id
    finally:
        db.close()


# ── 1. Executive dashboards ──────────────────────────────────────────────────

def test_executive_intelligence_center_returns_eight_dimensions():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        result = vanguard_executive_intelligence_service.executive_intelligence_center(db, tenant_id)
    finally:
        db.close()
    for key in ["enterprise_readiness", "surgical_readiness", "spd_quality", "financial_impact", "capacity", "enterprise_risk", "ai_health", "knowledge_growth"]:
        assert key in result
    assert result["human_review_required"] is True


def test_scorecard_generation_for_all_audiences():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        for audience in SCORECARD_AUDIENCES:
            result = vanguard_scorecard_service.generate_scorecard(db, tenant_id, audience)
            assert result["audience"] == audience
            assert result["kpis"]
    finally:
        db.close()


def test_scorecard_unknown_audience_rejected():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        try:
            vanguard_scorecard_service.generate_scorecard(db, tenant_id, "not_a_real_audience")
            assert False, "expected UnknownScorecardAudienceError"
        except vanguard_scorecard_service.UnknownScorecardAudienceError:
            pass
    finally:
        db.close()


# ── 2. Board reports ─────────────────────────────────────────────────────────

def test_generate_board_packet_for_each_type_without_facility():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        for packet_type in BOARD_PACKET_TYPES:
            packet = vanguard_board_reporting_service.generate_board_packet(db, tenant_id, packet_type)
            assert packet["packet_type"] == packet_type
            assert packet["content"]["source"] == "vanguard_executive_snapshot"
    finally:
        db.close()


def test_generate_board_packet_with_facility_uses_atlas_report():
    tenant_id = uid("vanguard-tenant")
    system_id = uid("system")
    _make_facility(tenant_id, system_id=system_id)
    db = SessionLocal()
    try:
        packet = vanguard_board_reporting_service.generate_board_packet(db, tenant_id, "monthly_board_packet")
    finally:
        db.close()
    assert packet["content"]["source"] == "atlas_report"


def test_board_packet_exports_produce_bytes():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        packet = vanguard_board_reporting_service.generate_board_packet(db, tenant_id, "quality_committee_report")
    finally:
        db.close()
    pdf_bytes = vanguard_board_reporting_service.build_packet_pdf_bytes(packet)
    xlsx_bytes = vanguard_board_reporting_service.build_packet_xlsx_bytes(packet)
    pptx_bytes = vanguard_board_reporting_service.build_packet_pptx_bytes(packet)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(xlsx_bytes) > 100
    assert len(pptx_bytes) > 100


def test_api_board_report_pdf_endpoint():
    tenant_id = uid("vanguard-tenant")
    headers = _headers(AUTH_MGR, tenant_id)
    generated = client.post("/api/vanguard/board-reports/generate", json={"packet_type": "monthly_board_packet"}, headers=headers)
    assert generated.status_code == 200
    packet_id = generated.json()["id"]

    pdf_res = client.get(f"/api/vanguard/board-reports/{packet_id}.pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"

    detail_res = client.get(f"/api/vanguard/board-reports/{packet_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["packet_type"] == "monthly_board_packet"


# ── 3. Financial models ──────────────────────────────────────────────────────

def test_financial_intelligence_surfaces_data_source_and_real_fields():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        result = vanguard_financial_service.financial_intelligence(db, tenant_id)
    finally:
        db.close()
    assert result["data_source"] in ("real", "mock")
    assert "inspection_cost_trend_note" in result
    assert "repair_cost_trend_usd" in result
    assert "instrument_utilization_pct" in result


def test_operational_intelligence_includes_correlation():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        result = vanguard_operational_service.operational_intelligence(db, tenant_id)
    finally:
        db.close()
    assert "repair_backlog_vs_delayed_cases_correlation" in result
    assert "correlation_coefficient" in result["repair_backlog_vs_delayed_cases_correlation"]


# ── 4. AI advisor ─────────────────────────────────────────────────────────────

def test_new_vanguard_intents_classify_correctly():
    assert catalyst_query_engine.classify_intent("What are our top enterprise risks?") == catalyst_query_engine.INTENT_ENTERPRISE_RISK_SUMMARY
    assert catalyst_query_engine.classify_intent("Which investment will reduce repair costs?") == catalyst_query_engine.INTENT_INVESTMENT_RECOMMENDATION
    assert catalyst_query_engine.classify_intent("Which facilities require attention?") == catalyst_query_engine.INTENT_FACILITY_ATTENTION_RANKING
    assert catalyst_query_engine.classify_intent("What quality trends should I discuss at tomorrow's executive meeting?") == catalyst_query_engine.INTENT_QUALITY_TRENDS_FOR_MEETING


def test_ai_advisor_answer_query_dispatches_to_vanguard_service():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        result = catalyst_query_engine.answer_query(db, tenant_id, "What are our top enterprise risks?")
    finally:
        db.close()
    assert result["intent"] == catalyst_query_engine.INTENT_ENTERPRISE_RISK_SUMMARY
    assert result["skill_used"] == "enterprise_risk_summary"
    assert "top_risks" in result["data"]


def test_facilities_requiring_attention_without_facility_returns_empty():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        result = vanguard_ai_advisor_service.facilities_requiring_attention(db, tenant_id)
    finally:
        db.close()
    assert result["facilities"] == []


def test_api_chat_endpoint_answers_enterprise_risk_question():
    tenant_id = uid("vanguard-tenant")
    res = client.post("/api/catalyst/chat", json={"message": "What are our top enterprise risks?"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200
    assert res.json()["intent"] == "enterprise_risk_summary"


# ── 5. Benchmarking ───────────────────────────────────────────────────────────

def test_compute_benchmark_for_all_types():
    tenant_id = uid("vanguard-tenant")
    system_id = uid("system")
    _make_facility(tenant_id, system_id=system_id)
    db = SessionLocal()
    try:
        for benchmark_type in BENCHMARK_TYPES:
            result = vanguard_benchmarking_service.compute_benchmark(db, tenant_id, system_id, benchmark_type)
            assert result["benchmark_type"] == benchmark_type
            assert result["results"]
    finally:
        db.close()


def test_compute_benchmark_unknown_type_rejected():
    db = SessionLocal()
    try:
        try:
            vanguard_benchmarking_service.compute_benchmark(db, "t", "s", "not_a_real_type")
            assert False, "expected UnknownBenchmarkTypeError"
        except vanguard_benchmarking_service.UnknownBenchmarkTypeError:
            pass
    finally:
        db.close()


# ── 6. Strategic planning ─────────────────────────────────────────────────────

def test_generate_capital_planning_initiative():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        result = vanguard_strategy_service.generate_capital_planning(db, tenant_id, created_by="tester")
    finally:
        db.close()
    assert result["initiative_type"] == "capital_planning"
    assert result["status"] == "draft"


def test_generate_service_line_expansion_uses_real_case_volume():
    tenant_id = uid("vanguard-tenant")
    _make_case(tenant_id, service_line="cardiology")
    _make_case(tenant_id, service_line="cardiology")
    db = SessionLocal()
    try:
        result = vanguard_strategy_service.generate_service_line_expansion(db, tenant_id, created_by="tester")
    finally:
        db.close()
    lines = {row["service_line"]: row for row in result["details"]["service_line_growth"]}
    assert lines["cardiology"]["recent_30d"] == 2


def test_update_initiative_status():
    tenant_id = uid("vanguard-tenant")
    db = SessionLocal()
    try:
        created = vanguard_strategy_service.generate_quality_initiative(db, tenant_id, created_by="tester")
        updated = vanguard_strategy_service.update_initiative_status(db, tenant_id, created["id"], status="approved")
    finally:
        db.close()
    assert updated["status"] == "approved"


def test_api_generate_scenario_planning_endpoint():
    tenant_id = uid("vanguard-tenant")
    headers = _headers(AUTH_MGR, tenant_id)
    res = client.post(
        "/api/vanguard/strategy/generate/scenario_planning", json={"scenario_description": "What if volume grows 20%?"}, headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["initiative_type"] == "scenario_planning"

    listed = client.get("/api/vanguard/strategy/initiatives", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["initiatives"]) >= 1


# ── 7. Role permissions ───────────────────────────────────────────────────────

def test_leadership_gated_endpoints_reject_viewer():
    tenant_id = uid("vanguard-tenant")
    viewer_headers = _headers(AUTH_VIEWER, tenant_id)
    for path in ["/api/vanguard/executive-intelligence", "/api/vanguard/scorecards/ceo", "/api/vanguard/financial", "/api/vanguard/governance"]:
        res = client.get(path, headers=viewer_headers)
        assert res.status_code == 403, f"{path} should reject viewer role"


def test_leadership_gated_endpoints_allow_manager():
    tenant_id = uid("vanguard-tenant")
    mgr_headers = _headers(AUTH_MGR, tenant_id)
    for path in ["/api/vanguard/executive-intelligence", "/api/vanguard/scorecards/ceo", "/api/vanguard/financial", "/api/vanguard/governance"]:
        res = client.get(path, headers=mgr_headers)
        assert res.status_code == 200, f"{path} should allow spd_manager role"


def test_operational_endpoint_allows_all_roles():
    tenant_id = uid("vanguard-tenant")
    res = client.get("/api/vanguard/operational", headers=_headers(AUTH_VIEWER, tenant_id))
    assert res.status_code == 200
