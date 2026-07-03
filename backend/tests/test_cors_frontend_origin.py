"""CORS must allow the Render-hosted frontend so the SPA's POSTs aren't blocked.

Regression: the frontend origin (lumen-ai-1.onrender.com) was not in the allowed
list, so authenticated POSTs from the inspection page failed with "Failed to
fetch" (blocked CORS preflight).
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FRONTEND = "https://lumen-ai-1.onrender.com"


def test_preflight_allows_frontend_origin_for_inspection_post():
    r = client.options(
        "/api/inspections",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,x-lumenai-role,x-lumenai-actor",
        },
    )
    assert r.status_code in (200, 204), r.text
    assert r.headers.get("access-control-allow-origin") == FRONTEND


def test_preflight_allows_image_upload():
    r = client.options(
        "/api/inspections/upload-images",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert r.status_code in (200, 204), r.text
    assert r.headers.get("access-control-allow-origin") == FRONTEND


def test_arbitrary_onrender_subdomain_rejected():
    """Regression guard for the CORS hardening fix: any *.onrender.com origin
    used to be allowed, meaning an attacker-hosted Render site could make
    credentialed cross-origin requests. The allow-list is now pinned to this
    project's exact frontend origin (see app/main.py's `_CORS_ORIGIN_REGEX`)."""
    origin = "https://some-other-frontend.onrender.com"
    r = client.options(
        "/api/inspections",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.headers.get("access-control-allow-origin") != origin
