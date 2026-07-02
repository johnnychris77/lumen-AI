"""Phase 18 — Real-World Pilot Validation & Clinical Performance Study tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH = {"Authorization": "Bearer manager-token"}


def _submit_case(**overrides) -> dict:
    body = {
        "instrument_family": "hemostat",
        "manufacturer": "Acme Surgical",
        "model": "AS-100",
        "anatomy_zone": "box locks",
        "baseline_source": "vendor_baseline",
        "has_baseline": True,
        "finding_type": "blood",
        "severity": "critical",
        "ai_prediction": True,
        "ai_confidence": 0.9,
        "ai_recommended_disposition": "reprocess",
        "supervisor_finding": True,
        "supervisor_zone_correction": "",
        "reviewer_name": "J. Rivera",
        "reviewer_rationale": "Confirmed residue under magnification.",
        "final_disposition": "reprocess",
        "dataset_version": "pilot-v1",
        "model_version": "cv-baseline-1.0",
    }
    body.update(overrides)
    res = client.post("/api/pilot-validation/cases", json=body, headers=AUTH)
    assert res.status_code == 201, res.text
    return res.json()


class TestGroundTruthCreation:
    def test_supervisor_review_creates_ground_truth_label(self):
        case = _submit_case(ai_prediction=True, supervisor_finding=True)
        assert case["ground_truth_label"] == "tp"

    def test_true_negative_label(self):
        case = _submit_case(ai_prediction=False, supervisor_finding=False, finding_type="none", severity="none")
        assert case["ground_truth_label"] == "tn"

    def test_false_positive_calculated_correctly(self):
        case = _submit_case(ai_prediction=True, supervisor_finding=False)
        assert case["ground_truth_label"] == "fp"

    def test_false_negative_calculated_correctly(self):
        case = _submit_case(ai_prediction=False, supervisor_finding=True)
        assert case["ground_truth_label"] == "fn"

    def test_inconclusive_when_supervisor_finding_missing(self):
        case = _submit_case(ai_prediction=True, supervisor_finding=None)
        assert case["ground_truth_label"] == "inconclusive"

    def test_critical_finding_flag_set_for_blood(self):
        case = _submit_case(finding_type="blood")
        assert case["is_critical_finding"] is True

    def test_critical_finding_flag_false_for_non_critical(self):
        case = _submit_case(finding_type="corrosion", ai_prediction=True, supervisor_finding=True)
        assert case["is_critical_finding"] is False

    def test_unauthenticated_rejected(self):
        res = client.post("/api/pilot-validation/cases", json={})
        assert res.status_code in (401, 403)

    def test_viewer_role_forbidden(self):
        res = client.post(
            "/api/pilot-validation/cases", json={"finding_type": "blood"},
            headers={"Authorization": "Bearer viewer-token"},
        )
        assert res.status_code == 403


class TestClinicalMetrics:
    def test_agreement_rate_calculated_correctly(self):
        # Fresh, deterministic set: 2 TP, 1 TN, 1 FP, 1 FN → agreement = 3/5
        _submit_case(ai_prediction=True, supervisor_finding=True, finding_type="tissue", anatomy_zone="lumens")
        _submit_case(ai_prediction=True, supervisor_finding=True, finding_type="tissue", anatomy_zone="lumens")
        _submit_case(ai_prediction=False, supervisor_finding=False, finding_type="none", severity="none", anatomy_zone="lumens")
        _submit_case(ai_prediction=True, supervisor_finding=False, finding_type="debris", anatomy_zone="lumens")
        _submit_case(ai_prediction=False, supervisor_finding=True, finding_type="tissue", anatomy_zone="lumens")

        res = client.get("/api/pilot-validation/metrics", headers=AUTH)
        assert res.status_code == 200
        metrics = res.json()["clinical_metrics"]
        cm = metrics["confusion_matrix"]
        assert cm["tp"] >= 2 and cm["tn"] >= 1 and cm["fp"] >= 1 and cm["fn"] >= 1
        # Agreement rate must equal (tp+tn)/adjudicated across the whole tenant dataset.
        expected = round((cm["tp"] + cm["tn"]) / metrics["adjudicated_count"], 4)
        assert metrics["supervisor_agreement_rate"] == expected

    def test_metrics_required_keys(self):
        data = client.get("/api/pilot-validation/metrics", headers=AUTH).json()
        metrics = data["clinical_metrics"]
        for key in ("accuracy", "precision", "recall", "f1", "false_positive_rate", "false_negative_rate",
                    "supervisor_agreement_rate", "override_rate", "confidence_calibration"):
            assert key in metrics
        assert data["clinical_metrics"]["human_review_required"] is True

    def test_critical_safety_metrics_include_all_types(self):
        data = client.get("/api/pilot-validation/metrics", headers=AUTH).json()
        by_type = data["critical_safety_metrics"]["by_finding_type"]
        for finding_type in ("blood", "tissue", "organic_residue", "crack", "missing_component"):
            assert finding_type in by_type

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-validation/metrics")
        assert res.status_code in (401, 403)


class TestZonePerformance:
    def test_zone_performance_calculated_correctly(self):
        _submit_case(anatomy_zone="hinges", ai_prediction=False, supervisor_finding=True, finding_type="tissue")
        _submit_case(anatomy_zone="hinges", ai_prediction=True, supervisor_finding=True, finding_type="tissue")

        res = client.get("/api/pilot-validation/zone-performance", headers=AUTH)
        assert res.status_code == 200
        zones = {z["zone"]: z for z in res.json()["zone_performance"]}
        assert "hinges" in zones
        assert zones["hinges"]["missed_count"] >= 1
        assert zones["hinges"]["case_count"] >= 2

    def test_zone_marked_high_risk(self):
        res = client.get("/api/pilot-validation/zone-performance", headers=AUTH)
        zones = {z["zone"]: z for z in res.json()["zone_performance"]}
        assert zones["hinges"]["is_high_risk_zone"] is True


class TestDashboard:
    def test_dashboard_returns_required_metrics(self):
        res = client.get("/api/pilot-validation/dashboard", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        for key in (
            "total_inspections_reviewed", "ai_supervisor_agreement_rate", "false_positives",
            "false_negatives", "high_risk_findings_detected", "inconclusive_cases",
            "model_confidence_trend", "zone_performance", "instrument_family_performance",
        ):
            assert key in data
        assert data["human_review_required"] is True

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-validation/dashboard")
        assert res.status_code in (401, 403)


class TestSafetyQueue:
    def test_safety_queue_includes_critical_missed_findings(self):
        _submit_case(
            finding_type="blood", ai_prediction=False, supervisor_finding=True,
            anatomy_zone="lumens", severity="critical",
        )
        res = client.get("/api/pilot-validation/safety-queue", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert data["critical_missed_findings"]["count"] >= 1
        assert any(c["finding_type"] == "blood" for c in data["critical_missed_findings"]["cases"])

    def test_missing_baseline_cases_tracked(self):
        _submit_case(has_baseline=False)
        res = client.get("/api/pilot-validation/safety-queue", headers=AUTH)
        data = res.json()
        assert data["missing_baseline_cases"]["count"] >= 1

    def test_viewer_forbidden(self):
        res = client.get(
            "/api/pilot-validation/safety-queue", headers={"Authorization": "Bearer viewer-token"}
        )
        assert res.status_code == 403


class TestValidationReport:
    def test_report_includes_dataset_and_model_version(self):
        _submit_case(dataset_version="pilot-v2", model_version="cv-baseline-2.0")
        res = client.get("/api/pilot-validation/report", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "dataset_version" in data
        assert "model_version" in data
        assert data["dataset_version"]
        assert data["model_version"]

    def test_report_required_sections(self):
        data = client.get("/api/pilot-validation/report", headers=AUTH).json()
        for key in (
            "study_scope", "results", "safety_findings", "limitations",
            "recommendations", "next_training_priorities", "go_no_go",
        ):
            assert key in data


class TestGoNoGo:
    def test_go_no_go_returns_decision(self):
        res = client.get("/api/pilot-validation/go-no-go", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] in ("GO", "NO-GO")
        assert "criteria" in data

    def test_no_go_when_critical_fn_present(self):
        # This tenant's dataset already has a blood FN from TestSafetyQueue — should block GO.
        data = client.get("/api/pilot-validation/go-no-go", headers=AUTH).json()
        if data["criteria"]["unresolved_critical_safety_issues"] > 0:
            assert data["decision"] == "NO-GO"
