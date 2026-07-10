"""v4.5 — LumenAI OS: Project Orbit — Perioperative Intelligence &
Surgical Readiness Platform tests.

Covers: readiness calculation, case intelligence, alert generation,
procedure mapping, dashboard aggregation, workflow coordination, API
endpoints, and simulation integration.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.or_connect import RISK_EQUIPMENT_UNAVAILABLE, RISK_MISSING_IMPLANT
from app.models.orbit_readiness import IMPLANT_MISSING, CaseCart, ImplantRecord, LoanerEquipment
from app.services import (
    knowledge_repository_service,
    or_connect_service,
    orbit_alert_service,
    orbit_case_intelligence_service,
    orbit_coordination_service,
    orbit_executive_service,
    orbit_procedure_knowledge_service,
    orbit_readiness_engine,
    orbit_simulation_service,
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


def _make_case(tenant_id: str, *, procedure: str = "Total Knee Replacement", hours_from_now: float = 48):
    db = SessionLocal()
    try:
        case = or_connect_service.create_case(
            db, tenant_id, procedure=procedure,
            scheduled_start=datetime.now(timezone.utc) + timedelta(hours=hours_from_now),
            service_line="orthopedics", surgeon="Dr. Test", facility_name="Main Hospital",
        )
        return case.id, case.case_ref
    finally:
        db.close()


# ── 1. Readiness calculation ─────────────────────────────────────────────────

def test_compute_surgical_readiness_returns_nine_weighted_dimensions():
    tenant_id = uid("orbit-tenant")
    case_id, case_ref = _make_case(tenant_id)

    db = SessionLocal()
    try:
        result = orbit_readiness_engine.compute_surgical_readiness(db, tenant_id, case_id)
    finally:
        db.close()

    assert result["case_ref"] == case_ref
    assert set(result["dimensions"]) == {
        "patient_procedure_score", "case_cart_score", "instrument_tray_score", "individual_instrument_score",
        "implant_score", "equipment_score", "staff_score", "environmental_score", "clinical_score",
    }
    total_weight = sum(d["weight"] for d in result["dimensions"].values())
    assert total_weight == 100
    assert 0 <= result["overall_score"] <= 100


def test_missing_implant_lowers_implant_score():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id)

    db = SessionLocal()
    try:
        db.add(ImplantRecord(tenant_id=tenant_id, case_id=case_id, implant_name="Femoral Component", status=IMPLANT_MISSING))
        db.commit()
        result = orbit_readiness_engine.compute_surgical_readiness(db, tenant_id, case_id)
    finally:
        db.close()

    assert result["dimensions"]["implant_score"]["value"] == 0.0


def test_readiness_history_accrues_snapshots():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id)

    db = SessionLocal()
    try:
        orbit_readiness_engine.compute_surgical_readiness(db, tenant_id, case_id)
        orbit_readiness_engine.compute_surgical_readiness(db, tenant_id, case_id)
        history = orbit_readiness_engine.readiness_history(db, tenant_id, case_id)
    finally:
        db.close()
    assert len(history) == 2


# ── 2. Case intelligence ──────────────────────────────────────────────────────

def test_case_intelligence_composes_implants_equipment_and_cart():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id)

    db = SessionLocal()
    try:
        db.add(ImplantRecord(tenant_id=tenant_id, case_id=case_id, implant_name="Tibial Tray", status="available"))
        db.add(LoanerEquipment(tenant_id=tenant_id, case_id=case_id, equipment_name="Nav System", status="requested"))
        db.add(CaseCart(tenant_id=tenant_id, case_id=case_id, status="assembling"))
        db.commit()
        result = orbit_case_intelligence_service.case_intelligence(db, tenant_id, case_id)
    finally:
        db.close()

    assert len(result["implants"]) == 1
    assert len(result["loaner_equipment"]) == 1
    assert result["case_cart"]["status"] == "assembling"
    assert result["supervisor_holds"] == ["Supervisor approval pending for this case."]


# ── 3. Alert generation ───────────────────────────────────────────────────────

def test_generate_readiness_alerts_detects_missing_implant_and_equipment():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id, hours_from_now=2)

    db = SessionLocal()
    try:
        db.add(ImplantRecord(tenant_id=tenant_id, case_id=case_id, implant_name="Femoral Component", status=IMPLANT_MISSING))
        db.add(LoanerEquipment(tenant_id=tenant_id, case_id=case_id, equipment_name="Nav System", status="requested"))
        db.commit()
        alerts = orbit_alert_service.generate_readiness_alerts(db, tenant_id, case_id)
    finally:
        db.close()

    risk_types = {a["risk_type"] for a in alerts}
    assert RISK_MISSING_IMPLANT in risk_types
    assert RISK_EQUIPMENT_UNAVAILABLE in risk_types
    for a in alerts:
        assert a["recommended_action"]


# ── 4. Procedure mapping ──────────────────────────────────────────────────────

def test_procedure_knowledge_maps_articles_to_instrument_families():
    tenant_id = uid("orbit-tenant")
    db = SessionLocal()
    try:
        knowledge_repository_service.create_article(
            db, tenant_id=tenant_id, category="best_practice", title="Knee replacement instrument care",
            body="Inspect the tibial cutting guide thoroughly.", author="tester", approval_status="approved",
            procedure="Total Knee Replacement",
        )
        db.commit()
        result = orbit_procedure_knowledge_service.procedure_knowledge(db, tenant_id, procedure="Total Knee Replacement")
    finally:
        db.close()

    assert result["procedure"] == "Total Knee Replacement"
    assert len(result["knowledge_articles"]) >= 1


# ── 5. Dashboard aggregation ──────────────────────────────────────────────────

def test_executive_surgical_operations_returns_expected_shape():
    tenant_id = uid("orbit-tenant")
    _make_case(tenant_id)

    db = SessionLocal()
    try:
        result = orbit_executive_service.executive_surgical_operations(db, tenant_id)
    finally:
        db.close()

    for key in ["cases_today", "readiness_pct", "delayed_cases", "inspection_holds", "repair_holds", "digital_twin_risk", "top_operational_risks"]:
        assert key in result
    assert result["human_review_required"] is True


# ── 6. Workflow coordination ──────────────────────────────────────────────────

def test_department_coordination_timeline_merges_notifications_and_alerts():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id, hours_from_now=1)

    db = SessionLocal()
    try:
        orbit_coordination_service.coordinate_case(db, tenant_id, case_id)
        timeline = orbit_coordination_service.department_coordination_timeline(db, tenant_id, case_id)
    finally:
        db.close()

    assert "infection_prevention" in timeline["departments"]
    assert "quality" in timeline["departments"]
    assert "biomedical_engineering" in timeline["departments"]
    assert isinstance(timeline["timeline"], list)


# ── 7. API endpoints ──────────────────────────────────────────────────────────

def test_api_case_readiness_and_timeline_and_alerts_endpoints():
    tenant_id = uid("orbit-tenant")
    case_id, case_ref = _make_case(tenant_id)
    headers = _headers(AUTH_ADMIN, tenant_id)

    readiness = client.get(f"/api/orbit/case-readiness/{case_id}", headers=headers)
    assert readiness.status_code == 200
    assert readiness.json()["case_ref"] == case_ref

    timeline = client.get(f"/api/orbit/cases/{case_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    step_names = [s["step"] for s in timeline.json()["steps"]]
    assert "Case Cart Complete" in step_names
    assert "Procedure Complete" in step_names
    assert "Sterilization Status (visibility only)" in step_names

    alerts = client.get(f"/api/orbit/readiness-alerts/{case_id}", headers=headers)
    assert alerts.status_code == 200

    executive = client.get("/api/orbit/executive", headers=_headers(AUTH_MGR, tenant_id))
    assert executive.status_code == 200

    executive_denied = client.get("/api/orbit/executive", headers=_headers(AUTH_VIEWER, tenant_id))
    assert executive_denied.status_code == 403


def test_api_case_cart_and_implant_creation_and_patch():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id)
    headers = _headers(AUTH_ADMIN, tenant_id)

    cart = client.post(f"/api/orbit/cases/{case_id}/cart", json={"status": "assembling", "item_count": 12}, headers=headers)
    assert cart.status_code == 200
    cart_id = cart.json()["id"]

    patched = client.patch(f"/api/orbit/cart/{cart_id}", json={"status": "complete"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["status"] == "complete"

    implant = client.post(f"/api/orbit/cases/{case_id}/implants", json={"implant_name": "Hip Stem", "status": "backordered"}, headers=headers)
    assert implant.status_code == 200
    assert implant.json()["status"] == "backordered"


def test_api_procedure_intelligence_endpoint():
    tenant_id = uid("orbit-tenant")
    res = client.get("/api/orbit/procedure-intelligence?procedure=Total Knee Replacement", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200
    assert res.json()["procedure"] == "Total Knee Replacement"


# ── 8. Simulation integration ─────────────────────────────────────────────────

def test_simulate_case_time_shift_persists_and_returns_impact():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id)

    db = SessionLocal()
    try:
        result = orbit_simulation_service.simulate_case_time_shift(db, tenant_id, case_id, hours_shift=2.0)
        runs = orbit_simulation_service.list_simulation_runs(db, tenant_id, case_id)
    finally:
        db.close()

    assert result["scenario_type"] == "case_time_shift"
    assert result["human_review_required"] is True
    assert len(runs) == 1


def test_simulate_vendor_tray_delay_refuses_to_fabricate_unshipped_arrival():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id)

    db = SessionLocal()
    try:
        tray = or_connect_service.add_vendor_tray(db, tenant_id, case_id, tray_name="Hip Instrument Set", vendor_name="AcmeVendor")
        result = orbit_simulation_service.simulate_vendor_tray_delayed(db, tenant_id, case_id, tray_id=tray.id, delay_hours=6.0)
    finally:
        db.close()

    assert result["projected_impact"]["misses_case_start"] is None
    assert "has not yet shipped" in result["rationale"]


def test_api_simulation_endpoint_roundtrip():
    tenant_id = uid("orbit-tenant")
    case_id, _ = _make_case(tenant_id)
    headers = _headers(AUTH_ADMIN, tenant_id)

    sim = client.post(f"/api/orbit/cases/{case_id}/simulate/time-shift", json={"hours_shift": -3}, headers=headers)
    assert sim.status_code == 200

    listed = client.get(f"/api/orbit/cases/{case_id}/simulations", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["simulations"]) == 1
