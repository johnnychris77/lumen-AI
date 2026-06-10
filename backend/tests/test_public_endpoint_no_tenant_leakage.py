from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_public_module_status_does_not_return_tenant_fields():
    response = client.get("/api/public/module-status/all")

    assert response.status_code == 200

    data = response.json()
    serialized = str(data).lower()

    forbidden_terms = [
        "tenant_id",
        "tenant_name",
        "facility_id",
        "facility_name",
        "customer_id",
        "organization_id",
        "patient",
        "mrn",
        "phi",
        "user_id",
        "email",
        "token",
        "secret",
    ]

    for term in forbidden_terms:
        assert term not in serialized
