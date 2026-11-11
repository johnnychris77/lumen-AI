"""/api/health must report schema readiness TRUTHFULLY.

A failed or partial startup schema bootstrap (e.g. a comparison-critical table
that could not be created) must never leave the app advertising readiness: the
health endpoint reports `status: "degraded"` (never "ok") in that case, so a
health check can't certify a deployment that would silently serve
"no visual (pixel) comparison was performed".
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Forbidden substrings that must never leak into a public health body.
_LEAKY = ["Traceback", "sqlalchemy.exc", "SELECT ", "INSERT INTO", "password", "private key"]


def test_health_ok_reports_commit_and_schema_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["schema_ok"] is True
    assert "git_commit" in body  # deployment verification handle


def test_health_degraded_when_schema_bootstrap_failed():
    # Simulate a bootstrap failure the way the lifespan records it.
    prev_ok = getattr(app.state, "schema_ok", None)
    prev_issues = getattr(app.state, "schema_issues", None)
    app.state.schema_ok = False
    app.state.schema_issues = ["missing required table: inspection_processing_images"]
    try:
        r = client.get("/api/health")
        # Still HTTP 200 (deploy stays observable) but NOT reporting "ok".
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "degraded"
        assert body["status"] != "ok"
        assert body["schema_ok"] is False
        assert "inspection_processing_images" in " ".join(body["schema_issues"])
        assert "git_commit" in body
        # No stack traces / SQL / secrets leak through the public body.
        blob = r.text
        for term in _LEAKY:
            assert term not in blob
    finally:
        # Restore shared app.state so other tests see a healthy app.
        if prev_ok is None:
            delattr(app.state, "schema_ok")
        else:
            app.state.schema_ok = prev_ok
        if prev_issues is None:
            if hasattr(app.state, "schema_issues"):
                delattr(app.state, "schema_issues")
        else:
            app.state.schema_issues = prev_issues
