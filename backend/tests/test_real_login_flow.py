"""Real login: validates credentials, returns a signed JWT + the user's role.

Replaces a stub that returned a hardcoded 'dev-token' with no role (which left
every user stuck as viewer and unable to authenticate). The founder bootstrap
can set a login password so an admin account exists without a registration flow.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.admin_credential import AdminCredential
from app.models.user_role_assignment import UserRoleAssignment

client = TestClient(app)

FOUNDER = "founder@lumen.ai"
PW = "S3cretPass123"


def _clear(username: str) -> None:
    db = SessionLocal()
    try:
        db.query(AdminCredential).filter(AdminCredential.username == username).delete()
        db.query(UserRoleAssignment).filter(UserRoleAssignment.username == username).delete()
        db.commit()
    finally:
        db.close()


class TestLoginValidation:
    def test_login_requires_credentials(self):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 400

    def test_login_rejects_unknown_user(self):
        _clear("nobody@lumen.ai")
        r = client.post("/api/auth/login", json={"username": "nobody@lumen.ai", "password": "whatever123"})
        assert r.status_code == 401

    def test_login_no_longer_returns_dev_token(self):
        # The old stub returned a hardcoded "dev-token" for anyone — must not happen.
        r = client.post("/api/auth/login", json={"username": "x@y.z", "password": "bad-passw0rd"})
        assert r.status_code == 401
        assert "dev-token" not in r.text


class TestBootstrapPasswordLogin:
    def setup_method(self, _):
        _clear(FOUNDER)

    def _bootstrap(self, monkeypatch, password=PW):
        monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "boot-secret")
        return client.post(
            "/api/admin/bootstrap",
            json={"username": FOUNDER, "password": password},
            headers={"X-Bootstrap-Token": "boot-secret"},
        )

    def test_bootstrap_sets_login_password(self, monkeypatch):
        r = self._bootstrap(monkeypatch)
        assert r.status_code == 200, r.text
        assert r.json()["login_password_set"] is True
        assert r.json()["role"] == "admin"

    def test_founder_can_login_as_admin(self, monkeypatch):
        self._bootstrap(monkeypatch)
        r = client.post("/api/auth/login", json={"username": FOUNDER, "password": PW})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["role"] == "admin"
        assert body["access_token"] and body["access_token"] != "dev-token"
        assert body["token_type"] == "bearer"

    def test_wrong_password_rejected(self, monkeypatch):
        self._bootstrap(monkeypatch)
        r = client.post("/api/auth/login", json={"username": FOUNDER, "password": "wrong-passw0rd"})
        assert r.status_code == 401

    def test_login_token_authorizes_admin_endpoint(self, monkeypatch):
        # The issued token must actually authenticate against role-gated routes.
        self._bootstrap(monkeypatch)
        login = client.post("/api/auth/login", json={"username": FOUNDER, "password": PW})
        token = login.json()["access_token"]
        r = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
