"""v4.2 — LumenAI OS: Project Pulse — Real-Time Operations Center & Live
Clinical Intelligence tests."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.enterprise_hierarchy import EnterpriseFacility, EnterpriseMarket, EnterpriseRegion, HealthSystem
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import REPAIR_PENDING, RepairRequest
from app.models.supervisor_review import SupervisorReview

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


def _make_inspection(tenant_id: str, *, days_ago: int = 0, **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type="kerrison_rongeur", status="pending",
            coverage_pct=90, ai_confidence=0.9, score_status="scored",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(tenant_id: str, inspection_id: int, *, days_ago: int = 0, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_type="kerrison_rongeur",
            finding_type="blood", zone="serrations", severity_index=2,
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        db.add(InspectionFinding(**defaults))
        db.commit()
    finally:
        db.close()


def _make_repair(tenant_id: str, *, days_ago: int = 0, **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=1, instrument_identity=f"barcode:{uid('inst')}", vendor_name="AcmeVendor",
            status=REPAIR_PENDING, created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        row = RepairRequest(**defaults)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _make_supervisor_review(tenant_id: str, inspection_id: int, *, agreement: str = "agree", override_action: str = "") -> None:
    db = SessionLocal()
    try:
        db.add(SupervisorReview(tenant_id=tenant_id, inspection_id=inspection_id, agreement=agreement, override_action=override_action))
        db.commit()
    finally:
        db.close()


def _make_enterprise_facility(tenant_id: str) -> dict:
    db = SessionLocal()
    try:
        system_id = uid("system")
        market_id = uid("market")
        region_id = uid("region")
        facility_id = uid("facility")
        db.add(HealthSystem(system_id=system_id, system_name="Test System", admin_email="admin@test.com"))
        db.add(EnterpriseMarket(market_id=market_id, market_name="Test Market", system_id=system_id))
        db.add(EnterpriseRegion(region_id=region_id, region_name="Test Region", market_id=market_id, system_id=system_id))
        db.add(EnterpriseFacility(
            facility_id=facility_id, facility_name="Test Hospital", region_id=region_id, market_id=market_id,
            system_id=system_id, tenant_id=tenant_id,
        ))
        db.commit()
        return {"system_id": system_id, "facility_id": facility_id}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Section 1 — Command Center
# ---------------------------------------------------------------------------


def test_command_center_returns_all_named_widgets():
    tenant_id = uid("hospital")
    res = client.get("/api/pulse/command-center", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    for key in (
        "enterprise_health", "facility_health", "inspection_queue", "ai_analysis_queue", "supervisor_queue",
        "repair_queue", "enterprise_alerts", "digital_twin_health", "knowledge_growth", "ai_model_health",
        "system_status", "integrations", "notifications", "recent_activity",
    ):
        assert key in body, f"missing widget: {key}"


# ---------------------------------------------------------------------------
# Section 2 — Live Event Stream
# ---------------------------------------------------------------------------


def test_live_event_stream_lists_published_events():
    tenant_id = uid("hospital")
    db = SessionLocal()
    try:
        from app.services import pulse_event_service
        pulse_event_service.publish_pulse_event(
            db, tenant_id, "InspectionStarted", facility="Main Hospital", severity="info", source="test",
        )
    finally:
        db.close()

    res = client.get("/api/pulse/events", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    events = res.json()["events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "InspectionStarted"
    assert events[0]["payload"]["facility"] == "Main Hospital"


def test_workflow_execution_publishes_workflow_executed_event():
    tenant_id = uid("hospital")
    nodes = [
        {"key": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
        {"key": "end", "type": "end", "label": "End", "x": 200, "y": 0},
    ]
    edges = [{"from": "start", "to": "end"}]
    create = client.post("/api/forge/workflows", json={"name": uid("wf"), "nodes": nodes, "edges": edges}, headers=_headers(AUTH_ADMIN, tenant_id))
    workflow_id = create.json()["id"]
    client.post(f"/api/forge/workflows/{workflow_id}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    client.post("/api/forge/workflow-execution", json={"workflow_id": workflow_id}, headers=_headers(AUTH_ADMIN, tenant_id))

    res = client.get("/api/pulse/events", params={"event_type": "WorkflowExecuted"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200
    assert len(res.json()["events"]) == 1


# ---------------------------------------------------------------------------
# Section 3 — Enterprise Command Map
# ---------------------------------------------------------------------------


def test_enterprise_map_includes_facility_with_status_color():
    tenant_id = uid("hospital")
    ids = _make_enterprise_facility(tenant_id)
    res = client.get("/api/pulse/map", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    facilities = {f["facility_id"]: f for f in res.json()["facilities"]}
    assert ids["facility_id"] in facilities
    assert facilities[ids["facility_id"]]["status_color"] in ("green", "yellow", "orange", "red", "gray")


def test_facility_detail_404_for_unknown_facility():
    res = client.get("/api/pulse/map/facilities/not-a-system/not-a-facility", headers=AUTH_VIEWER)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Section 4 — Live Operational KPIs
# ---------------------------------------------------------------------------


def test_live_kpis_reflect_real_inspection_data():
    tenant_id = uid("hospital")
    _make_inspection(tenant_id, coverage_pct=80, ai_confidence=0.85)
    _make_inspection(tenant_id, coverage_pct=90, ai_confidence=0.95)
    _make_repair(tenant_id)

    res = client.get("/api/pulse/kpis", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["inspection_throughput"] == 2
    assert body["repair_queue_length"] == 1
    assert abs(body["coverage_pct_avg"] - 85.0) < 0.01
    assert abs(body["ai_confidence_avg"] - 0.9) < 0.01


# ---------------------------------------------------------------------------
# Section 5 — Pulse Alert Engine
# ---------------------------------------------------------------------------


def test_generate_alerts_detects_missing_baseline():
    tenant_id = uid("hospital")
    for _ in range(6):
        _make_inspection(tenant_id, baseline_status="not_checked")

    res = client.post("/api/pulse/alerts/generate", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    alert_types = {a["alert_type"] for a in res.json()["alerts"]}
    assert "missing_baseline" in alert_types


def test_generate_alerts_is_idempotent_no_duplicate_active():
    tenant_id = uid("hospital")
    for _ in range(6):
        _make_inspection(tenant_id, baseline_status="not_checked")

    first = client.post("/api/pulse/alerts/generate", headers=_headers(AUTH_ADMIN, tenant_id)).json()["alerts"]
    second = client.post("/api/pulse/alerts/generate", headers=_headers(AUTH_ADMIN, tenant_id)).json()["alerts"]
    assert len(first) >= 1
    assert len(second) == 0  # already active, not duplicated

    listed = client.get("/api/pulse/alerts", params={"status": "active"}, headers=_headers(AUTH_ADMIN, tenant_id)).json()["alerts"]
    missing_baseline_alerts = [a for a in listed if a["alert_type"] == "missing_baseline"]
    assert len(missing_baseline_alerts) == 1


def test_acknowledge_and_resolve_alert():
    tenant_id = uid("hospital")
    for _ in range(6):
        _make_inspection(tenant_id, baseline_status="not_checked")
    generated = client.post("/api/pulse/alerts/generate", headers=_headers(AUTH_ADMIN, tenant_id)).json()["alerts"]
    alert_id = generated[0]["id"]

    ack = client.post(f"/api/pulse/alerts/{alert_id}/acknowledge", headers=_headers(AUTH_MGR, tenant_id))
    assert ack.status_code == 200, ack.text
    assert ack.json()["status"] == "acknowledged"

    resolve = client.post(f"/api/pulse/alerts/{alert_id}/resolve", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"


def test_repeated_supervisor_overrides_alert():
    tenant_id = uid("hospital")
    for i in range(6):
        insp_id = _make_inspection(tenant_id)
        _make_supervisor_review(tenant_id, insp_id, agreement="disagree", override_action="reclean")

    res = client.post("/api/pulse/alerts/generate", headers=_headers(AUTH_ADMIN, tenant_id))
    alert_types = {a["alert_type"] for a in res.json()["alerts"]}
    assert "repeated_supervisor_overrides" in alert_types


def test_acknowledge_unknown_alert_404():
    res = client.post("/api/pulse/alerts/999999999/acknowledge", headers=AUTH_ADMIN)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Section 6 — Executive Command Dashboard
# ---------------------------------------------------------------------------


def test_executive_dashboard_returns_scores():
    tenant_id = uid("hospital")
    res = client.get("/api/pulse/executive", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    for key in ("enterprise_score", "quality_score", "risk_score", "operational_health_pct", "digital_twin_health_pct"):
        assert key in body


def test_executive_dashboard_requires_leadership_role():
    res = client.get("/api/pulse/executive", headers=AUTH_VIEWER)
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Section 7 — Live Workflow Monitoring
# ---------------------------------------------------------------------------


def test_workflow_monitor_reflects_completed_execution():
    tenant_id = uid("hospital")
    nodes = [
        {"key": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
        {"key": "notify", "type": "notification", "label": "Notify", "x": 200, "y": 0},
        {"key": "end", "type": "end", "label": "End", "x": 400, "y": 0},
    ]
    edges = [{"from": "start", "to": "notify"}, {"from": "notify", "to": "end"}]
    create = client.post("/api/forge/workflows", json={"name": uid("wf"), "nodes": nodes, "edges": edges}, headers=_headers(AUTH_ADMIN, tenant_id))
    workflow_id = create.json()["id"]
    client.post(f"/api/forge/workflows/{workflow_id}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    execution = client.post("/api/forge/workflow-execution", json={"workflow_id": workflow_id}, headers=_headers(AUTH_ADMIN, tenant_id)).json()

    res = client.get(f"/api/pulse/workflow-monitor/{execution['id']}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "completed"
    assert body["current_stage"] == "end"


def test_workflow_monitor_404_for_unknown_execution():
    res = client.get("/api/pulse/workflow-monitor/999999999", headers=AUTH_ADMIN)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Section 8 — AI Operations Monitor
# ---------------------------------------------------------------------------


def test_ai_ops_monitor_reports_hardware_not_applicable():
    tenant_id = uid("hospital")
    _make_inspection(tenant_id, model_version="1.2.0", ai_confidence=0.88)
    res = client.get("/api/pulse/ai-ops", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["gpu_utilization"] == "not_applicable"
    assert body["cpu_utilization"] == "not_applicable"
    assert "1.2.0" in body["model_version_distribution"]


# ---------------------------------------------------------------------------
# Section 9 — Facility Command Console (drill-down)
# ---------------------------------------------------------------------------


def test_facility_console_composes_kpis_and_alerts():
    tenant_id = uid("hospital")
    _make_inspection(tenant_id)
    res = client.get("/api/pulse/facility-console", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert "kpis" in body and "alerts" in body and "notifications" in body


# ---------------------------------------------------------------------------
# Section 10 — Notification Center
# ---------------------------------------------------------------------------


def test_notification_center_feed_endpoint():
    tenant_id = uid("hospital")
    res = client.get("/api/pulse/notifications", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    assert "supported_channels" in res.json()
    assert "sms" in res.json()["supported_channels"]


def test_send_notification_sms_is_an_honest_stub():
    res = client.post(
        "/api/pulse/notifications/send", json={"channel": "sms", "title": "Test", "message": "hello", "recipient": "+15551234567"},
        headers=AUTH_ADMIN,
    )
    assert res.status_code == 200, res.text
    assert res.json()["sent"] is False
    assert "not configured" in res.json()["reason"]


def test_send_notification_rejects_unknown_channel():
    res = client.post("/api/pulse/notifications/send", json={"channel": "carrier_pigeon", "title": "x", "message": "y"}, headers=AUTH_ADMIN)
    assert res.status_code == 422


def test_route_notification_dispatches_matching_forge_rule():
    tenant_id = uid("hospital")
    condition = {"field": "severity", "operator": "gte", "value": 3}
    rule = client.post(
        "/api/forge/workflow-rules",
        json={"name": "High Severity Notify", "condition": condition, "actions": [{"type": "notify_supervisor", "params": {"channel": "in_app", "message": "High severity finding"}}]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    ).json()
    client.post(f"/api/forge/workflow-rules/{rule['id']}/approve", headers=_headers(AUTH_ADMIN, tenant_id))

    res = client.post(
        "/api/pulse/notifications/route", json={"context": {"severity": 4}}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 200, res.text
    dispatched = res.json()["dispatched"]
    assert len(dispatched) == 1
    assert dispatched[0]["channel"] == "in_app"
    assert dispatched[0]["result"]["sent"] is True


# ---------------------------------------------------------------------------
# Section 11 — Operational Replay
# ---------------------------------------------------------------------------


def test_replay_shift_includes_recent_events():
    tenant_id = uid("hospital")
    db = SessionLocal()
    try:
        from app.services import pulse_event_service
        pulse_event_service.publish_pulse_event(db, tenant_id, "InspectionStarted", severity="info")
    finally:
        db.close()

    shift_start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    res = client.get("/api/pulse/replay/shift", params={"shift_start": shift_start, "shift_hours": 8}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["event_count"] >= 1
    assert any(e["kind"] == "event" for e in body["timeline"])


def test_replay_incident_404_for_unknown_alert():
    res = client.get("/api/pulse/replay/incident/999999999", headers=AUTH_ADMIN)
    assert res.status_code == 404


def test_replay_incident_centers_on_alert_time():
    tenant_id = uid("hospital")
    for _ in range(6):
        _make_inspection(tenant_id, baseline_status="not_checked")
    generated = client.post("/api/pulse/alerts/generate", headers=_headers(AUTH_ADMIN, tenant_id)).json()["alerts"]
    alert_id = generated[0]["id"]

    res = client.get(f"/api/pulse/replay/incident/{alert_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    assert res.json()["incident_alert_id"] == alert_id


# ---------------------------------------------------------------------------
# Section 12 — Command Widgets + Section 13 — Mobile layout personalization
# ---------------------------------------------------------------------------


def test_widgets_catalog_has_nine_named_widgets():
    res = client.get("/api/pulse/widgets", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    keys = {w["widget_key"] for w in res.json()["widgets"]}
    assert keys == {
        "inspection_counter", "queue_heatmap", "facility_status", "ai_health", "knowledge_growth",
        "digital_twin_status", "enterprise_alerts", "trend_chart", "forecast_widget",
    }


def test_default_layout_has_all_widgets_when_unsaved():
    tenant_id = uid("hospital")
    res = client.get("/api/pulse/dashboard-layout", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    assert res.json()["is_default"] is True
    assert len(res.json()["layout"]) == 9


def test_save_and_retrieve_custom_layout():
    tenant_id = uid("hospital")
    custom_layout = [{"widget_key": "ai_health", "x": 0, "y": 0, "w": 2, "h": 1}]
    save = client.post("/api/pulse/dashboard-layout", json={"layout": custom_layout}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert save.status_code == 200, save.text

    fetched = client.get("/api/pulse/dashboard-layout", headers=_headers(AUTH_ADMIN, tenant_id))
    assert fetched.json()["is_default"] is False
    assert fetched.json()["layout"] == custom_layout


def test_mobile_layout_independent_of_desktop_layout():
    tenant_id = uid("hospital")
    desktop_layout = [{"widget_key": "trend_chart", "x": 0, "y": 0, "w": 1, "h": 1}]
    mobile_layout = [{"widget_key": "inspection_counter", "x": 0, "y": 0, "w": 1, "h": 1}]

    client.post("/api/pulse/dashboard-layout", json={"layout": desktop_layout, "is_mobile": False}, headers=_headers(AUTH_ADMIN, tenant_id))
    client.post("/api/pulse/dashboard-layout", json={"layout": mobile_layout, "is_mobile": True}, headers=_headers(AUTH_ADMIN, tenant_id))

    desktop = client.get("/api/pulse/dashboard-layout", params={"is_mobile": False}, headers=_headers(AUTH_ADMIN, tenant_id))
    mobile = client.get("/api/pulse/dashboard-layout", params={"is_mobile": True}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert desktop.json()["layout"] == desktop_layout
    assert mobile.json()["layout"] == mobile_layout


def test_save_layout_rejects_unknown_widget_key():
    tenant_id = uid("hospital")
    res = client.post(
        "/api/pulse/dashboard-layout", json={"layout": [{"widget_key": "not_a_widget", "x": 0, "y": 0, "w": 1, "h": 1}]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# API permissions (enterprise aggregation gating)
# ---------------------------------------------------------------------------


def test_alert_generate_requires_leadership_role():
    res = client.post("/api/pulse/alerts/generate", headers=AUTH_VIEWER)
    assert res.status_code == 403


def test_command_center_permitted_for_viewer():
    res = client.get("/api/pulse/command-center", headers=AUTH_VIEWER)
    assert res.status_code == 200
