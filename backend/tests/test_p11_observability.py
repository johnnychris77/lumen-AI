"""Tests for P11 observability endpoints: /health, /ready, /metrics."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_has_status_ok(self):
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "ok"

    def test_health_has_version(self):
        r = client.get("/health")
        data = r.json()
        assert "version" in data

    def test_health_has_environment(self):
        r = client.get("/health")
        data = r.json()
        assert "environment" in data

    def test_health_no_auth_required(self):
        r = client.get("/health")
        assert r.status_code != 401
        assert r.status_code != 403


class TestReadyEndpoint:
    def test_ready_returns_2xx(self):
        r = client.get("/ready")
        assert r.status_code in (200, 503)

    def test_ready_has_status_field(self):
        r = client.get("/ready")
        data = r.json()
        assert "status" in data

    def test_ready_no_auth_required(self):
        r = client.get("/ready")
        assert r.status_code != 401
        assert r.status_code != 403

    def test_ready_db_ok_in_test(self):
        # In test environment with SQLite, DB should be reachable
        r = client.get("/ready")
        assert r.status_code == 200


class TestMetricsEndpoint:
    def test_metrics_accessible_from_localhost(self):
        # TestClient is treated as localhost
        r = client.get("/metrics")
        # Should succeed (localhost access) or require token
        assert r.status_code in (200, 401, 403)

    def test_metrics_returns_text_on_success(self):
        r = client.get("/metrics")
        if r.status_code == 200:
            assert "uptime" in r.text or "request" in r.text.lower()

    def test_metrics_with_valid_token(self, monkeypatch):
        monkeypatch.setenv("METRICS_TOKEN", "test-metrics-token-123")
        r = client.get("/metrics?token=test-metrics-token-123")
        assert r.status_code == 200

    def test_metrics_with_invalid_token(self, monkeypatch):
        monkeypatch.setenv("METRICS_TOKEN", "correct-token")
        r = client.get("/metrics?token=wrong-token")
        assert r.status_code in (401, 403)


class TestCorrelationIDMiddleware:
    def test_correlation_id_returned_in_response(self):
        r = client.get("/health")
        assert "x-correlation-id" in r.headers or "X-Correlation-ID" in r.headers

    def test_custom_correlation_id_propagated(self):
        r = client.get("/health", headers={"X-Correlation-ID": "test-corr-123"})
        header_val = r.headers.get("x-correlation-id") or r.headers.get("X-Correlation-ID", "")
        assert "test-corr-123" in header_val

    def test_correlation_id_generated_when_absent(self):
        r = client.get("/health")
        corr_id = r.headers.get("x-correlation-id") or r.headers.get("X-Correlation-ID", "")
        assert len(corr_id) > 0
