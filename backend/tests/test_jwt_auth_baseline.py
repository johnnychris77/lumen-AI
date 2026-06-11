from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.core.jwt_auth import require_authenticated_user, require_any_role
from app.core.principal import Principal


def test_principal_role_helpers():
    principal = Principal(
        user_id="user_1",
        tenant_id="tenant_1",
        roles=["customer_admin", "quality_manager"],
    )

    assert principal.has_role("customer_admin")
    assert principal.has_any_role(["auditor", "quality_manager"])
    assert not principal.has_role("vendor_user")


def test_missing_bearer_token_returns_401():
    app = FastAPI()

    @app.get("/protected")
    def protected_route(principal=Depends(require_authenticated_user)):
        return {"user_id": principal.user_id}

    client = TestClient(app)
    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_role_dependency_exists_and_blocks_missing_auth():
    app = FastAPI()

    @app.get("/admin")
    def admin_route(principal=Depends(require_any_role(["system_admin"]))):
        return {"user_id": principal.user_id}

    client = TestClient(app)
    response = client.get("/admin")

    assert response.status_code == 401
