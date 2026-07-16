"""Shadow — Phase 6: Prospective Shadow-Mode Clinical Validation tests.

Covers: the reveal gate (predictions hidden until workflow completion),
the AI comparison engine, ground truth collection, the error review queue,
failure analysis, the performance dashboard, drift monitoring, validation
metrics, safety monitoring, the clinical review board, reproducible
reports, the Validated Candidate promotion gate's new evidence items, and
audit trail completeness.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.inspection import Inspection
from app.models.model_registry import ModelRegistryEntry
from app.models.shadow_prediction import ShadowPrediction
from app.models.shadow_validation import ShadowGroundTruth
from app.services import workflow_state_service
from app.services.ml import (
    candidate_promotion,
    shadow_clinical_review_board,
    shadow_comparison_engine,
    shadow_dashboard,
    shadow_drift_monitor,
    shadow_error_review_queue,
    shadow_failure_analysis,
    shadow_ground_truth,
    shadow_mode,
    shadow_reports,
    shadow_safety_monitor,
    shadow_validation_metrics,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _make_inspection(db) -> Inspection:
    insp = Inspection(tenant_id=TENANT, file_name="shadow-test.png")
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return insp


def _finalize(db, insp) -> None:
    workflow_state_service.record_disposition_action(
        db, insp=insp, tenant_id=TENANT, action="approve", actor="supervisor",
    )
    db.commit()


def _make_shadow(
    db, *, model_id="dash-model", predicted_label="debris", confidence="0.9",
    final_label="debris", facility_id="F1", instrument_family="scissors",
    anatomy_zone="hinge", image_quality="Good", revealed=True,
) -> ShadowPrediction:
    row = ShadowPrediction(
        tenant_id=TENANT, model_id=model_id, model_version="1",
        model_type="candidate_finding_multiclass", predicted_label=predicted_label,
        predicted_confidence=confidence, supervisor_final_label=final_label,
        agreed_with_human=(predicted_label == final_label),
        comparison_category=shadow_comparison_engine.classify_comparison(
            predicted_label=predicted_label, human_final_label=final_label, confidence=float(confidence),
        ),
        facility_id=facility_id, instrument_family=instrument_family, anatomy_zone=anatomy_zone,
        image_quality=image_quality, revealed=revealed,
        revealed_at=datetime.now(timezone.utc) if revealed else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


class TestRevealGate:
    def test_prediction_hidden_until_workflow_completed(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            row = shadow_mode.record_shadow_prediction(
                db, tenant_id=TENANT, model_id="reveal-1", model_version="1",
                model_type="candidate_finding_multiclass", predicted_label="debris",
                predicted_confidence="0.9", inspection_id=insp.id,
            )
            assert row.revealed is False

            row = shadow_mode.reveal_if_finalized(db, row, insp=insp, final_label="debris")
            assert row.revealed is False
            assert row.comparison_category == ""

            _finalize(db, insp)
            row = shadow_mode.reveal_if_finalized(db, row, insp=insp, final_label="debris")
            assert row.revealed is True
            assert row.revealed_at is not None
            assert row.comparison_category == "agreement"
            assert row.agreed_with_human is True
        finally:
            db.close()

    def test_reveal_is_noop_without_an_inspection(self):
        db = SessionLocal()
        try:
            row = shadow_mode.record_shadow_prediction(
                db, tenant_id=TENANT, model_id="reveal-2", model_version="1",
                model_type="candidate_finding_multiclass", predicted_label="debris",
                predicted_confidence="0.9",
            )
            row = shadow_mode.reveal_if_finalized(db, row, insp=None, final_label="debris")
            assert row.revealed is False
        finally:
            db.close()

    def test_public_view_never_exposes_predicted_label(self):
        db = SessionLocal()
        try:
            row = shadow_mode.record_shadow_prediction(
                db, tenant_id=TENANT, model_id="reveal-3", model_version="1",
                model_type="candidate_finding_multiclass", predicted_label="blood",
                predicted_confidence="0.9",
            )
            view = shadow_mode.public_view(row)
            assert "predicted_label" not in view
            assert "blood" not in str(view)
            assert view["clinical_recommendation_shown"] is False
        finally:
            db.close()


class TestErrorReviewQueue:
    def test_disagreement_auto_routes_to_queue(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            row = shadow_mode.record_shadow_prediction(
                db, tenant_id=TENANT, model_id="queue-1", model_version="1",
                model_type="candidate_finding_multiclass", predicted_label="debris",
                predicted_confidence="0.9", inspection_id=insp.id,
            )
            _finalize(db, insp)
            row = shadow_mode.reveal_if_finalized(db, row, insp=insp, final_label="no_actionable_finding")
            assert row.comparison_category == "false_positive"

            items = shadow_error_review_queue.list_queue(db, TENANT, status="open")
            assert any(i.shadow_prediction_id == row.id for i in items)
        finally:
            db.close()

    def test_agreement_never_queued(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            row = shadow_mode.record_shadow_prediction(
                db, tenant_id=TENANT, model_id="queue-2", model_version="1",
                model_type="candidate_finding_multiclass", predicted_label="debris",
                predicted_confidence="0.9", inspection_id=insp.id,
            )
            _finalize(db, insp)
            row = shadow_mode.reveal_if_finalized(db, row, insp=insp, final_label="debris")
            assert shadow_error_review_queue.route_if_disagreement(db, row) is None
        finally:
            db.close()

    def test_resolve_item(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            row = shadow_mode.record_shadow_prediction(
                db, tenant_id=TENANT, model_id="queue-3", model_version="1",
                model_type="candidate_finding_multiclass", predicted_label="corrosion",
                predicted_confidence="0.9", inspection_id=insp.id,
            )
            _finalize(db, insp)
            row = shadow_mode.reveal_if_finalized(db, row, insp=insp, final_label="debris")
            item = shadow_error_review_queue.list_queue(db, TENANT, status="open")[0]
            resolved = shadow_error_review_queue.resolve_item(
                db, item, resolved_by="reviewer1", reviewer_comments="Reviewed.",
                failure_classification="model_limitation",
            )
            assert resolved.status == "resolved"
            assert resolved.resolved_by == "reviewer1"
        finally:
            db.close()


class TestComparisonEngine:
    def test_agreement(self):
        assert shadow_comparison_engine.classify_comparison(
            predicted_label="debris", human_final_label="debris", confidence=0.9,
        ) == "agreement"

    def test_low_confidence_agreement(self):
        assert shadow_comparison_engine.classify_comparison(
            predicted_label="debris", human_final_label="debris", confidence=0.3,
        ) == "low_confidence"

    def test_false_positive(self):
        assert shadow_comparison_engine.classify_comparison(
            predicted_label="debris", human_final_label="no_actionable_finding", confidence=0.9,
        ) == "false_positive"

    def test_false_negative(self):
        assert shadow_comparison_engine.classify_comparison(
            predicted_label="no_actionable_finding", human_final_label="debris", confidence=0.9,
        ) == "false_negative"

    def test_disagreement_between_findings(self):
        assert shadow_comparison_engine.classify_comparison(
            predicted_label="debris", human_final_label="corrosion", confidence=0.9,
        ) == "disagreement"

    def test_unknown_pattern_missing_data(self):
        assert shadow_comparison_engine.classify_comparison(
            predicted_label="", human_final_label="debris", confidence=0.9,
        ) == "unknown_pattern"


class TestGroundTruth:
    def test_full_chain_and_adjudication(self):
        db = SessionLocal()
        try:
            row = shadow_ground_truth.record_technician_finding(
                db, tenant_id=TENANT, inspection_id=101, technician_finding="debris", technician_name="tech1",
            )
            assert shadow_ground_truth.is_locked(row) is False
            assert shadow_ground_truth.final_finding(row) == ""

            row = shadow_ground_truth.record_supervisor_finding(
                db, row, supervisor_finding="corrosion", supervisor_name="sup1",
            )
            assert shadow_ground_truth.is_locked(row) is True
            assert shadow_ground_truth.final_finding(row) == "corrosion"

            row = shadow_ground_truth.record_adjudication(
                db, row, final_adjudicated_finding="debris", adjudicator_name="adj1",
                reason_for_correction="Supervisor missed a zone.", supporting_evidence="photo-ref-1",
            )
            assert shadow_ground_truth.final_finding(row) == "debris"
            assert row.reason_for_correction == "Supervisor missed a zone."
        finally:
            db.close()

    def test_record_technician_finding_upserts_same_inspection(self):
        db = SessionLocal()
        try:
            row1 = shadow_ground_truth.record_technician_finding(
                db, tenant_id=TENANT, inspection_id=202, technician_finding="debris", technician_name="tech1",
            )
            row2 = shadow_ground_truth.record_technician_finding(
                db, tenant_id=TENANT, inspection_id=202, technician_finding="corrosion", technician_name="tech2",
            )
            assert row1.id == row2.id
            assert row2.technician_finding == "corrosion"
        finally:
            db.close()


class TestFailureAnalysis:
    def test_reuses_genesis_signals_and_adds_shadow_refinements(self):
        samples = [
            {"id": 1, "true_label": "debris", "predicted_label": "corrosion", "confidence": 0.9, "blur_flag": True},
            {"id": 2, "true_label": "debris", "predicted_label": "corrosion", "confidence": 0.9,
             "workflow_anomaly": True, "anatomy_zone": "hinge"},
            {"id": 3, "true_label": "debris", "predicted_label": "corrosion", "confidence": 0.9, "anatomy_zone": "hinge"},
            {"id": 4, "true_label": "debris", "predicted_label": "debris", "confidence": 0.9},
        ]
        result = shadow_failure_analysis.analyze_failures(samples)
        assert result["total_failures"] == 3
        causes = {f["failure_classification"] for f in result["failures"]}
        assert causes == {"poor_image_quality", "workflow_issue", "model_limitation"}


class TestDashboard:
    def test_performance_dashboard_computes_real_metrics(self):
        db = SessionLocal()
        try:
            _make_shadow(db, model_id="dash-a", predicted_label="debris", final_label="debris", facility_id="FA")
            _make_shadow(db, model_id="dash-a", predicted_label="debris", final_label="debris", facility_id="FA")
            _make_shadow(db, model_id="dash-a", predicted_label="corrosion", final_label="no_actionable_finding", facility_id="FB")
            _make_shadow(db, model_id="dash-a", predicted_label="no_actionable_finding", final_label="debris", facility_id="FB")
            rows = db.query(ShadowPrediction).filter(ShadowPrediction.model_id == "dash-a").all()
            result = shadow_dashboard.performance_dashboard(rows)
            assert result["total_reconciled"] == 4
            assert result["false_positives"] == 1
            assert result["false_negatives"] == 1
            assert result["agreement_rate"] == 0.5
            assert "FA" in result["performance_by_facility"]
            assert result["human_review_required"] is True
        finally:
            db.close()


class TestDriftMonitor:
    def test_assess_drift_reports_distributions(self):
        db = SessionLocal()
        try:
            _make_shadow(db, model_id="drift-a", predicted_label="debris", final_label="debris", facility_id="FA")
            _make_shadow(db, model_id="drift-a", predicted_label="corrosion", final_label="corrosion", facility_id="FB")
            rows = db.query(ShadowPrediction).filter(ShadowPrediction.model_id == "drift-a").all()
            result = shadow_drift_monitor.assess_drift(db, TENANT, rows)
            assert "drift_detected" in result
            assert result["prediction_distribution"]["debris"] == 1
            assert result["facility_variation"]["FA"] == 1
        finally:
            db.close()


class TestValidationMetrics:
    def test_validated_metrics_and_shadow_go_no_go(self):
        db = SessionLocal()
        try:
            for _ in range(35):
                _make_shadow(db, model_id="vm-a", predicted_label="debris", final_label="debris")
            rows = db.query(ShadowPrediction).filter(ShadowPrediction.model_id == "vm-a").all()
            metrics = shadow_validation_metrics.validated_metrics(rows)
            assert metrics["agreement_rate"] == 1.0
            assert metrics["sample_count"] == 35

            gng = shadow_validation_metrics.shadow_go_no_go(rows)
            assert gng["decision"] == "GO"
            assert gng["inspection_volume_achieved"] is True
            assert gng["performance_targets_met"] is True
        finally:
            db.close()

    def test_shadow_go_no_go_blocks_on_insufficient_volume(self):
        result = shadow_validation_metrics.shadow_go_no_go([])
        assert result["decision"] == "NO-GO"
        assert result["inspection_volume_achieved"] is False

    def test_inter_reviewer_agreement(self):
        db = SessionLocal()
        try:
            gt = shadow_ground_truth.record_technician_finding(
                db, tenant_id=TENANT, inspection_id=303, technician_finding="debris", technician_name="t",
            )
            shadow_ground_truth.record_supervisor_finding(db, gt, supervisor_finding="debris", supervisor_name="s")
            rows = db.query(ShadowGroundTruth).filter(ShadowGroundTruth.tenant_id == TENANT).all()
            result = shadow_validation_metrics.inter_reviewer_agreement(rows)
            assert result["n"] >= 1
            assert result["agreement_rate"] is not None
        finally:
            db.close()


class TestSafetyMonitor:
    def test_safety_report_flags_missed_finding_and_out_of_scope(self):
        db = SessionLocal()
        try:
            _make_shadow(
                db, model_id="safety-a", predicted_label="no_actionable_finding",
                final_label="blood", image_quality="Reject",
            )
            rows = db.query(ShadowPrediction).filter(ShadowPrediction.model_id == "safety-a").all()
            report = shadow_safety_monitor.safety_monitor_report(
                rows, candidate_classes=["debris", "corrosion", "no_actionable_finding", "blood"],
                supported_classes=["debris", "corrosion", "no_actionable_finding"],
            )
            assert len(report["potential_unsafe_recommendations"]) == 1
            assert len(report["missed_findings"]) == 1
            assert len(report["out_of_scope_images"]) == 1
            assert report["human_review_required"] is True
        finally:
            db.close()


class TestClinicalReviewBoard:
    def test_record_and_check_approval(self):
        db = SessionLocal()
        try:
            row = shadow_clinical_review_board.record_review_session(
                db, tenant_id=TENANT, model_id="board-a", model_version="1",
                reviewers=[{"name": "a", "role": "quality"}], readiness_assessment="Ready.",
                approved=True, decided_by="chair",
            )
            assert shadow_clinical_review_board.board_approved(
                db, tenant_id=TENANT, model_id="board-a", model_version="1",
            ) is True
            as_dict = shadow_clinical_review_board.as_dict(row)
            assert as_dict["approved"] is True
            assert as_dict["reviewers"] == [{"name": "a", "role": "quality"}]
        finally:
            db.close()

    def test_not_approved_when_no_session_exists(self):
        db = SessionLocal()
        try:
            assert shadow_clinical_review_board.board_approved(
                db, tenant_id=TENANT, model_id="board-nonexistent",
            ) is False
        finally:
            db.close()


class TestReportsReproducible:
    def test_performance_summary_is_reproducible(self):
        db = SessionLocal()
        try:
            _make_shadow(db, model_id="report-a", predicted_label="debris", final_label="debris")
            rows = db.query(ShadowPrediction).filter(ShadowPrediction.model_id == "report-a").all()
            r1 = shadow_reports.performance_summary(rows)
            r2 = shadow_reports.performance_summary(rows)
            r1.pop("generated_at")
            r2.pop("generated_at")
            assert r1 == r2
            assert r1["report_type"] == "performance_summary"
        finally:
            db.close()


class TestPromotionGateShadowEvidence:
    def test_validated_candidate_checklist_reflects_real_evidence(self):
        db = SessionLocal()
        try:
            model = ModelRegistryEntry(
                tenant_id=TENANT, model_id="gate-a", model_version="1",
                model_type="candidate_finding_multiclass", candidate_stage="Candidate",
            )
            db.add(model)
            db.commit()
            db.refresh(model)

            checklist = candidate_promotion.evaluate_validated_candidate_checklist(db, model)
            assert checklist["inspection_volume_achieved"] is False
            assert checklist["clinical_review_board_approved"] is False

            for _ in range(30):
                _make_shadow(db, model_id="gate-a", predicted_label="debris", final_label="debris")
            shadow_clinical_review_board.record_review_session(
                db, tenant_id=TENANT, model_id="gate-a", model_version="1",
                reviewers=[{"name": "a", "role": "quality"}], approved=True, decided_by="chair",
            )
            checklist2 = candidate_promotion.evaluate_validated_candidate_checklist(db, model)
            assert checklist2["inspection_volume_achieved"] is True
            assert checklist2["performance_targets_met"] is True
            assert checklist2["clinical_review_board_approved"] is True
            assert checklist2["model_drift_acceptable"] is True
        finally:
            db.close()

    def test_candidate_stage_promotion_unaffected_by_shadow_gate(self):
        """The Experimental -> Candidate transition Genesis's own tests
        exercise must not require any Shadow evidence."""
        db = SessionLocal()
        try:
            model = ModelRegistryEntry(
                tenant_id=TENANT, model_id="gate-b", model_version="1",
                model_type="candidate_finding_multiclass", candidate_stage="Experimental",
                dataset_version_id=None,
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            decision = candidate_promotion.evaluate_candidate_promotion(
                db, model=model, target_stage="Candidate", approver="reviewer1",
            )
            assert "inspection_volume_achieved" not in decision["checklist"]
        finally:
            db.close()


class TestApiSurface:
    def test_pilot_site_registration_and_audit(self):
        r = client.post(
            "/api/shadow-validation/pilot-sites",
            json={
                "facility_id": "api-facility-1", "organization": "Org A", "department": "SPD",
                "clinical_lead": "Dr. A", "technical_lead": "Tech B", "quality_lead": "QA C",
                "validation_coordinator": "Coord D",
            },
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["clinical_lead"] == "Dr. A"

        get_r = client.get("/api/shadow-validation/pilot-sites/api-facility-1", headers=AUTH_ADMIN)
        assert get_r.status_code == 200
        assert get_r.json()["organization"] == "Org A"

        db = SessionLocal()
        try:
            events = db.query(AuditLog).filter(AuditLog.action_type == "shadow_pilot_site_registered").all()
            assert len(events) >= 1
        finally:
            db.close()

    def test_ground_truth_api_flow(self):
        r = client.post(
            "/api/shadow-validation/ground-truth",
            json={"inspection_id": 404, "technician_finding": "debris", "technician_name": "tech1"},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 201, r.text
        gt_id = r.json()["id"]

        sup = client.patch(
            f"/api/shadow-validation/ground-truth/{gt_id}/supervisor-finding",
            json={"supervisor_finding": "corrosion", "supervisor_name": "sup1"},
            headers=AUTH_ADMIN,
        )
        assert sup.status_code == 200
        assert sup.json()["final_finding"] == "corrosion"

        adj = client.patch(
            f"/api/shadow-validation/ground-truth/{gt_id}/adjudication",
            json={"final_adjudicated_finding": "debris", "adjudicator_name": "adj1", "reason_for_correction": "r"},
            headers=AUTH_ADMIN,
        )
        assert adj.status_code == 200
        assert adj.json()["final_finding"] == "debris"

        db = SessionLocal()
        try:
            events = db.query(AuditLog).filter(AuditLog.action_type == "shadow_ground_truth_adjudicated").all()
            assert len(events) >= 1
        finally:
            db.close()

        listing = client.get("/api/shadow-validation/ground-truth", headers=AUTH_ADMIN)
        assert listing.status_code == 200
        assert listing.json()["count"] >= 1

    def test_dashboard_and_drift_and_metrics_endpoints(self):
        db = SessionLocal()
        try:
            _make_shadow(db, model_id="api-dash", predicted_label="debris", final_label="debris")
        finally:
            db.close()

        dash = client.get("/api/shadow-validation/dashboard", params={"model_id": "api-dash"}, headers=AUTH_ADMIN)
        assert dash.status_code == 200
        assert dash.json()["total_reconciled"] >= 1

        drift = client.get("/api/shadow-validation/drift", params={"model_id": "api-dash"}, headers=AUTH_ADMIN)
        assert drift.status_code == 200
        assert "drift_detected" in drift.json()

        metrics = client.get("/api/shadow-validation/validation-metrics", params={"model_id": "api-dash"}, headers=AUTH_ADMIN)
        assert metrics.status_code == 200
        assert "inter_reviewer_agreement" in metrics.json()

    def test_error_review_queue_and_resolve_endpoint(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            row = shadow_mode.record_shadow_prediction(
                db, tenant_id=TENANT, model_id="api-queue", model_version="1",
                model_type="candidate_finding_multiclass", predicted_label="debris",
                predicted_confidence="0.9", inspection_id=insp.id,
            )
            _finalize(db, insp)
            shadow_mode.reveal_if_finalized(db, row, insp=insp, final_label="corrosion")
        finally:
            db.close()

        queue = client.get("/api/shadow-validation/error-review-queue", headers=AUTH_ADMIN)
        assert queue.status_code == 200
        assert queue.json()["count"] >= 1
        item_id = queue.json()["queue"][0]["id"]

        resolved = client.post(
            f"/api/shadow-validation/error-review-queue/{item_id}/resolve",
            json={"reviewer_comments": "Reviewed.", "failure_classification": "model_limitation"},
            headers=AUTH_ADMIN,
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"

        analysis = client.get("/api/shadow-validation/failure-analysis", headers=AUTH_ADMIN)
        assert analysis.status_code == 200

    def test_clinical_review_board_api(self):
        r = client.post(
            "/api/shadow-validation/clinical-review-board",
            json={
                "model_id": "api-board", "model_version": "1",
                "reviewers": [{"name": "a", "role": "clinical_advisor"}],
                "readiness_assessment": "Ready.", "approved": True,
            },
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 201, r.text
        latest = client.get(
            "/api/shadow-validation/clinical-review-board/latest",
            params={"model_id": "api-board", "model_version": "1"}, headers=AUTH_ADMIN,
        )
        assert latest.status_code == 200
        assert latest.json()["approved"] is True

    def test_reports_endpoint_requires_period_for_weekly(self):
        r = client.get("/api/shadow-validation/reports/weekly", headers=AUTH_ADMIN)
        assert r.status_code == 422

        r2 = client.get("/api/shadow-validation/reports/performance-summary", headers=AUTH_ADMIN)
        assert r2.status_code == 200
        assert r2.json()["report_type"] == "performance_summary"

    def test_unknown_report_type_returns_404(self):
        r = client.get("/api/shadow-validation/reports/nonexistent-report", headers=AUTH_ADMIN)
        assert r.status_code == 404
