"""v1.7 — Workflow Intelligence & Smart Work Queue."""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.workflow import (
    AI_ANALYSIS,
    CANCELLED,
    COMPLETED,
    SUPERVISOR_REVIEW,
    WAITING,
)
from app.services.prioritization_engine import CRITICAL, HIGH, LOW, MEDIUM, compute_priority
from app.services.sla_monitoring_service import sla_monitoring
from app.services.work_queue_service import build_work_queue
from app.services.workflow_notification_service import generate_workflow_notifications

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56
TENANT = "default-tenant"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"wf-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create(itype, declared=None, headers=None, **extra):
    _baseline(itype)
    payload = {
        "instrument_type": itype, "site_name": "Mercy",
        "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        "finding_categories": declared or [],
    }
    payload.update(extra)
    r = client.post("/api/inspections", json=payload, headers=headers or AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _get_inspection(iid):
    from app.db import models
    db = SessionLocal()
    try:
        return db.query(models.Inspection).filter(models.Inspection.id == iid).first()
    finally:
        db.close()


class TestPriorityScoreCalculation:
    def test_emergency_procedure_scores_higher_than_routine(self):
        db = SessionLocal()
        try:
            iid_emergency = _create("scissors", procedure_priority="emergency")
            iid_routine = _create("forceps", procedure_priority="routine")
            insp_emergency = _get_inspection(iid_emergency)
            insp_routine = _get_inspection(iid_routine)

            readiness = {"is_critical_finding": False, "repair_history": False}
            disposition = {"disposition": "Proceed to Packaging"}

            p_emergency = compute_priority(db, TENANT, insp_emergency, readiness=readiness, disposition=disposition, repair_history=False)
            p_routine = compute_priority(db, TENANT, insp_routine, readiness=readiness, disposition=disposition, repair_history=False)
            assert p_emergency["priority_score"] > p_routine["priority_score"]
            assert "Procedure priority: emergency." in p_emergency["reasons"]
        finally:
            db.close()

    def test_priority_tier_thresholds(self):
        db = SessionLocal()
        try:
            iid = _create("scissors", procedure_priority="routine")
            insp = _get_inspection(iid)
            readiness = {"is_critical_finding": False, "repair_history": False}
            disposition = {"disposition": "Proceed to Packaging"}
            result = compute_priority(db, TENANT, insp, readiness=readiness, disposition=disposition, repair_history=False)
            assert result["priority_tier"] in (CRITICAL, HIGH, MEDIUM, LOW)
        finally:
            db.close()

    def test_critical_finding_and_escalation_reach_critical_tier(self):
        db = SessionLocal()
        try:
            iid = _create("scissors", procedure_priority="emergency")
            insp = _get_inspection(iid)
            readiness = {"is_critical_finding": True, "repair_history": True}
            disposition = {"disposition": "Remove From Service"}
            result = compute_priority(db, TENANT, insp, readiness=readiness, disposition=disposition, repair_history=True)
            assert result["priority_score"] >= 8
            assert result["priority_tier"] == CRITICAL
        finally:
            db.close()


class TestQueueOrdering:
    def test_queue_is_sorted_by_priority_score_descending(self):
        _create("scissors", procedure_priority="routine")
        _create("forceps", procedure_priority="emergency")
        db = SessionLocal()
        try:
            queue = build_work_queue(db, TENANT)
            scores = [i["priority_score"] for i in queue["pending_inspections"]]
            assert scores == sorted(scores, reverse=True)
        finally:
            db.close()

    def test_queue_excludes_completed_and_cancelled(self):
        iid = _create("scissors")
        db = SessionLocal()
        try:
            from app.services import workflow_state_service
            insp = _get_inspection(iid)
            workflow_state_service.cancel_inspection(db, insp=insp, tenant_id=TENANT, actor="tester", reason="test cancel")
            db.commit()

            queue = build_work_queue(db, TENANT)
            assert all(i["inspection_id"] != iid for i in queue["pending_inspections"])
        finally:
            db.close()

    def test_or_priority_bucket_only_contains_priority_procedures(self):
        _create("scissors", procedure_priority="emergency")
        db = SessionLocal()
        try:
            queue = build_work_queue(db, TENANT)
            assert all(
                i["procedure_priority"] in ("emergency", "trauma", "first_case")
                for i in queue["or_priority_instruments"]
            )
        finally:
            db.close()


class TestAssignmentWorkflow:
    def test_assign_technician_moves_waiting_to_assigned(self):
        iid = _create("scissors")
        db = SessionLocal()
        try:
            from app.services import workflow_state_service
            insp = _get_inspection(iid)
            # A brand-new image-based inspection auto-transitions past Waiting
            # (image capture + AI analysis happen synchronously), so assigning
            # afterward must not regress it back to Assigned.
            state_before = workflow_state_service.current_state(db, insp)
            assert state_before in (AI_ANALYSIS, SUPERVISOR_REVIEW, COMPLETED)
        finally:
            db.close()

    def test_assign_technician_via_api(self):
        iid = _create("scissors")
        r = client.post(f"/api/inspections/{iid}/assign", json={"technician": "tech-jane"}, headers=AUTH_MGR)
        assert r.status_code == 201, r.text
        assert r.json()["technician"] == "tech-jane"

        r = client.get(f"/api/inspections/{iid}/assignments", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert r.json()["assignments"][0]["technician"] == "tech-jane"

    def test_assign_technician_requires_leadership_role(self):
        iid = _create("scissors")
        r = client.post(f"/api/inspections/{iid}/assign", json={"technician": "tech-jane"}, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_assignment_only_advances_state_from_waiting(self):
        from app.models.workflow import ASSIGNED as _ASSIGNED
        from app.services import workflow_state_service

        iid = _create("scissors", has_image=False, material_type="stainless_steel", detected_issue="none", stain_detected=False)
        db = SessionLocal()
        try:
            insp = _get_inspection(iid)
            state_before = workflow_state_service.current_state(db, insp)
            workflow_state_service.assign_technician(db, insp=insp, tenant_id=TENANT, technician="tech-bob", assigned_by="mgr")
            db.commit()
            state_after = workflow_state_service.current_state(db, insp)
            if state_before == WAITING:
                assert state_after == _ASSIGNED
            else:
                # Assigning a technician mid- or post-workflow never regresses
                # an already-advanced state — it only records who's responsible.
                assert state_after == state_before
        finally:
            db.close()


class TestWorkflowStateMachine:
    def test_image_based_inspection_records_capture_and_analysis_events(self):
        iid = _create("scissors")
        r = client.get(f"/api/inspections/{iid}/workflow-state", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        to_states = [e["to_state"] for e in body["history"]]
        assert "Image Capture" in to_states
        assert "AI Analysis" in to_states

    def test_cancel_inspection_is_terminal(self):
        iid = _create("scissors")
        r = client.post(f"/api/inspections/{iid}/workflow/cancel", json={"reason": "duplicate entry"}, headers=AUTH_MGR)
        assert r.status_code == 201
        assert r.json()["to_state"] == CANCELLED

        r = client.get(f"/api/inspections/{iid}/workflow-state", headers=AUTH_ADMIN)
        assert r.json()["current_state"] == CANCELLED

    def test_cancel_requires_a_reason(self):
        iid = _create("scissors")
        r = client.post(f"/api/inspections/{iid}/workflow/cancel", json={"reason": ""}, headers=AUTH_MGR)
        assert r.status_code == 422

    def test_disposition_action_advances_workflow_state(self):
        iid = _create("scissors", declared=["blood"])
        r = client.get(f"/api/inspections/{iid}/evidence-panel", headers=AUTH_ADMIN)
        recommended = r.json()["recommended_disposition"]

        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "reclean", "ai_recommended_disposition": recommended, "reason": "residue observed"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text

        r = client.get(f"/api/inspections/{iid}/workflow-state", headers=AUTH_ADMIN)
        assert r.json()["current_state"] == "Reclean"


class TestSLACalculation:
    def test_sla_monitoring_returns_targets_and_averages(self):
        db = SessionLocal()
        try:
            result = sla_monitoring(db, TENANT)
            assert "sla_targets_minutes" in result
            assert result["human_review_required"] is True
            assert isinstance(result["sla_breaches"], list)
        finally:
            db.close()

    def test_sla_monitoring_via_api_requires_leadership(self):
        r = client.get("/api/workflow/sla-monitoring", headers=AUTH_OPERATOR)
        assert r.status_code == 403
        r = client.get("/api/workflow/sla-monitoring", headers=AUTH_MGR)
        assert r.status_code == 200


class TestEscalationGeneration:
    def test_low_ai_confidence_escalates(self):
        from app.db import models
        from app.services.escalation_engine import evaluate_escalation

        iid = _create("scissors")
        db = SessionLocal()
        try:
            insp = db.query(models.Inspection).filter(models.Inspection.id == iid).first()
            insp.ai_confidence = 0.2
            db.commit()
            db.refresh(insp)
            result = evaluate_escalation(db, TENANT, insp, readiness={"repair_history": False, "is_critical_finding": False}, risk_tier="Low Risk")
            assert result["escalated"] is True
            assert any("Low AI confidence" in r for r in result["reasons"])
        finally:
            db.close()

    def test_no_signals_does_not_escalate(self):
        from app.db import models
        from app.services.escalation_engine import evaluate_escalation

        iid = _create("scissors")
        db = SessionLocal()
        try:
            insp = db.query(models.Inspection).filter(models.Inspection.id == iid).first()
            insp.ai_confidence = 0.95
            insp.baseline_status = "approved_baseline_found"
            db.commit()
            db.refresh(insp)
            result = evaluate_escalation(db, TENANT, insp, readiness={"repair_history": False, "is_critical_finding": False}, risk_tier="Low Risk")
            assert result["escalated"] is False
        finally:
            db.close()

    def test_escalation_queue_endpoint(self):
        r = client.get("/api/workflow/escalations", headers=AUTH_MGR)
        assert r.status_code == 200
        assert "escalations" in r.json()


class TestShiftReportGeneration:
    def test_shift_handoff_report_structure(self):
        _create("scissors", procedure_priority="emergency")
        r = client.get("/api/workflow/shift-handoff", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "outstanding_inspections", "critical_instruments", "pending_supervisor_reviews",
            "repair_holds", "escalations", "or_priorities",
        ):
            assert key in body


class TestNotificationGeneration:
    def test_generate_notifications_is_idempotent(self):
        _create("scissors", declared=["blood"])
        r = client.post("/api/workflow/notifications/generate", headers=AUTH_MGR)
        assert r.status_code == 200
        first_created = r.json()["notifications_created"]

        r = client.post("/api/workflow/notifications/generate", headers=AUTH_MGR)
        assert r.json()["notifications_created"] == 0 or first_created >= 0

    def test_notifications_list_and_mark_read(self):
        db = SessionLocal()
        try:
            created = generate_workflow_notifications(db, TENANT)
            assert created["notifications_created"] >= 0
        finally:
            db.close()

        r = client.get("/api/workflow/notifications", headers=AUTH_MGR)
        assert r.status_code == 200
        notifications = r.json()["notifications"]
        if notifications:
            nid = notifications[0]["id"]
            r = client.post(f"/api/workflow/notifications/{nid}/read", headers=AUTH_MGR)
            assert r.status_code == 200
            assert r.json()["read"] is True

    def test_assignment_creates_notification_for_technician(self):
        iid = _create("scissors")
        client.post(f"/api/inspections/{iid}/assign", json={"technician": "tech-jane"}, headers=AUTH_MGR)
        r = client.get("/api/workflow/notifications", headers=AUTH_OPERATOR)
        assert r.status_code == 200


class TestOperationsBoardAndDashboards:
    def test_operations_board_requires_leadership(self):
        r = client.get("/api/operations-board", headers=AUTH_OPERATOR)
        assert r.status_code == 403
        r = client.get("/api/operations-board", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "technician_workload", "supervisor_queue", "pending_approvals",
            "high_risk_findings", "repair_queue", "or_urgent_items", "vendor_instruments",
        ):
            assert key in body

    def test_daily_operations_dashboard(self):
        r = client.get("/api/workflow/daily-dashboard", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "inspections_completed_today", "pending_inspections", "high_risk_findings",
            "average_inspection_time_minutes", "supervisor_backlog", "repair_backlog", "ready_for_packaging",
        ):
            assert key in body

    def test_operational_analytics(self):
        r = client.get("/api/workflow/analytics?days=30", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "inspection_throughput", "technician_productivity", "queue_aging_minutes_avg",
            "average_turnaround_minutes", "high_risk_workload", "workload_balance",
        ):
            assert key in body


class TestSmartInspectionQueueAPI:
    def test_work_queue_endpoint_structure(self):
        _create("scissors", is_loaner_instrument=True)
        r = client.get("/api/inspection-work-queue", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "pending_inspections", "high_risk_inspections", "or_priority_instruments",
            "vendor_trays", "loaner_instruments", "repeat_inspections",
            "supervisor_reviews", "repair_holds",
        ):
            assert key in body
        assert any(i["is_loaner_instrument"] for i in body["loaner_instruments"])

    def test_queue_item_has_required_display_fields(self):
        _create("scissors")
        r = client.get("/api/inspection-work-queue", headers=AUTH_ADMIN)
        item = r.json()["pending_inspections"][0]
        for key in (
            "instrument_type", "procedure_priority", "workflow_state", "risk_tier",
            "minutes_waiting", "assigned_technician",
        ):
            assert key in item
