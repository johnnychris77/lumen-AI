"""Founder/admin user-management: bootstrap + role assignment."""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.user_role_assignment import UserRoleAssignment

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}       # admin (dev)
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}   # viewer (dev)


def _clear(username: str) -> None:
    db = SessionLocal()
    try:
        db.query(UserRoleAssignment).filter(UserRoleAssignment.username == username).delete()
        db.commit()
    finally:
        db.close()


class TestBootstrap:
    def test_bootstrap_inert_without_secret(self, monkeypatch):
        monkeypatch.delenv("ADMIN_BOOTSTRAP_TOKEN", raising=False)
        r = client.post("/api/admin/bootstrap", json={"username": "founder@lumen.ai"})
        assert r.status_code == 404

    def test_bootstrap_rejects_bad_token(self, monkeypatch):
        monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "s3cret")
        r = client.post("/api/admin/bootstrap", json={"username": "founder@lumen.ai"},
                        headers={"X-Bootstrap-Token": "wrong"})
        assert r.status_code == 403

    def test_bootstrap_grants_admin(self, monkeypatch):
        _clear("founder@lumen.ai")
        monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "s3cret")
        r = client.post("/api/admin/bootstrap", json={"username": "founder@lumen.ai"},
                        headers={"X-Bootstrap-Token": "s3cret"})
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "admin"
        # Persisted
        db = SessionLocal()
        try:
            row = db.query(UserRoleAssignment).filter_by(username="founder@lumen.ai").first()
            assert row is not None and row.role == "admin"
        finally:
            db.close()


class TestRoleAssignment:
    def test_admin_can_assign_roles(self):
        _clear("tech@lumen.ai")
        r = client.post("/api/admin/users/role",
                        json={"username": "tech@lumen.ai", "role": "spd_manager"},
                        headers=AUTH_ADMIN)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "spd_manager"

    def test_assign_supervisor_role(self):
        _clear("sup@lumen.ai")
        r = client.post("/api/admin/users/role",
                        json={"username": "sup@lumen.ai", "role": "supervisor"},
                        headers=AUTH_ADMIN)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "supervisor"

    def test_viewer_cannot_assign_roles(self):
        r = client.post("/api/admin/users/role",
                        json={"username": "x@lumen.ai", "role": "admin"},
                        headers=AUTH_VIEWER)
        assert r.status_code == 403

    def test_invalid_role_rejected(self):
        r = client.post("/api/admin/users/role",
                        json={"username": "x@lumen.ai", "role": "superuser"},
                        headers=AUTH_ADMIN)
        assert r.status_code == 422

    def test_admin_can_list_users(self):
        _clear("listed@lumen.ai")
        client.post("/api/admin/users/role",
                    json={"username": "listed@lumen.ai", "role": "viewer"}, headers=AUTH_ADMIN)
        r = client.get("/api/admin/users", headers=AUTH_ADMIN)
        assert r.status_code == 200, r.text
        usernames = [u["username"] for u in r.json()["users"]]
        assert "listed@lumen.ai" in usernames
        assert "supervisor" in r.json()["assignable_roles"]
