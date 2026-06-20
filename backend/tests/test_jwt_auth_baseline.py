import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")

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


def test_valid_hs256_jwt_creates_principal(monkeypatch):
    import time
    import jwt

    monkeypatch.setenv("AUTH_MODE", "production")
    monkeypatch.setenv("ENABLE_DEV_AUTH", "false")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.delenv("JWT_ISSUER", raising=False)
    monkeypatch.delenv("JWT_AUDIENCE", raising=False)

    app = FastAPI()

    @app.get("/protected-jwt")
    def protected_route(principal=Depends(require_authenticated_user)):
        return {
            "user_id": principal.user_id,
            "tenant_id": principal.tenant_id,
            "roles": principal.roles,
            "auth_mode": principal.auth_mode,
        }

    token = jwt.encode(
        {
            "sub": "user_123",
            "tenant_id": "tenant_abc",
            "roles": ["customer_admin"],
            "email": "user@example.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        "test-secret",
        algorithm="HS256",
    )

    client = TestClient(app)
    response = client.get(
        "/protected-jwt",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == "user_123"
    assert response.json()["tenant_id"] == "tenant_abc"
    assert response.json()["roles"] == ["customer_admin"]
    assert response.json()["auth_mode"] == "jwt"


def test_invalid_hs256_jwt_returns_401(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "production")
    monkeypatch.setenv("ENABLE_DEV_AUTH", "false")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    app = FastAPI()

    @app.get("/protected-jwt")
    def protected_route(principal=Depends(require_authenticated_user)):
        return {"user_id": principal.user_id}

    client = TestClient(app)
    response = client.get(
        "/protected-jwt",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "AUTHENTICATION_REQUIRED"
