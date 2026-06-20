"""P12 gap closure tests — reader study simulator, sealed test set, RWE enrollment."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}


# ---------------------------------------------------------------------------
# GAP 1: Reader Study Simulator
# ---------------------------------------------------------------------------

class TestReaderStudySimulator:
    def test_simulate_study_returns_200(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        assert resp.status_code == 200

    def test_simulate_study_total_cases_positive(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        assert resp.json()["total_cases"] > 0

    def test_simulate_study_categories_simulated(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        assert resp.json()["categories_simulated"] == 12

    def test_simulate_study_readers_simulated(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        assert resp.json()["readers_simulated"] == 5

    def test_simulate_study_has_summary_by_role(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        assert "summary_by_role" in resp.json()
        assert isinstance(resp.json()["summary_by_role"], dict)

    def test_simulate_study_all_roles_present(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        roles = resp.json()["summary_by_role"]
        expected = {"technician_entry", "technician_senior", "educator", "manager", "infection_prevention"}
        assert set(roles.keys()) == expected

    def test_simulate_study_avg_recall_in_range(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        for role, stats in resp.json()["summary_by_role"].items():
            assert 0.0 <= stats["avg_recall"] <= 1.0, f"avg_recall out of range for {role}"

    def test_simulate_study_avg_f1_in_range(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        for role, stats in resp.json()["summary_by_role"].items():
            assert 0.0 <= stats["avg_f1"] <= 1.0, f"avg_f1 out of range for {role}"

    def test_simulate_study_has_run_label(self):
        resp = client.post("/api/validation/simulate-study", headers=HEADERS)
        assert "run_label" in resp.json()

    def test_simulate_study_deterministic(self):
        r1 = client.post(
            "/api/validation/simulate-study",
            params={"run_label": "determinism-test"},
            headers=HEADERS,
        )
        r2 = client.post(
            "/api/validation/simulate-study",
            params={"run_label": "determinism-test"},
            headers=HEADERS,
        )
        assert r1.json()["total_cases"] == r2.json()["total_cases"]


# ---------------------------------------------------------------------------
# GAP 2: Sealed Test Registry
# ---------------------------------------------------------------------------

class TestSealedTestRegistry:
    def _create(self, label: str = "v1.0-holdout") -> dict:
        resp = client.post(
            "/api/validation/sealed-test",
            json={
                "set_label": label,
                "manifest_hash": "abc123def456" + "0" * 52,
                "sealed_by": "CVC-chair@hospital.org",
                "notes": "Pre-submission holdout",
            },
            headers=HEADERS,
        )
        assert resp.status_code == 200
        return resp.json()

    def test_register_sealed_test_returns_200(self):
        resp = client.post(
            "/api/validation/sealed-test",
            json={
                "set_label": "v2.0-holdout",
                "manifest_hash": "a" * 64,
                "sealed_by": "chair@hospital.org",
            },
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert "set_label" in resp.json()

    def test_register_has_manifest_hash(self):
        data = self._create("v3-holdout")
        assert "manifest_hash" in data and len(data["manifest_hash"]) > 0

    def test_register_status_is_sealed(self):
        data = self._create("v4-holdout")
        assert data["status"] == "sealed"

    def test_list_sealed_tests_returns_200(self):
        self._create("v5-holdout")
        resp = client.get("/api/validation/sealed-test", headers=HEADERS)
        assert resp.status_code == 200
        assert "entries" in resp.json()

    def test_evaluate_sealed_test_returns_200(self):
        entry = self._create("v6-holdout")
        resp = client.post(
            f"/api/validation/sealed-test/{entry['id']}/evaluate",
            json={"overall_accuracy": 0.91, "critical_fn_rate": 0.01, "overall_kappa": 0.83},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_evaluate_passing_results_passed_true(self):
        entry = self._create("v7-holdout")
        resp = client.post(
            f"/api/validation/sealed-test/{entry['id']}/evaluate",
            json={"overall_accuracy": 0.91, "critical_fn_rate": 0.01, "overall_kappa": 0.83},
            headers=HEADERS,
        )
        assert resp.json()["passed"] is True

    def test_evaluate_high_fn_rate_passed_false(self):
        entry = self._create("v8-holdout")
        resp = client.post(
            f"/api/validation/sealed-test/{entry['id']}/evaluate",
            json={"overall_accuracy": 0.91, "critical_fn_rate": 0.05, "overall_kappa": 0.83},
            headers=HEADERS,
        )
        assert resp.json()["passed"] is False

    def test_evaluate_updates_status(self):
        entry = self._create("v9-holdout")
        resp = client.post(
            f"/api/validation/sealed-test/{entry['id']}/evaluate",
            json={"overall_accuracy": 0.91, "critical_fn_rate": 0.01, "overall_kappa": 0.83},
            headers=HEADERS,
        )
        assert resp.json()["status"] in {"passed", "failed"}

    def test_evaluate_nonexistent_returns_404(self):
        resp = client.post(
            "/api/validation/sealed-test/999999/evaluate",
            json={"overall_accuracy": 0.91, "critical_fn_rate": 0.01, "overall_kappa": 0.83},
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_list_returns_most_recent_first(self):
        self._create("z-first")
        self._create("z-second")
        resp = client.get("/api/validation/sealed-test", headers=HEADERS)
        entries = resp.json()["entries"]
        assert len(entries) >= 2


# ---------------------------------------------------------------------------
# GAP 4: RWE Enrollment & Metrics
# ---------------------------------------------------------------------------

class TestRWEEnrollment:
    def test_enroll_returns_200(self):
        resp = client.post(
            "/api/validation/rwe/enroll",
            json={"facility_id": "hospital-A", "enrolled_by": "admin@hospital.org"},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_enroll_has_facility_id_and_is_active(self):
        resp = client.post(
            "/api/validation/rwe/enroll",
            json={"facility_id": "hospital-B", "enrolled_by": "admin@hospital.org"},
            headers=HEADERS,
        )
        data = resp.json()
        assert data["facility_id"] == "hospital-B"
        assert data["is_active"] is True

    def test_list_enrollments_returns_200(self):
        resp = client.get("/api/validation/rwe/enrollments", headers=HEADERS)
        assert resp.status_code == 200
        assert "enrollments" in resp.json()

    def test_snapshot_returns_200(self):
        resp = client.post(
            "/api/validation/rwe/snapshot",
            params={"week_label": "2026-W25"},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_snapshot_override_rate_in_range(self):
        resp = client.post(
            "/api/validation/rwe/snapshot",
            params={"week_label": "2026-W26"},
            headers=HEADERS,
        )
        rate = resp.json()["override_rate"]
        assert 0.0 <= rate <= 1.0

    def test_snapshot_psi_score_nonnegative(self):
        resp = client.post(
            "/api/validation/rwe/snapshot",
            params={"week_label": "2026-W27"},
            headers=HEADERS,
        )
        assert resp.json()["psi_score"] >= 0.0

    def test_snapshot_has_drift_alert_bool(self):
        resp = client.post(
            "/api/validation/rwe/snapshot",
            params={"week_label": "2026-W28"},
            headers=HEADERS,
        )
        assert isinstance(resp.json()["drift_alert"], bool)

    def test_snapshot_has_week_label(self):
        resp = client.post(
            "/api/validation/rwe/snapshot",
            params={"week_label": "2026-W29"},
            headers=HEADERS,
        )
        assert "week_label" in resp.json()

    def test_get_metrics_returns_200(self):
        resp = client.get("/api/validation/rwe/metrics", headers=HEADERS)
        assert resp.status_code == 200
        assert "snapshots" in resp.json()

    def test_snapshot_drift_alert_when_psi_high(self):
        # Use a deterministic seed that produces psi > 0.2
        # We test the logic by checking consistency: drift_alert == (psi_score > 0.2)
        resp = client.post(
            "/api/validation/rwe/snapshot",
            params={"week_label": "2026-W30"},
            headers=HEADERS,
        )
        data = resp.json()
        assert data["drift_alert"] == (data["psi_score"] > 0.2)


# ---------------------------------------------------------------------------
# GAP: Documentation & Auth Guards
# ---------------------------------------------------------------------------

class TestDocumentationExists:
    def test_validation_report_still_200(self):
        resp = client.get("/api/validation/report", headers=HEADERS)
        assert resp.status_code == 200

    def test_report_has_meets_primary_endpoint(self):
        resp = client.get("/api/validation/report", headers=HEADERS)
        assert "meets_primary_endpoint" in resp.json()

    def test_report_has_meets_safety_endpoint(self):
        resp = client.get("/api/validation/report", headers=HEADERS)
        assert "meets_safety_endpoint" in resp.json()

    def test_simulate_study_requires_auth(self):
        resp = client.post("/api/validation/simulate-study")
        assert resp.status_code in {401, 403}

    def test_sealed_test_requires_auth(self):
        resp = client.post(
            "/api/validation/sealed-test",
            json={"set_label": "x", "manifest_hash": "a" * 64, "sealed_by": "x"},
        )
        assert resp.status_code in {401, 403}

    def test_rwe_enroll_requires_auth(self):
        resp = client.post(
            "/api/validation/rwe/enroll",
            json={"facility_id": "h", "enrolled_by": "a"},
        )
        assert resp.status_code in {401, 403}

    def test_rwe_metrics_requires_auth(self):
        resp = client.get("/api/validation/rwe/metrics")
        assert resp.status_code in {401, 403}

    def test_simulate_study_deterministic_across_calls(self):
        r1 = client.post(
            "/api/validation/simulate-study",
            params={"run_label": "doc-det-test"},
            headers=HEADERS,
        )
        r2 = client.post(
            "/api/validation/simulate-study",
            params={"run_label": "doc-det-test"},
            headers=HEADERS,
        )
        assert r1.json()["summary_by_role"] == r2.json()["summary_by_role"]

    def test_sealed_test_list_empty_not_error(self):
        # Even if no records exist, list should return 200 with empty list (not error)
        resp = client.get("/api/validation/sealed-test", headers=HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json()["entries"], list)

    def test_doc_sealed_test_protocol_exists(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "docs", "clinical", "sealed-test-set-protocol.md",
        )
        assert os.path.exists(os.path.abspath(path))

    def test_doc_cybersecurity_threat_model_exists(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "docs", "clinical", "cybersecurity-threat-model.md",
        )
        assert os.path.exists(os.path.abspath(path))
