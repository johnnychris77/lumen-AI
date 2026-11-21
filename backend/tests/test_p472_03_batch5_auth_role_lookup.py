"""P472-03 Batch 5 — B5.5 ``auth_simple`` role lookup vs the canonical ``users`` schema.

The defect (reproduced before the fix)
--------------------------------------
``app.routers.auth_simple`` queried ``users.username`` and ``users.password_hash``.
The canonical table (ORM ``app.models.user.User`` and Alembic baseline
``4b336d3ed612``) has ``email`` / ``hashed_password`` / ``role``. Every lookup
raised; the exception was swallowed with ``except Exception: pass``:

* ``_user_role`` — called by every authentication path with the validated JWT
  ``sub`` — silently fell back to ``viewer`` whenever the role-assignment table
  had no row, so a role stored on the user row was never applied, and a broken
  query was indistinguishable from "no role" (2,450 PostgreSQL server errors in
  one CI run, nothing in the application log);
* ``_verify_user`` (legacy users-table login) always raised, which ``/api/auth/login``
  turned into 401.

The fix
-------
* ``_user_role``: assignment table, then ``users.role`` looked up by ``email``;
  an exact-case match wins; case-variant rows that disagree are ambiguous and
  fail closed to ``viewer``; any database error is LOGGED and fails closed.
* ``_verify_user``: the legacy users-table password login never worked against
  this schema. Enabling it would add an unreviewed credential source, so it is
  explicitly disabled (logged, returns ``None`` → 401) pending an
  authentication-owner decision (AUTH-1). Login through ``admin_credentials``
  is unchanged.
"""
from __future__ import annotations

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from passlib.hash import bcrypt
from sqlalchemy import text

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.admin_credential import AdminCredential
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment
from app.routers import auth_simple
from app.routers.auth_simple import _make_token, _user_role, _verify_user

RUN = uuid.uuid4().hex[:8]
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)


def _add(*rows):
    db = SessionLocal()
    try:
        for row in rows:
            db.add(row)
        db.commit()
    finally:
        db.close()


def _user(email: str, role: str, password: str = "irrelevant-hash-input") -> User:
    return User(email=email, hashed_password=bcrypt.hash(password), role=role)


class TestCanonicalSchemaIsWhatTheCodeQueries:
    def test_the_users_table_has_email_not_username(self):
        db = SessionLocal()
        try:
            db.execute(text("SELECT email, hashed_password, role FROM users WHERE 1=0")).fetchall()
            with pytest.raises(Exception):
                db.execute(text("SELECT username FROM users WHERE 1=0")).fetchall()
        finally:
            db.rollback()
            db.close()


class TestRoleLookup:
    def test_a_role_stored_on_the_user_row_is_applied(self):
        email = f"b55-row-{RUN}@example.com"
        _add(_user(email, "spd_manager"))
        assert _user_role(email) == "spd_manager"

    def test_email_match_is_case_insensitive(self):
        email = f"b55-case-{RUN}@example.com"
        _add(_user(email, "quality_manager"))
        assert _user_role(email.upper()) == "quality_manager"

    def test_the_assignment_table_still_takes_precedence(self):
        email = f"b55-assign-{RUN}@example.com"
        _add(_user(email, "admin"), UserRoleAssignment(username=email, role="viewer", assigned_by="b5.5"))
        assert _user_role(email) == "viewer"

    def test_unknown_principal_is_least_privilege(self):
        assert _user_role(f"b55-nobody-{RUN}@example.com") == "viewer"
        assert _user_role("") == "viewer"
        assert _user_role("   ") == "viewer"

    def test_case_variant_assignments_that_disagree_fail_closed(self):
        base = f"b55-amb-{RUN}@example.com"
        _add(UserRoleAssignment(username=base, role="viewer", assigned_by="b5.5"),
             UserRoleAssignment(username=base.upper(), role="admin", assigned_by="b5.5"))
        # The exact principal gets its own row; a third spelling cannot pick one.
        assert _user_role(base) == "viewer"
        assert _user_role(base.upper()) == "admin"
        assert _user_role(base.title()) == "viewer"

    def test_a_database_error_is_logged_not_swallowed_and_fails_closed(self, monkeypatch, caplog):
        class Broken:
            def begin(self):
                raise RuntimeError("simulated database outage")
        monkeypatch.setattr(auth_simple, "engine", Broken())
        with caplog.at_level(logging.WARNING, logger="app.routers.auth_simple"):
            assert _user_role(f"b55-err-{RUN}@example.com") == "viewer"
        assert any("role lookup" in r.getMessage() and r.exc_info for r in caplog.records), caplog.text

    def test_no_server_error_is_raised_by_the_role_query(self, caplog):
        # Before the fix this lookup errored on every call (missing column).
        with caplog.at_level(logging.WARNING, logger="app.routers.auth_simple"):
            _user_role(f"b55-quiet-{RUN}@example.com")
        assert not [r for r in caplog.records if "role lookup" in r.getMessage()], caplog.text


class TestRoleFlowsThroughAuthentication:
    def test_a_jwt_principal_gets_its_stored_role(self):
        email = f"b55-jwt-{RUN}@example.com"
        _add(_user(email, "spd_manager"))
        # /api/platform/identity/me reports the role the auth layer resolved.
        response = client.get("/api/auth/tenants", headers={"Authorization": f"Bearer {_make_token(email)}"})
        assert response.status_code == 200
        from app.deps import get_current_user
        db = SessionLocal()
        try:
            principal = get_current_user(authorization=f"Bearer {_make_token(email)}", db=db)
        finally:
            db.close()
        assert principal.role == "spd_manager"

    def test_a_role_header_does_not_change_the_resolved_role(self):
        email = f"b55-hdr-{RUN}@example.com"
        _add(_user(email, "viewer"))
        from app.deps import get_current_user
        db = SessionLocal()
        try:
            principal = get_current_user(authorization=f"Bearer {_make_token(email)}", db=db)
        finally:
            db.close()
        assert principal.role == "viewer"
        response = client.get("/api/v1/system/inference-status",
                              headers={"Authorization": f"Bearer {_make_token(email)}", "X-LumenAI-Role": "admin"})
        assert response.status_code == 403


class TestLegacyUsersTableLogin:
    def test_verify_user_does_not_raise_and_refuses(self, caplog):
        email = f"b55-login-{RUN}@example.com"
        _add(_user(email, "admin", password="correct horse battery staple"))
        with caplog.at_level(logging.WARNING, logger="app.routers.auth_simple"):
            assert _verify_user(email, "correct horse battery staple") is None
        assert any("users-table password login is disabled" in r.getMessage() for r in caplog.records)

    def test_login_with_users_table_credentials_is_refused(self):
        email = f"b55-login2-{RUN}@example.com"
        _add(_user(email, "admin", password="correct horse battery staple"))
        response = client.post("/api/auth/login", json={"username": email, "password": "correct horse battery staple"})
        assert response.status_code == 401

    def test_admin_credential_login_is_unchanged_and_wrong_password_refused(self):
        email = f"b55-cred-{RUN}@example.com"
        _add(AdminCredential(username=email, password_hash=bcrypt.hash("right-password"), role="admin"),
             UserRoleAssignment(username=email, role="spd_manager", assigned_by="b5.5"))
        ok = client.post("/api/auth/login", json={"username": email, "password": "right-password"})
        assert ok.status_code == 200 and ok.json()["role"] == "spd_manager"
        assert client.post("/api/auth/login", json={"username": email, "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"username": email}).status_code == 400
