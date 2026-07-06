"""Regression test for a production bug: any deployment that hasn't
explicitly set AUTH_MODE=oidc (i.e. every deployment that leaves it at the
"dev" default) could never authenticate a real logged-in user against
enterprise-scoped routes (app/enterprise_auth.py's require_enterprise_auth) —
_require_dev_auth_context only ever accepted an exact match against the
shared DEV_AUTH_TOKEN/demo-token, never a real JWT issued by /auth/login.
Every real user's session was silently locked out of every route gated by
require_enterprise_auth (e.g. /api/network/baselines), while routes gated by
app.deps.get_current_user (e.g. /api/history/summary) worked fine — causing
the frontend's blanket "any 401 signs you out" rule to bounce a freshly
logged-in user straight back to /login.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.db.session import SessionLocal
from app.models.user_role_assignment import UserRoleAssignment


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({"type": "http", "method": "GET", "path": "/test", "headers": headers})


def _upsert_role(username: str, role: str) -> None:
    db = SessionLocal()
    try:
        db.query(UserRoleAssignment).filter(UserRoleAssignment.username == username).delete()
        db.add(UserRoleAssignment(username=username, role=role, assigned_by="test"))
        db.commit()
    finally:
        db.close()


def _mint_token(username: str) -> str:
    from app.routers.auth_simple import _make_token

    return _make_token(username)


def test_dev_auth_mode_accepts_real_user_jwt(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")
    _upsert_role("real.user@hospital.org", "spd_manager")
    token = _mint_token("real.user@hospital.org")

    request = _request([(b"authorization", f"Bearer {token}".encode())])
    context = get_auth_context(request)

    assert context.actor == "real.user@hospital.org"
    assert context.role == "spd_manager"


def test_dev_auth_mode_still_rejects_garbage_token(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request([(b"authorization", b"Bearer not-a-real-jwt")])

    with pytest.raises(HTTPException) as exc:
        get_auth_context(request)
    assert exc.value.status_code == 401


def test_dev_auth_mode_real_jwt_role_defaults_to_viewer_when_unassigned(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    db = SessionLocal()
    try:
        db.query(UserRoleAssignment).filter(
            UserRoleAssignment.username == "no.role@hospital.org"
        ).delete()
        db.commit()
    finally:
        db.close()

    token = _mint_token("no.role@hospital.org")
    request = _request([(b"authorization", f"Bearer {token}".encode())])
    context = get_auth_context(request)

    assert context.actor == "no.role@hospital.org"
    assert context.role == "viewer"
