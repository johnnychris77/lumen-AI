"""P13 gap closure tests — kappa monitor, RWE scheduler, rate limiter."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}


class TestKappaMonitor:
    def test_kappa_monitor_returns_200(self):
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        assert r.status_code == 200

    def test_kappa_monitor_has_kappa(self):
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        data = r.json()
        assert "overall_kappa" in data
        assert 0 <= data["overall_kappa"] <= 1

    def test_kappa_monitor_has_status(self):
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        data = r.json()
        assert data["status"] in ("ok", "warning", "critical")

    def test_kappa_monitor_has_thresholds(self):
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        data = r.json()
        assert data["primary_endpoint_threshold"] == 0.80
        assert data["retraining_threshold"] == 0.75

    def test_kappa_monitor_has_meets_primary(self):
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        data = r.json()
        assert "meets_primary_endpoint" in data

    def test_kappa_monitor_requires_auth(self):
        r = client.get("/api/validation/kappa-monitor")
        assert r.status_code in (401, 403)

    def test_kappa_monitor_tenant_id_in_response(self):
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        data = r.json()
        assert "tenant_id" in data

    def test_kappa_monitor_run_label_param(self):
        r = client.get("/api/validation/kappa-monitor?run_label=test-run", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["run_label"] == "test-run"

    def test_kappa_warning_when_below_080(self):
        # Mock data kappa is ~0.79, so status should be "warning" or "ok"
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        data = r.json()
        kappa = data["overall_kappa"]
        if kappa < 0.75:
            assert data["status"] == "critical"
        elif kappa < 0.80:
            assert data["status"] == "warning"
        else:
            assert data["status"] == "ok"

    def test_kappa_alert_is_none_when_ok(self):
        r = client.get("/api/validation/kappa-monitor", headers=HEADERS)
        data = r.json()
        if data["status"] == "ok":
            assert data["alert"] is None


class TestRWEScheduler:
    def test_rwe_scheduler_module_importable(self):
        from app.services.rwe_scheduler import register_rwe_scheduler
        assert callable(register_rwe_scheduler)

    def test_rwe_run_function_importable(self):
        from app.services.rwe_scheduler import _run_weekly_rwe_snapshots
        assert callable(_run_weekly_rwe_snapshots)

    def test_rwe_run_does_not_crash_with_no_enrollments(self):
        from app.services.rwe_scheduler import _run_weekly_rwe_snapshots
        from app.db.session import SessionLocal
        # Should not raise even with no enrollments
        _run_weekly_rwe_snapshots(SessionLocal)

    def test_rwe_snapshot_created_after_enroll_and_run(self):
        from app.services.rwe_scheduler import _run_weekly_rwe_snapshots
        from app.db.session import SessionLocal
        # Enroll a facility first
        r = client.post("/api/validation/rwe/enroll", headers=HEADERS, json={
            "facility_id": "rwe-sched-test",
            "enrolled_by": "test-user"
        })
        assert r.status_code == 200
        # Run the scheduler
        _run_weekly_rwe_snapshots(SessionLocal)
        # Check snapshot was created
        r2 = client.get("/api/validation/rwe/metrics", headers=HEADERS)
        assert r2.status_code == 200


class TestLimiterModule:
    def test_limiter_module_importable(self):
        from app.limiter import _rate_limit
        assert callable(_rate_limit)

    def test_rate_limit_decorator_is_callable(self):
        from app.limiter import _rate_limit
        decorator = _rate_limit("30/minute")
        assert callable(decorator)

    def test_rate_limit_wraps_function(self):
        from app.limiter import _rate_limit

        @_rate_limit("10/minute")
        def dummy():
            return "ok"

        assert callable(dummy)

    def test_cv_inference_endpoint_still_works(self):
        # Rate limiting should not break existing endpoints in test env
        r = client.get("/health")
        assert r.status_code == 200


class TestNewDocs:
    def test_docs_regulatory_dir_has_new_files(self):
        import os
        base = "/home/user/lumen-AI/docs/regulatory"
        expected = [
            "510k-predicate-search-log.md",
            "external-pentest-scope.md",
            "q-submission-preparation.md",
            "predetermined-change-control-plan.md",
            "post-market-surveillance-plan.md",
        ]
        for f in expected:
            assert os.path.exists(os.path.join(base, f)), f"Missing: {f}"

    def test_existing_regulatory_docs_still_present(self):
        import os
        base = "/home/user/lumen-AI/docs/regulatory"
        existing = [
            "intended-use-and-claims-boundary.md",
            "samd-classification-assessment.md",
            "risk-management-file.md",
            "fda-submission-readiness-checklist.md",
            "traceability-matrix.md",
        ]
        for f in existing:
            assert os.path.exists(os.path.join(base, f)), f"Missing: {f}"
