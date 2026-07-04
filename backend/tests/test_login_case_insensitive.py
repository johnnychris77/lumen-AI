"""Regression test: bootstrap + login must match usernames/emails
case-insensitively. Previously every lookup (AdminCredential, the legacy
users table, user_role_assignments) did an exact-case string match, so an
account bootstrapped as "Jane@Hospital.org" could not log in when typed as
"jane@hospital.org" (or vice versa) — silently failing with a generic
"Invalid credentials" that gave no hint the issue was casing.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.admin_credential import AdminCredential
from app.models.user_role_assignment import UserRoleAssignment

client = TestClient(app)


def _clear(username: str) -> None:
    db = SessionLocal()
    try:
        db.query(UserRoleAssignment).filter(UserRoleAssignment.username == username).delete()
        db.query(AdminCredential).filter(AdminCredential.username == username).delete()
        db.commit()
    finally:
        db.close()


class TestCaseInsensitiveLogin:
    def test_login_with_different_case_than_bootstrap_succeeds(self, monkeypatch):
        _clear("Founder@Lumen.AI")
        monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "s3cret")
        boot = client.post(
            "/api/admin/bootstrap",
            json={"username": "Founder@Lumen.AI", "password": "NewPassword123"},
            headers={"X-Bootstrap-Token": "s3cret"},
        )
        assert boot.status_code == 200, boot.text
        assert boot.json()["login_password_set"] is True

        # Log in with a different case than what was used at bootstrap.
        login = client.post(
            "/api/auth/login",
            json={"email": "founder@lumen.ai", "password": "NewPassword123"},
        )
        assert login.status_code == 200, login.text
        body = login.json()
        assert body["access_token"]
        assert body["role"] == "admin"

    def test_bootstrap_twice_with_different_case_updates_same_row(self, monkeypatch):
        _clear("Dup@Lumen.AI")
        monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "s3cret")
        client.post(
            "/api/admin/bootstrap",
            json={"username": "Dup@Lumen.AI", "password": "FirstPassword123"},
            headers={"X-Bootstrap-Token": "s3cret"},
        )
        client.post(
            "/api/admin/bootstrap",
            json={"username": "dup@lumen.ai", "password": "SecondPassword123"},
            headers={"X-Bootstrap-Token": "s3cret"},
        )

        db = SessionLocal()
        try:
            rows = db.query(AdminCredential).filter(
                AdminCredential.username.in_(["Dup@Lumen.AI", "dup@lumen.ai"])
            ).all()
            assert len(rows) == 1  # updated in place, not duplicated
        finally:
            db.close()

        # The second (most recent) password is the one that works now.
        login = client.post(
            "/api/auth/login",
            json={"email": "DUP@LUMEN.AI", "password": "SecondPassword123"},
        )
        assert login.status_code == 200, login.text
