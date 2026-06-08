import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _client():
    from app.main import app

    return TestClient(app)


def _headers(role: str, actor: str):
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": role,
        "X-LumenAI-Actor": actor,
    }


def test_hospital_admin_can_view_vendor_baseline_library():
    client = _client()

    response = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_headers("hospital_admin", "library-access-hospital-admin"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"


def test_enterprise_admin_can_view_vendor_baseline_library():
    client = _client()

    response = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_headers("enterprise_admin", "library-access-enterprise-admin"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"


def test_vendor_cannot_view_full_vendor_baseline_library():
    client = _client()

    response = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_headers("vendor", "library-access-vendor"),
    )

    assert response.status_code in {401, 403}


def test_missing_auth_cannot_view_vendor_baseline_library():
    client = _client()

    response = client.get("/api/enterprise/vendor-baseline-subscription/baselines")

    assert response.status_code in {401, 403}
