"""v3.0 — Project Sentinel: Autonomous Clinical Intelligence Orchestration tests."""
from __future__ import annotations


from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.disposition_override import DispositionOverride
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import RepairRequest
from app.models.supervisor_review import SupervisorReview

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "s3nt1nel" + "0" * 56
TENANT = "default-tenant"


def _make_inspection(**overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=TENANT, file_name="x.jpg", instrument_type="kerrison_rongeur",
            has_image=True, image_sha256=SHA, score_status="scored", risk_score=10,
            detected_issue="none", stain_detected=False, supervisor_review_required=False,
            qa_review_status="pending", status="pending", inspected_zones_json="null",
            coverage_pct=100, baseline_status="approved", disposition="PASS", technician="Alex Tech",
            facility_name="Mercy General",
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(inspection_id: int, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(tenant_id=TENANT, inspection_id=inspection_id, instrument_type="kerrison_rongeur", finding_type="blood", zone="serrations")
        defaults.update(overrides)
        db.add(InspectionFinding(**defaults))
        db.commit()
    finally:
        db.close()


def _make_supervisor_review(**overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(tenant_id=TENANT, inspection_id=1, reviewer_name="Supervisor One", reviewer_role="spd_manager", agreement="agree", ai_confidence=0.9)
        defaults.update(overrides)
        db.add(SupervisorReview(**defaults))
        db.commit()
    finally:
        db.close()


def _make_override(**overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(tenant_id=TENANT, inspection_id=1, reviewer_name="Supervisor One", reviewer_role="spd_manager", action="modify", ai_recommended_disposition="PASS")
        defaults.update(overrides)
        db.add(DispositionOverride(**defaults))
        db.commit()
    finally:
        db.close()


def _make_repair(**overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(tenant_id=TENANT, inspection_id=1, instrument_identity="barcode:x", vendor_name="AcmeSurgical")
        defaults.update(overrides)
        db.add(RepairRequest(**defaults))
        db.commit()
    finally:
        db.close()


class TestSentinelEngine:
    def test_run_scan_returns_summary(self):
        r = client.post("/api/sentinel/scan", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "risk_signals_count", "watchlist_count", "digital_twin_flags_count",
            "alerts_count", "recommendations_count", "enterprise_risk_score",
        ):
            assert key in body
        assert body["human_review_required"] is True

    def test_scan_requires_leadership_role(self):
        r = client.post("/api/sentinel/scan", headers=AUTH_VIEWER)
        assert r.status_code == 403


class TestRiskMonitor:
    def test_detects_repeated_blood(self):
        for _ in range(3):
            insp_id = _make_inspection()
            _make_finding(insp_id, finding_type="blood", zone="serrations")

        r = client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR)
        assert r.status_code == 200
        signals = r.json()["signals"]
        assert any(s["signal_type"] == "repeated_blood" and s["scope"] == "serrations" for s in signals)

    def test_detects_repeated_supervisor_overrides(self):
        insp_id = _make_inspection(instrument_type="scissors_test_type")
        for _ in range(3):
            _make_override(inspection_id=insp_id)

        r = client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR)
        signals = r.json()["signals"]
        assert any(s["signal_type"] == "repeated_supervisor_overrides" and s["scope"] == "scissors_test_type" for s in signals)

    def test_detects_repeated_repair_referrals(self):
        insp_id = _make_inspection(instrument_type="drill_bit_test_type")
        for _ in range(3):
            _make_repair(inspection_id=insp_id)

        r = client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR)
        signals = r.json()["signals"]
        assert any(s["signal_type"] == "repeated_repair_referrals" and s["scope"] == "drill_bit_test_type" for s in signals)

    def test_no_signal_below_threshold(self):
        insp_id = _make_inspection(instrument_type="unique_below_threshold")
        _make_finding(insp_id, finding_type="rust", zone="unique_zone_xyz")

        r = client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR)
        signals = r.json()["signals"]
        assert not any(s["scope"] == "unique_zone_xyz" for s in signals)

    def test_resolve_signal(self):
        for _ in range(3):
            insp_id = _make_inspection()
            _make_finding(insp_id, finding_type="bone", zone="resolve-test-zone")
        signals = client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR).json()["signals"]
        target = next(s for s in signals if s["scope"] == "resolve-test-zone")

        r = client.post(f"/api/sentinel/risk-signals/{target['id']}/resolve", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["resolved_at"] is not None

        r2 = client.get("/api/sentinel/risk-signals", headers=AUTH_OPERATOR)
        assert not any(s["id"] == target["id"] for s in r2.json()["signals"])

    def test_list_requires_auth(self):
        r = client.get("/api/sentinel/risk-signals")
        assert r.status_code in (401, 403)


class TestWatchlists:
    def test_refresh_creates_anatomy_and_instrument_entries(self):
        for _ in range(3):
            insp_id = _make_inspection(instrument_type="watchlist_instrument")
            _make_finding(insp_id, finding_type="corrosion", zone="watchlist-zone", instrument_type="watchlist_instrument")

        r = client.post("/api/sentinel/watchlist/refresh", headers=AUTH_MGR)
        assert r.status_code == 200
        watchlist = r.json()["watchlist"]
        assert any(w["entity_type"] == "anatomy" and w["entity_value"] == "watchlist-zone" for w in watchlist)
        assert any(w["entity_type"] == "instrument" and w["entity_value"] == "watchlist_instrument" for w in watchlist)

    def test_filter_by_entity_type(self):
        r = client.get("/api/sentinel/watchlist", params={"entity_type": "anatomy"}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert all(w["entity_type"] == "anatomy" for w in r.json()["watchlist"])

    def test_invalid_entity_type_rejected(self):
        r = client.get("/api/sentinel/watchlist", params={"entity_type": "not_a_type"}, headers=AUTH_OPERATOR)
        assert r.status_code == 422

    def test_resolve_watchlist_entry(self):
        for _ in range(3):
            insp_id = _make_inspection(instrument_type="resolve_watch_instrument")
            _make_finding(insp_id, finding_type="pitting", zone="z1", instrument_type="resolve_watch_instrument")
        watchlist = client.post("/api/sentinel/watchlist/refresh", headers=AUTH_MGR).json()["watchlist"]
        target = next(w for w in watchlist if w["entity_value"] == "resolve_watch_instrument")

        r = client.post(f"/api/sentinel/watchlist/{target['id']}/resolve", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "resolved"


class TestAIHealthMonitor:
    def test_ai_health_returns_expected_shape(self):
        _make_supervisor_review()
        r = client.get("/api/sentinel/ai-health", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "ai_confidence_avg", "supervisor_agreement_rate", "false_positive_rate", "false_negative_rate",
            "coverage_quality_pct", "baseline_quality_pct", "kg_confidence", "drift_detected", "drift_detail",
        ):
            assert key in body

    def test_insufficient_reviews_reports_honestly_not_fabricated(self):
        r = client.get("/api/sentinel/ai-health", headers=AUTH_MGR)
        body = r.json()
        assert body["drift_detected"] is False
        assert "insufficient" in body["drift_detail"].lower() or "no significant" in body["drift_detail"].lower()

    def test_requires_leadership_role(self):
        r = client.get("/api/sentinel/ai-health", headers=AUTH_VIEWER)
        assert r.status_code == 403


class TestDigitalTwinMonitoring:
    def test_declining_trend_with_repairs_flags_escalation(self):
        barcode = "twin-escalation-001"
        for i in range(4):
            insp_id = _make_inspection(
                instrument_barcode=barcode, disposition="REMOVE FROM SERVICE" if i < 2 else "PASS",
            )
            _make_finding(insp_id, finding_type="corrosion", zone="z1")

        r = client.post("/api/sentinel/digital-twin-flags/monitor", headers=AUTH_MGR)
        assert r.status_code == 200
        flags = r.json()["flags"]
        flag = next((f for f in flags if f["instrument_identity"] == f"barcode:{barcode}"), None)
        assert flag is not None
        assert flag["tier"] in ("critical", "escalation")

    def test_insufficient_history_not_flagged(self):
        barcode = "twin-insufficient-001"
        _make_inspection(instrument_barcode=barcode)

        r = client.post("/api/sentinel/digital-twin-flags/monitor", headers=AUTH_MGR)
        flags = r.json()["flags"]
        assert not any(f["instrument_identity"] == f"barcode:{barcode}" for f in flags)

    def test_filter_by_tier(self):
        r = client.get("/api/sentinel/digital-twin-flags", params={"tier": "escalation"}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert all(f["tier"] == "escalation" for f in r.json()["flags"])


class TestRecommendationEngine:
    def test_high_retention_zone_recommends_ifu_review(self):
        for _ in range(3):
            insp_id = _make_inspection()
            _make_finding(insp_id, finding_type="blood", zone="serrations")
        client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR)

        r = client.post("/api/sentinel/recommendations/generate", headers=AUTH_MGR)
        assert r.status_code == 200
        recs = r.json()["recommendations"]
        assert any(rec["recommendation_type"] == "review_ifu" and rec["target_description"] == "serrations" for rec in recs)
        ifu_rec = next(rec for rec in recs if rec["recommendation_type"] == "review_ifu")
        assert "IFU" in ifu_rec["reasoning"] or "serrations" in ifu_rec["reasoning"]

    def test_watchlist_instrument_without_baseline_recommends_create_baseline(self):
        for _ in range(3):
            insp_id = _make_inspection(instrument_type="no_baseline_instrument_xyz")
            _make_finding(insp_id, finding_type="crack", zone="z2", instrument_type="no_baseline_instrument_xyz")
        client.post("/api/sentinel/watchlist/refresh", headers=AUTH_MGR)

        r = client.post("/api/sentinel/recommendations/generate", headers=AUTH_MGR)
        recs = r.json()["recommendations"]
        assert any(rec["recommendation_type"] == "create_baseline" and rec["target_description"] == "no_baseline_instrument_xyz" for rec in recs)

    def test_action_and_dismiss_recommendation(self):
        recs = client.get("/api/sentinel/recommendations", headers=AUTH_OPERATOR).json()["recommendations"]
        assert len(recs) > 0
        rec_id = recs[0]["id"]

        r = client.post(f"/api/sentinel/recommendations/{rec_id}/action", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "actioned"

    def test_every_recommendation_has_reasoning(self):
        recs = client.get("/api/sentinel/recommendations", params={"status": ""}, headers=AUTH_OPERATOR).json()["recommendations"]
        assert all(rec["reasoning"] for rec in recs)


class TestAlertGeneration:
    def test_generates_explainable_alert_from_risk_signal(self):
        for _ in range(3):
            insp_id = _make_inspection()
            _make_finding(insp_id, finding_type="blood", zone="alert-test-zone")
        client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR)

        r = client.post("/api/sentinel/alerts/generate", headers=AUTH_MGR)
        assert r.status_code == 200
        alerts = r.json()["alerts"]
        alert = next((a for a in alerts if "alert-test-zone" in a["title"]), None)
        assert alert is not None
        assert alert["narrative"]
        assert alert["recommendation"]
        assert alert["severity"] in ("low", "medium", "high", "critical")

    def test_acknowledge_and_resolve_alert(self):
        alerts = client.get("/api/sentinel/alerts", headers=AUTH_OPERATOR).json()["alerts"]
        assert len(alerts) > 0
        alert_id = alerts[0]["id"]

        r = client.post(f"/api/sentinel/alerts/{alert_id}/acknowledge", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert r.json()["acknowledged"] is True

        r2 = client.post(f"/api/sentinel/alerts/{alert_id}/resolve", headers=AUTH_MGR)
        assert r2.status_code == 200
        assert r2.json()["resolved_at"] is not None

    def test_no_duplicate_alerts_for_same_signal(self):
        for _ in range(3):
            insp_id = _make_inspection()
            _make_finding(insp_id, finding_type="bone", zone="dedup-test-zone")
        client.post("/api/sentinel/risk-signals/detect", headers=AUTH_MGR)
        client.post("/api/sentinel/alerts/generate", headers=AUTH_MGR)
        r = client.post("/api/sentinel/alerts/generate", headers=AUTH_MGR)
        alerts = [a for a in r.json()["alerts"] if "dedup-test-zone" in a["title"]]
        assert len(alerts) == 1


class TestSupervisorIntelligence:
    def test_summary_returns_expected_shape(self):
        r = client.get("/api/sentinel/supervisor-intelligence", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "high_risk_instruments_awaiting_review", "recurring_technician_education_needs", "coverage_gaps",
            "unusual_contamination_trends", "repeated_repair_referrals", "potential_ifu_conflicts",
        ):
            assert key in body


class TestDashboardAggregation:
    def test_dashboard_returns_expected_shape(self):
        r = client.get("/api/sentinel/dashboard", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "enterprise_risk_score", "critical_findings", "open_watchlists", "model_health",
            "knowledge_growth", "inspection_throughput", "facility_comparison", "supervisor_workload",
            "top_emerging_risks",
        ):
            assert key in body
        assert 0 <= body["enterprise_risk_score"] <= 100

    def test_dashboard_requires_leadership_role(self):
        r = client.get("/api/sentinel/dashboard", headers=AUTH_VIEWER)
        assert r.status_code == 403
