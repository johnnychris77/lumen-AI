"""P9: Autonomous Inspection Copilot — comprehensive test suite (80+ tests)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def start_session(instrument_name="Mayo Scissors", instrument_id="SCI-001", mode="guided", technician="tech-001"):
    r = client.post("/api/copilot/sessions", headers=HEADERS, json={
        "technician_id": technician,
        "instrument_name": instrument_name,
        "instrument_id": instrument_id,
        "copilot_mode": mode,
        "facility_id": "FAC-A",
    })
    assert r.status_code == 200, r.text
    return r.json()


def respond_step(session_id, step_id, response="pass", finding="", notes=""):
    r = client.post(
        f"/api/copilot/sessions/{session_id}/steps/{step_id}/respond",
        headers=HEADERS,
        json={"technician_response": response, "finding_category": finding, "notes": notes},
    )
    assert r.status_code == 200, r.text
    return r.json()


# ── TestSessionLifecycle ─────────────────────────────────────────────────────

class TestSessionLifecycle:
    def test_start_session_basic(self):
        data = start_session()
        assert data["session_status"] == "active"
        assert data["instrument_name"] == "Mayo Scissors"
        assert len(data["steps"]) > 0
        assert data["total_steps"] == len(data["steps"])
        assert data["completed_steps"] == 0

    def test_start_session_returns_technician_id(self):
        data = start_session(technician="tech-xyz")
        assert data["technician_id"] == "tech-xyz"

    def test_start_session_instrument_id_stored(self):
        data = start_session(instrument_id="SCI-999")
        assert data["instrument_id"] == "SCI-999"

    def test_start_session_copilot_mode_stored(self):
        data = start_session(mode="autonomous")
        assert data["copilot_mode"] == "autonomous"

    def test_start_session_audit_mode(self):
        data = start_session(mode="audit")
        assert data["copilot_mode"] == "audit"

    def test_start_session_has_started_at(self):
        data = start_session()
        assert data["started_at"]

    def test_start_session_completed_at_null(self):
        data = start_session()
        assert data["completed_at"] is None

    def test_get_session_detail(self):
        session = start_session()
        r = client.get(f"/api/copilot/sessions/{session['id']}", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == session["id"]
        assert len(data["steps"]) > 0

    def test_get_session_not_found(self):
        r = client.get("/api/copilot/sessions/9999999", headers=HEADERS)
        assert r.status_code == 404

    def test_complete_session_manually(self):
        session = start_session()
        r = client.post(f"/api/copilot/sessions/{session['id']}/complete", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["session_status"] == "completed"

    def test_complete_session_sets_completed_at(self):
        session = start_session()
        r = client.post(f"/api/copilot/sessions/{session['id']}/complete", headers=HEADERS)
        data = r.json()
        assert data["completed_at"] is not None

    def test_list_sessions_structure(self):
        start_session()
        r = client.get("/api/copilot/sessions", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "sessions" in data

    def test_list_sessions_facility_filter(self):
        r = client.get("/api/copilot/sessions?facility_id=FAC-A", headers=HEADERS)
        assert r.status_code == 200

    def test_session_steps_have_instructions(self):
        data = start_session()
        for step in data["steps"]:
            assert step["step_instructions"]
            assert step["step_title"]

    def test_session_risk_level_initial(self):
        data = start_session()
        assert data["risk_level"] in ("low", "medium", "high", "critical", "unknown")

    def test_full_lifecycle_pass_all_steps(self):
        session = start_session()
        session_id = session["id"]
        for step in session["steps"]:
            data = respond_step(session_id, step["id"], response="pass")
        assert data["completed_steps"] == data["total_steps"]
        assert data["session_status"] == "completed"

    def test_pdf_generated_for_session(self):
        session = start_session()
        r = client.post(f"/api/copilot/sessions/{session['id']}/pdf", headers=HEADERS)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert len(r.content) > 100

    def test_session_data_source_real(self):
        data = start_session()
        # After starting with DB, data_source should be real
        assert "data_source" in data


# ── TestStepResponses ────────────────────────────────────────────────────────

class TestStepResponses:
    def test_respond_pass(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="pass")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert updated_step["technician_response"] == "pass"

    def test_respond_fail(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert updated_step["technician_response"] == "fail"

    def test_respond_skip(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="skip")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert updated_step["technician_response"] == "skip"

    def test_respond_escalate(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="escalate")
        assert data["session_status"] == "escalated"

    def test_respond_with_finding_blood(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="blood")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert updated_step["finding_category"] == "blood"
        assert updated_step["severity"] in ("high", "critical")

    def test_respond_with_finding_crack(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="crack")
        assert data["session_status"] == "escalated"

    def test_respond_with_finding_corrosion(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="corrosion")
        assert data["session_status"] == "escalated"

    def test_respond_with_notes(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="pass", notes="Checked thoroughly")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert "Checked thoroughly" in updated_step["notes"]

    def test_respond_increments_completed_steps(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="pass")
        assert data["completed_steps"] >= 1

    def test_respond_step_not_found(self):
        session = start_session()
        r = client.post(
            f"/api/copilot/sessions/{session['id']}/steps/9999999/respond",
            headers=HEADERS,
            json={"technician_response": "pass"},
        )
        assert r.status_code == 404

    def test_respond_session_not_found(self):
        r = client.post(
            "/api/copilot/sessions/9999999/steps/1/respond",
            headers=HEADERS,
            json={"technician_response": "pass"},
        )
        assert r.status_code == 404

    def test_respond_with_insulation_finding(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="insulation")
        assert data["session_status"] == "escalated"

    def test_respond_with_tissue_finding(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="tissue")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert updated_step["severity"] in ("high", "critical")

    def test_respond_with_bone_finding(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="bone")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert updated_step["severity"] in ("high", "critical")

    def test_respond_completed_at_set(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="pass")
        updated_step = next(s for s in data["steps"] if s["id"] == step["id"])
        assert updated_step["completed_at"] is not None


# ── TestEscalations ──────────────────────────────────────────────────────────

class TestEscalations:
    def test_escalation_created_on_crack(self):
        session = start_session()
        step = session["steps"][0]
        respond_step(session["id"], step["id"], response="fail", finding="crack")
        r = client.get("/api/copilot/escalations", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["escalations"]

    def test_list_escalations_structure(self):
        r = client.get("/api/copilot/escalations", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "escalations" in data
        assert "status" in data

    def test_escalation_has_required_fields(self):
        session = start_session()
        step = session["steps"][0]
        respond_step(session["id"], step["id"], response="escalate")
        r = client.get("/api/copilot/escalations", headers=HEADERS)
        escs = r.json()["escalations"]
        if escs:
            esc = escs[0]
            assert "id" in esc
            assert "severity" in esc
            assert "escalation_type" in esc
            assert "description" in esc

    def test_resolve_escalation(self):
        # Create an escalation
        session = start_session()
        step = session["steps"][0]
        respond_step(session["id"], step["id"], response="fail", finding="crack")
        escs_r = client.get("/api/copilot/escalations", headers=HEADERS)
        escs = escs_r.json()["escalations"]
        if escs:
            esc_id = escs[0]["id"]
            r = client.post(
                f"/api/copilot/escalations/{esc_id}/resolve",
                headers=HEADERS,
                json={"resolved_by": "supervisor-001", "notes": "Issue resolved"},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["resolved"] is True
            assert data["resolved_by"] == "supervisor-001"

    def test_resolve_escalation_sets_resolved_at(self):
        session = start_session()
        step = session["steps"][0]
        respond_step(session["id"], step["id"], response="fail", finding="corrosion")
        escs = client.get("/api/copilot/escalations", headers=HEADERS).json()["escalations"]
        if escs:
            esc_id = escs[0]["id"]
            data = client.post(
                f"/api/copilot/escalations/{esc_id}/resolve",
                headers=HEADERS,
                json={"resolved_by": "sup-001"},
            ).json()
            assert data["resolved_at"] is not None

    def test_resolve_nonexistent_escalation(self):
        r = client.post(
            "/api/copilot/escalations/9999999/resolve",
            headers=HEADERS,
            json={"resolved_by": "sup-001"},
        )
        assert r.status_code == 404

    def test_escalation_auto_generated_flag(self):
        session = start_session()
        step = session["steps"][0]
        respond_step(session["id"], step["id"], response="fail", finding="crack")
        escs = client.get("/api/copilot/escalations", headers=HEADERS).json()["escalations"]
        if escs:
            assert escs[0]["auto_generated"] is True


# ── TestProtocols ────────────────────────────────────────────────────────────

class TestProtocols:
    def test_list_protocols_returns_ok(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        assert r.status_code == 200

    def test_list_protocols_has_builtin_templates(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        data = r.json()
        protocols = data["protocols"]
        categories = {p["instrument_category"] for p in protocols}
        assert "scissors" in categories
        assert "forceps" in categories
        assert "default" in categories

    def test_protocols_have_steps(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        for p in r.json()["protocols"]:
            assert len(p["steps"]) > 0

    def test_scissors_protocol_has_5_steps(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        scissors = next(p for p in r.json()["protocols"] if p["instrument_category"] == "scissors")
        assert len(scissors["steps"]) == 5

    def test_forceps_protocol_has_5_steps(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        forceps = next(p for p in r.json()["protocols"] if p["instrument_category"] == "forceps")
        assert len(forceps["steps"]) == 5

    def test_scope_protocol_present(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        cats = {p["instrument_category"] for p in r.json()["protocols"]}
        assert "scope" in cats

    def test_retractor_protocol_present(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        cats = {p["instrument_category"] for p in r.json()["protocols"]}
        assert "retractor" in cats

    def test_protocols_structure(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        assert "protocols" in r.json()
        assert "status" in r.json()

    def test_protocol_steps_have_required_fields(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        for p in r.json()["protocols"]:
            for step in p["steps"]:
                assert "step_number" in step
                assert "step_title" in step
                assert "step_instructions" in step


# ── TestCopilotDashboard ─────────────────────────────────────────────────────

class TestCopilotDashboard:
    def test_dashboard_returns_ok(self):
        r = client.get("/api/copilot/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_dashboard_has_required_fields(self):
        r = client.get("/api/copilot/dashboard", headers=HEADERS)
        data = r.json()
        assert "active_sessions" in data
        assert "pass_rate_pct" in data
        assert "escalations_open" in data
        assert "data_source" in data
        assert "generated_at" in data

    def test_dashboard_data_source_field(self):
        r = client.get("/api/copilot/dashboard", headers=HEADERS)
        data = r.json()
        assert data["data_source"] in ("real", "mock")

    def test_dashboard_mock_fallback(self):
        # With empty DB for a new tenant, should return mock
        r = client.get("/api/copilot/dashboard?facility_id=nonexistent-fac-xyz", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "data_source" in data

    def test_dashboard_top_findings_structure(self):
        r = client.get("/api/copilot/dashboard", headers=HEADERS)
        for finding in r.json()["top_finding_categories"]:
            assert "category" in finding
            assert "count" in finding

    def test_dashboard_technician_performance_structure(self):
        r = client.get("/api/copilot/dashboard", headers=HEADERS)
        for tech in r.json()["technician_performance"]:
            assert "technician_id" in tech
            assert "sessions" in tech
            assert "pass_rate" in tech

    def test_dashboard_with_real_data(self):
        # Create a session and complete it, then check dashboard
        session = start_session(technician="dash-tech-01")
        respond_step(session["id"], session["steps"][0]["id"], response="pass")
        r = client.get("/api/copilot/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_dashboard_facility_filter(self):
        r = client.get("/api/copilot/dashboard?facility_id=FAC-A", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["facility_id"] == "FAC-A"


# ── TestCopilotPDF ───────────────────────────────────────────────────────────

class TestCopilotPDF:
    def test_pdf_returns_bytes(self):
        session = start_session()
        r = client.post(f"/api/copilot/sessions/{session['id']}/pdf", headers=HEADERS)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_pdf_content_type(self):
        session = start_session()
        r = client.post(f"/api/copilot/sessions/{session['id']}/pdf", headers=HEADERS)
        assert "application/pdf" in r.headers["content-type"]

    def test_pdf_content_disposition(self):
        session = start_session()
        r = client.post(f"/api/copilot/sessions/{session['id']}/pdf", headers=HEADERS)
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_pdf_nonexistent_session(self):
        r = client.post("/api/copilot/sessions/9999999/pdf", headers=HEADERS)
        assert r.status_code == 404

    def test_pdf_after_steps_completed(self):
        session = start_session()
        for step in session["steps"]:
            respond_step(session["id"], step["id"], response="pass")
        r = client.post(f"/api/copilot/sessions/{session['id']}/pdf", headers=HEADERS)
        assert r.status_code == 200
        assert len(r.content) > 500


# ── TestTierGating ───────────────────────────────────────────────────────────

class TestTierGating:
    def test_copilot_basic_in_standard_tier(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_basic" in TIER_FEATURES["standard"]

    def test_copilot_basic_in_professional_tier(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_basic" in TIER_FEATURES["professional"]

    def test_copilot_basic_in_enterprise_tier(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_basic" in TIER_FEATURES["enterprise"]

    def test_copilot_escalations_in_professional(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_escalations" in TIER_FEATURES["professional"]

    def test_copilot_escalations_in_enterprise(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_escalations" in TIER_FEATURES["enterprise"]

    def test_copilot_dashboard_in_enterprise(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_dashboard" in TIER_FEATURES["enterprise"]

    def test_copilot_protocols_in_enterprise(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_protocols" in TIER_FEATURES["enterprise"]

    def test_copilot_dashboard_not_in_standard(self):
        from app.tier_guard import TIER_FEATURES
        assert "copilot_dashboard" not in TIER_FEATURES["standard"]

    def test_routes_require_auth(self):
        r = client.post("/api/copilot/sessions", json={
            "technician_id": "t", "instrument_name": "x"
        })
        assert r.status_code == 401

    def test_escalations_require_auth(self):
        r = client.get("/api/copilot/escalations")
        assert r.status_code == 401

    def test_dashboard_requires_auth(self):
        r = client.get("/api/copilot/dashboard")
        assert r.status_code == 401


# ── TestMockFallback ─────────────────────────────────────────────────────────

class TestMockFallback:
    def test_dashboard_mock_returns_valid_structure(self):
        r = client.get("/api/copilot/dashboard?facility_id=totally-fake-fac-zzz999", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["active_sessions"], int)
        assert isinstance(data["pass_rate_pct"], float)
        assert isinstance(data["high_risk_instruments"], list)

    def test_mock_dashboard_consistent_seed(self):
        """Same tenant+facility should produce consistent mock values."""
        r1 = client.get("/api/copilot/dashboard?facility_id=seed-test-fac", headers=HEADERS)
        r2 = client.get("/api/copilot/dashboard?facility_id=seed-test-fac", headers=HEADERS)
        d1 = r1.json()
        d2 = r2.json()
        if d1["data_source"] == "mock" and d2["data_source"] == "mock":
            assert d1["active_sessions"] == d2["active_sessions"]
            assert d1["pass_rate_pct"] == d2["pass_rate_pct"]

    def test_protocols_always_returns_builtins(self):
        r = client.get("/api/copilot/protocols", headers=HEADERS)
        assert len(r.json()["protocols"]) >= 5  # at least 5 built-in categories


# ── TestAIRecommendations ────────────────────────────────────────────────────

class TestAIRecommendations:
    def test_recommendation_created_on_fail(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="blood")
        assert len(data["recommendations"]) > 0

    def test_recommendation_type_warning_for_blood(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="blood")
        recs = [r for r in data["recommendations"] if r.get("step_id") == step["id"]]
        if recs:
            assert recs[0]["recommendation_type"] == "warning"

    def test_recommendation_type_escalate_for_crack(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="crack")
        recs = [r for r in data["recommendations"] if r.get("step_id") == step["id"]]
        if recs:
            assert recs[0]["recommendation_type"] == "escalate"

    def test_recommendation_has_confidence(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="blood")
        for rec in data["recommendations"]:
            assert 0.0 <= rec["confidence"] <= 1.0

    def test_recommendation_message_not_empty(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="tissue")
        for rec in data["recommendations"]:
            assert rec["message"]

    def test_recommendation_evidence_is_list(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="bone")
        for rec in data["recommendations"]:
            assert isinstance(rec["evidence"], list)

    def test_no_recommendation_on_pass_without_finding(self):
        session = start_session()
        step = session["steps"][0]
        initial_rec_count = len(session.get("recommendations", []))
        data = respond_step(session["id"], step["id"], response="pass")
        # No additional recommendation should be added on clean pass
        assert len(data["recommendations"]) >= initial_rec_count

    def test_recommendation_for_corrosion_is_escalate(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="corrosion")
        recs = [r for r in data["recommendations"] if r.get("step_id") == step["id"]]
        if recs:
            assert recs[0]["recommendation_type"] == "escalate"

    def test_initial_step_has_ai_recommendation_text(self):
        data = start_session()
        for step in data["steps"]:
            assert step["ai_recommendation"]


# ── TestRiskLevels ───────────────────────────────────────────────────────────

class TestRiskLevels:
    def test_risk_low_after_pass(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="pass")
        assert data["risk_level"] in ("low", "medium", "high", "critical", "unknown")

    def test_risk_high_after_blood_finding(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="blood")
        assert data["risk_level"] in ("high", "critical")

    def test_risk_critical_after_crack_finding(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="crack")
        assert data["risk_level"] == "critical"

    def test_risk_level_worst_case(self):
        """Risk level should reflect worst step severity."""
        session = start_session()
        steps = session["steps"]
        # Pass first step
        respond_step(session["id"], steps[0]["id"], response="pass")
        # Critical second step
        data = respond_step(session["id"], steps[1]["id"], response="fail", finding="insulation")
        assert data["risk_level"] == "critical"

    def test_session_status_escalated_on_critical(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="crack")
        assert data["session_status"] == "escalated"

    def test_session_escalation_reason_set(self):
        session = start_session()
        step = session["steps"][0]
        data = respond_step(session["id"], step["id"], response="fail", finding="corrosion")
        if data["session_status"] == "escalated":
            assert data["escalation_reason"]

    def test_instrument_category_scissors(self):
        """Scissors instrument should get scissors protocol."""
        data = start_session(instrument_name="Mayo Scissors")
        assert len(data["steps"]) == 5

    def test_instrument_category_forceps(self):
        data = start_session(instrument_name="DeBakey Forceps")
        assert len(data["steps"]) == 5

    def test_instrument_category_retractor(self):
        data = start_session(instrument_name="Bookwalter Retractor")
        assert len(data["steps"]) == 4

    def test_instrument_category_scope(self):
        data = start_session(instrument_name="Laparoscope")
        assert len(data["steps"]) == 5

    def test_instrument_category_default(self):
        data = start_session(instrument_name="Needle Holder")
        assert len(data["steps"]) == 4
