from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


PUBLIC_ENDPOINTS = [
    "/api/health",
    "/api/public/module-status/vendor",
    "/api/public/module-status/capa",
    "/api/public/module-status/audit",
    "/api/public/module-status/evidence",
    "/api/public/module-status/all",
]


PROTECTED_ENDPOINT_CANDIDATES = [
    "/api/capa",
    "/api/enterprise/audit/events",
    "/api/enterprise/audit/evidence-bundle",
    "/api/enterprise/audit/evidence-bundle/verification-summary",
    "/api/analytics/vendors",
    "/api/history",
    "/api/history/summary",
]


FORBIDDEN_RESPONSE_TERMS = [
    "traceback",
    "stack trace",
    "database error",
    "sqlalchemy.exc",
    "select * from",
    "insert into",
    "update ",
    "delete from",
    "private key",
    "password",
    "secret",
]


def test_public_endpoints_remain_public_safe():
    for route in PUBLIC_ENDPOINTS:
        response = client.get(route)
        assert response.status_code in {200, 404}

        if response.status_code == 200:
            body = response.text.lower()
            for term in FORBIDDEN_RESPONSE_TERMS:
                assert term not in body


def test_protected_endpoint_candidates_do_not_leak_internal_details_anonymously():
    for route in PROTECTED_ENDPOINT_CANDIDATES:
        response = client.get(route)

        assert response.status_code in {200, 401, 403, 404, 405, 422}

        body = response.text.lower()
        for term in FORBIDDEN_RESPONSE_TERMS:
            assert term not in body


def test_public_module_status_all_is_safe_without_authentication():
    response = client.get("/api/public/module-status/all")

    assert response.status_code == 200

    body = response.text.lower()

    assert "vendor governance" in body
    assert "capa workflow" in body
    assert "audit command center" in body
    assert "compliance evidence" in body

    forbidden_terms = [
        "tenant_id",
        "patient",
        "mrn",
        "phi",
        "dev-token",
        "enterprise_admin",
        "x-lumenai-role",
        "x-lumenai-actor",
    ]

    for term in forbidden_terms:
        assert term not in body
