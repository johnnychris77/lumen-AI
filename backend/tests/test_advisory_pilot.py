"""Advisor — Phase 7: Supervised Advisory Pilot & Human-AI Collaboration
tests.

Covers: recommendation presentation, technician interaction logging (with
reasons and timing), workflow impact analysis, clinical performance,
user feedback, safety monitoring, the pilot dashboard, success metrics,
the Production promotion gate's new evidence items, and audit trail
completeness.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.inspection import Inspection
from app.models.model_registry import ModelRegistryEntry
from app.services import (
    advisory_clinical_performance_service,
    advisory_pilot_dashboard_service,
    advisory_recommendation_service,
    advisory_safety_service,
    advisory_success_metrics_service,
    advisory_user_feedback_service,
    advisory_workflow_impact_service,
    workflow_state_service,
)
from app.services.ml import candidate_promotion
from app.services.ml.candidate_training import CANDIDATE_CLASSES

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _make_inspection(db) -> Inspection:
    insp = Inspection(tenant_id=TENANT, file_name="advisor-test.png")
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return insp


def _with_ai_analysis(db, insp) -> None:
    workflow_state_service.record_capture_and_analysis(db, insp=insp, tenant_id=TENANT, actor="system")
    db.commit()


class TestPresentRecommendation:
    def test_presents_supported_finding_with_disclaimer(self):
        result = advisory_recommendation_service.present_recommendation(
            predicted_class="debris", confidence=0.9, model_version="1.0",
            image_quality="Good", supported_classes=list(CANDIDATE_CLASSES),
        )
        assert result["supported_class"] == "debris"
        assert result["human_review_required"] is True
        assert result["abstained"] is False
        assert "not a definitive conclusion" in result["recommendation_disclaimer"]

    def test_abstains_on_low_confidence(self):
        result = advisory_recommendation_service.present_recommendation(
            predicted_class="debris", confidence=0.2, model_version="1.0",
            image_quality="Good", supported_classes=list(CANDIDATE_CLASSES),
        )
        assert result["abstained"] is True

    def test_abstains_on_unsupported_class(self):
        result = advisory_recommendation_service.present_recommendation(
            predicted_class="blood", confidence=0.95, model_version="1.0",
            image_quality="Good", supported_classes=["debris", "corrosion"],
        )
        assert result["supported_class"] is None
        assert result["abstained"] is True


class TestRecordInteraction:
    def test_accept_records_time_to_decision(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            _with_ai_analysis(db, insp)
            row = advisory_recommendation_service.record_interaction(
                db, tenant_id=TENANT, inspection_id=insp.id, model_id="m1", model_version="1",
                predicted_label="debris", confidence=0.9, decision="accepted",
                decided_by="tech1", decided_role="operator",
            )
            assert row.decision == "accepted"
            assert row.time_to_decision_seconds is not None
            assert row.time_to_decision_seconds >= 0
        finally:
            db.close()

    def test_reject_captures_reason(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            row = advisory_recommendation_service.record_interaction(
                db, tenant_id=TENANT, inspection_id=insp.id, predicted_label="corrosion", confidence=0.7,
                decision="rejected", reason_for_rejection="Image was blurry.",
                user_confidence_rating=4, decided_by="tech2",
            )
            assert row.decision == "rejected"
            assert row.reason_for_rejection == "Image was blurry."
            assert row.user_confidence_rating == 4
        finally:
            db.close()

    def test_unknown_decision_rejected(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            try:
                advisory_recommendation_service.record_interaction(
                    db, tenant_id=TENANT, inspection_id=insp.id, predicted_label="debris",
                    confidence=0.9, decision="ignored", decided_by="tech3",
                )
                assert False, "should have raised"
            except ValueError:
                pass
        finally:
            db.close()

    def test_no_ai_analysis_event_leaves_time_to_decision_none(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            row = advisory_recommendation_service.record_interaction(
                db, tenant_id=TENANT, inspection_id=insp.id, predicted_label="debris",
                confidence=0.9, decision="accepted", decided_by="tech4",
            )
            assert row.time_to_decision_seconds is None
        finally:
            db.close()


class TestWorkflowImpact:
    def test_adoption_rate_and_acceptance_override(self):
        db = SessionLocal()
        try:
            insp1 = _make_inspection(db)
            insp1.has_image = True
            insp2 = _make_inspection(db)
            insp2.has_image = True
            db.commit()

            advisory_recommendation_service.record_interaction(
                db, tenant_id=TENANT, inspection_id=insp1.id, model_id="wf-1", predicted_label="debris",
                confidence=0.9, decision="accepted", decided_by="tech1",
            )
            advisory_recommendation_service.record_interaction(
                db, tenant_id=TENANT, inspection_id=insp2.id, model_id="wf-1", predicted_label="corrosion",
                confidence=0.4, decision="rejected", reason_for_rejection="wrong", decided_by="tech2",
            )
            interactions = advisory_recommendation_service.list_interactions(db, TENANT, model_id="wf-1")
            rates = advisory_workflow_impact_service.acceptance_and_override_rates(interactions)
            assert rates["total_interactions"] == 2
            assert rates["accepted"] == 1
            assert rates["rejected"] == 1
            assert rates["acceptance_rate"] == 0.5

            interruptions = advisory_workflow_impact_service.workflow_interruptions(interactions)
            assert interruptions["interruption_count"] == 1

            adoption = advisory_workflow_impact_service.adoption_rate(db, TENANT)
            assert adoption["inspections_with_interaction"] >= 2
        finally:
            db.close()

    def test_training_requirements_flags_high_reject_rate(self):
        db = SessionLocal()
        try:
            for i in range(4):
                insp = _make_inspection(db)
                advisory_recommendation_service.record_interaction(
                    db, tenant_id=TENANT, inspection_id=insp.id, model_id="wf-2", predicted_label="debris",
                    confidence=0.9, decision="rejected" if i < 3 else "accepted",
                    reason_for_rejection="bad" if i < 3 else "", decided_by="tech-high-reject",
                )
            interactions = advisory_recommendation_service.list_interactions(db, TENANT, model_id="wf-2")
            flagged = advisory_workflow_impact_service.training_requirements(interactions)
            assert any(f["user"] == "tech-high-reject" for f in flagged)
        finally:
            db.close()


class TestClinicalPerformance:
    def test_unsupported_cases_and_abstentions(self):
        presentations = [
            advisory_recommendation_service.present_recommendation(
                predicted_class="debris", confidence=0.9, model_version="1",
                image_quality="Good", supported_classes=list(CANDIDATE_CLASSES),
            ),
            advisory_recommendation_service.present_recommendation(
                predicted_class="blood", confidence=0.9, model_version="1",
                image_quality="Good", supported_classes=list(CANDIDATE_CLASSES),
            ),
        ]
        unsupported = advisory_clinical_performance_service.unsupported_cases(presentations)
        assert len(unsupported) == 1
        abstentions = advisory_clinical_performance_service.model_abstentions(presentations)
        assert abstentions["abstentions"] == 1

    def test_performance_summary_composes_pilot_validation(self):
        result = advisory_clinical_performance_service.performance_summary([], [])
        assert "clinical_metrics" in result
        assert result["human_review_required"] is True


class TestUserFeedback:
    def test_record_and_summarize(self):
        db = SessionLocal()
        try:
            advisory_user_feedback_service.record_feedback(
                db, tenant_id=TENANT, submitted_by="t1", submitted_role="technician",
                ease_of_use=5, trust=4, suggestions="More context please.",
            )
            advisory_user_feedback_service.record_feedback(
                db, tenant_id=TENANT, submitted_by="s1", submitted_role="supervisor", trust=3,
            )
            summary = advisory_user_feedback_service.feedback_summary(db, TENANT)
            assert summary["total_responses"] >= 2
            assert summary["overall"]["trust"] is not None
            assert "technician" in summary["by_role"]
            assert "More context please." in summary["suggestions"]
        finally:
            db.close()


class TestSafetyMonitoring:
    def test_report_and_review_event(self):
        db = SessionLocal()
        try:
            event = advisory_safety_service.report_event(
                db, tenant_id=TENANT, model_id="safety-1", event_type="near_miss",
                description="Technician almost accepted a wrong recommendation.",
                severity="high", reported_by="sup1",
            )
            assert event.reviewed is False

            summary_before = advisory_safety_service.safety_summary(db, TENANT)
            assert summary_before["unreviewed_count"] >= 1
            assert advisory_safety_service.safety_objectives_achieved(db, TENANT) is False

            advisory_safety_service.review_event(db, event, reviewed_by="qa1", resolution_notes="Reviewed, no action needed.")
            summary_after = advisory_safety_service.safety_summary(db, TENANT)
            assert summary_after["unreviewed_count"] == summary_before["unreviewed_count"] - 1
        finally:
            db.close()

    def test_unknown_event_type_rejected(self):
        db = SessionLocal()
        try:
            try:
                advisory_safety_service.report_event(
                    db, tenant_id=TENANT, event_type="not_a_real_type", reported_by="x",
                )
                assert False, "should have raised"
            except ValueError:
                pass
        finally:
            db.close()


class TestPilotDashboard:
    def test_dashboard_composes_services(self):
        db = SessionLocal()
        try:
            result = advisory_pilot_dashboard_service.pilot_dashboard(db, TENANT)
            assert "adoption" in result
            assert "safety_events" in result
            assert "operational_impact" in result
            assert result["human_review_required"] is True
        finally:
            db.close()


class TestSuccessMetrics:
    def test_success_metrics_reproducible(self):
        db = SessionLocal()
        try:
            r1 = advisory_success_metrics_service.success_metrics(db, TENANT)
            r2 = advisory_success_metrics_service.success_metrics(db, TENANT)
            assert r1 == r2
            assert "reduction_in_missed_findings" in r1
            assert "system_availability" in r1
        finally:
            db.close()


class TestProductionPromotionGate:
    def test_checklist_reflects_real_evidence(self):
        db = SessionLocal()
        try:
            model = ModelRegistryEntry(
                tenant_id=TENANT, model_id="prod-gate-a", model_version="1",
                model_type="candidate_finding_multiclass", candidate_stage="Pilot",
            )
            db.add(model)
            db.commit()
            db.refresh(model)

            checklist = candidate_promotion.evaluate_production_checklist(db, model)
            assert checklist["safety_objectives_achieved"] is True
            assert checklist["customer_approval"] is False
            assert checklist["user_adoption_targets_met"] is False

            advisory_safety_service.report_event(
                db, tenant_id=TENANT, model_id="prod-gate-a", event_type="near_miss",
                reported_by="x", description="d",
            )
            checklist2 = candidate_promotion.evaluate_production_checklist(db, model)
            assert checklist2["safety_objectives_achieved"] is False

            model.customer_approved = True
            db.commit()
            checklist3 = candidate_promotion.evaluate_production_checklist(db, model)
            assert checklist3["customer_approval"] is True
        finally:
            db.close()

    def test_earlier_stages_unaffected_by_production_checklist(self):
        db = SessionLocal()
        try:
            model = ModelRegistryEntry(
                tenant_id=TENANT, model_id="prod-gate-b", model_version="1",
                model_type="candidate_finding_multiclass", candidate_stage="Experimental",
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            decision = candidate_promotion.evaluate_candidate_promotion(
                db, model=model, target_stage="Candidate", approver="reviewer1",
            )
            assert "customer_approval" not in decision["checklist"]
            assert "safety_objectives_achieved" not in decision["checklist"]
        finally:
            db.close()


class TestApiSurface:
    def test_pilot_governance_registration(self):
        r = client.post(
            "/api/advisory-pilot/governance",
            json={
                "facility_id": "advisor-facility-1", "organization": "Org B", "pilot_sponsor": "VP Ops",
                "clinical_lead": "Dr. X", "quality_lead": "QA Y", "product_owner": "PM Z",
                "engineering_lead": "Eng W", "success_criteria": "80% acceptance rate.",
                "pilot_duration_days": 90,
            },
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["pilot_sponsor"] == "VP Ops"
        assert body["pilot_duration_days"] == 90

        db = SessionLocal()
        try:
            events = db.query(AuditLog).filter(AuditLog.action_type == "advisory_pilot_governance_registered").all()
            assert len(events) >= 1
        finally:
            db.close()

    def test_present_and_respond_flow_with_audit(self):
        present = client.post(
            "/api/advisory-pilot/recommendations/present",
            json={"predicted_class": "debris", "confidence": 0.9, "model_version": "1.0", "image_quality": "Good"},
            headers=AUTH_ADMIN,
        )
        assert present.status_code == 200
        assert present.json()["recommendation_disclaimer"]

        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            inspection_id = insp.id
        finally:
            db.close()

        respond = client.post(
            "/api/advisory-pilot/recommendations/respond",
            json={
                "inspection_id": inspection_id, "predicted_label": "debris", "confidence": 0.9,
                "decision": "modified", "modified_to": "corrosion", "reviewer_comments": "Looked more like corrosion.",
                "user_confidence_rating": 3,
            },
            headers=AUTH_ADMIN,
        )
        assert respond.status_code == 201, respond.text
        assert respond.json()["decision"] == "modified"

        listing = client.get("/api/advisory-pilot/recommendations", headers=AUTH_ADMIN)
        assert listing.status_code == 200
        assert listing.json()["count"] >= 1

        db = SessionLocal()
        try:
            events = db.query(AuditLog).filter(AuditLog.action_type == "advisory_recommendation_modified").all()
            assert len(events) >= 1
        finally:
            db.close()

    def test_invalid_decision_returns_422(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            inspection_id = insp.id
        finally:
            db.close()
        r = client.post(
            "/api/advisory-pilot/recommendations/respond",
            json={"inspection_id": inspection_id, "predicted_label": "debris", "decision": "bogus"},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 422

    def test_workflow_impact_and_clinical_performance_endpoints(self):
        wf = client.get("/api/advisory-pilot/workflow-impact", headers=AUTH_ADMIN)
        assert wf.status_code == 200
        assert "adoption" in wf.json()

        cp = client.get("/api/advisory-pilot/clinical-performance", headers=AUTH_ADMIN)
        assert cp.status_code == 200
        assert "clinical_metrics" in cp.json()

    def test_feedback_endpoints(self):
        r = client.post(
            "/api/advisory-pilot/feedback",
            json={"submitted_by": "api-user", "submitted_role": "quality", "trust": 5, "suggestions": "Great tool."},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 201

        summary = client.get("/api/advisory-pilot/feedback/summary", headers=AUTH_ADMIN)
        assert summary.status_code == 200
        assert summary.json()["total_responses"] >= 1

    def test_safety_event_endpoints_and_audit(self):
        r = client.post(
            "/api/advisory-pilot/safety-events",
            json={"model_id": "api-safety", "event_type": "unsafe_recommendation", "description": "d", "severity": "high"},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 201, r.text
        event_id = r.json()["id"]

        db = SessionLocal()
        try:
            events = db.query(AuditLog).filter(AuditLog.action_type == "advisory_safety_event_reported").all()
            assert len(events) >= 1
        finally:
            db.close()

        review = client.post(
            f"/api/advisory-pilot/safety-events/{event_id}/review",
            json={"resolution_notes": "Confirmed safe after review."},
            headers=AUTH_ADMIN,
        )
        assert review.status_code == 200
        assert review.json()["reviewed"] is True

        summary = client.get("/api/advisory-pilot/safety-events/summary", headers=AUTH_ADMIN)
        assert summary.status_code == 200

    def test_dashboard_and_success_metrics_endpoints(self):
        dash = client.get("/api/advisory-pilot/dashboard", headers=AUTH_ADMIN)
        assert dash.status_code == 200
        assert "adoption" in dash.json()

        metrics = client.get("/api/advisory-pilot/success-metrics", headers=AUTH_ADMIN)
        assert metrics.status_code == 200
        assert "reduction_in_repeat_inspections" in metrics.json()

    def test_final_report_endpoint(self):
        db = SessionLocal()
        try:
            model = ModelRegistryEntry(
                tenant_id=TENANT, model_id="final-report-model", model_version="1",
                model_type="candidate_finding_multiclass", candidate_stage="Pilot",
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            model_db_id = model.id
        finally:
            db.close()

        r = client.get(
            "/api/advisory-pilot/final-report", params={"model_db_id": model_db_id}, headers=AUTH_ADMIN,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["model_id"] == "final-report-model"
        assert "production_promotion_checklist" in body
        assert "pilot_dashboard" in body

    def test_final_report_404_for_unknown_model(self):
        r = client.get(
            "/api/advisory-pilot/final-report", params={"model_db_id": 999999}, headers=AUTH_ADMIN,
        )
        assert r.status_code == 404
