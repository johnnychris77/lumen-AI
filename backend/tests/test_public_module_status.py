from fastapi.testclient import TestClient

try:
    from app.main import app
except Exception:
    from main import app


client = TestClient(app)


def test_public_module_status_all_returns_safe_metadata():
    response = client.get("/api/public/module-status/all")

    assert response.status_code == 200

    data = response.json()
    assert "modules" in data
    assert len(data["modules"]) == 4

    serialized = str(data).lower()

    forbidden_terms = [
        "patient",
        "phi",
        "password",
        "secret",
        "token",
        "stack",
        "traceback",
        "sql",
        "database error",
    ]

    for term in forbidden_terms:
        assert term not in serialized

    for module in data["modules"]:
        assert module["status"] in {"available", "degraded", "unavailable"}
        assert module["public_status"] in {"public", "protected", "not_configured"}
        assert isinstance(module["requires_authentication"], bool)
        assert "description" in module
        assert "checked_at" in module


def test_public_module_status_individual_routes_return_200():
    routes = [
        "/api/public/module-status/vendor",
        "/api/public/module-status/capa",
        "/api/public/module-status/audit",
        "/api/public/module-status/evidence",
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "available"
        assert data["public_status"] == "protected"
        assert data["requires_authentication"] is True
        assert "module" in data
        assert "description" in data
        assert "checked_at" in data
