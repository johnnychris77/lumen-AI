"""P472-03 PA-1 remediation — canonical production determination and fail-closed gates.

Covers RB-T38…RB-T40 (converted in ``test_p472_03_batch8_pa1_env_gates.py``) at every layer:

1. ``app.core.environment``: one determination (APP_ENV or ENVIRONMENT, case-insensitive),
   conflicts, and the startup refusal list.
2. Runtime defence in depth: with a production signal set *after* import (no ``app.main``
   startup check in the way), every development / demo credential is refused at its gate:
   dev-token map, demo token (three readers), enterprise dev mode, JWT-shape check,
   portfolio literal token, demo routes. Destructive demo reset persists nothing.
3. Development workflows outside production are preserved.
4. No new privileged pathway: the PA1-04 portfolio role/email grants stay inert.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.main  # noqa: F401  (import once, before any test sets a production signal at runtime)
from app.routers.auth_simple import _make_token  # same reason: refuses a missing SECRET_KEY in production
from app.core import environment as envmod
from app.core.environment import determine_environment, is_production, production_configuration_errors

STRONG = "pa1-remediation-strong-secret-0123456789abcdef"
RENDER = {"APP_ENV": "production", "ENVIRONMENT": "production", "AUTH_MODE": "oidc", "ENABLE_DEV_AUTH": "false",
          "SECRET_KEY": STRONG}


def _request(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "query_string": b""})


# --------------------------------------------------------------------------- 1. determination
class TestCanonicalDetermination:
    @pytest.mark.parametrize("env", [
        {"APP_ENV": "production"}, {"ENVIRONMENT": "production"}, {"APP_ENV": "prod"}, {"ENVIRONMENT": "PROD"},
        {"APP_ENV": " Production "}, {"APP_ENV": "Production", "ENVIRONMENT": "Production"},
        {"APP_ENV": "production", "ENVIRONMENT": "prod"},
    ])
    def test_any_production_signal_is_production(self, env):
        d = determine_environment(env)
        assert d.is_production is True and d.conflict is None

    @pytest.mark.parametrize("env", [
        {}, {"APP_ENV": "development"}, {"APP_ENV": "test"}, {"ENVIRONMENT": "staging"},
        {"APP_ENV": "", "ENVIRONMENT": "  "}, {"APP_ENV": "development", "ENVIRONMENT": "test"},
    ])
    def test_no_production_signal_is_not_production(self, env):
        d = determine_environment(env)
        assert d.is_production is False and d.conflict is None

    @pytest.mark.parametrize("env", [
        {"APP_ENV": "development", "ENVIRONMENT": "production"},
        {"APP_ENV": "production", "ENVIRONMENT": "development"},
        {"APP_ENV": "prod", "ENVIRONMENT": "staging"},
    ])
    def test_conflicting_signals_are_production_and_a_conflict(self, env):
        d = determine_environment(env)
        assert d.is_production is True  # every runtime gate fails closed
        assert d.conflict and "conflicting environment signals" in d.conflict

    def test_is_production_reads_the_process_environment_when_no_mapping_is_given(self, monkeypatch):
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "Production")
        assert is_production() is True
        monkeypatch.setenv("ENVIRONMENT", "development")
        assert is_production() is False


class TestStartupRefusalList:
    def test_render_configuration_has_no_errors(self):
        assert production_configuration_errors(RENDER) == []

    def test_non_production_has_no_errors_even_with_dev_settings(self):
        assert production_configuration_errors({"APP_ENV": "test", "ENABLE_DEV_AUTH": "true", "DEMO_MODE": "1",
                                                "AUTH_MODE": "dev"}) == []

    @pytest.mark.parametrize("override, needle", [
        ({"ENVIRONMENT": "development"}, "conflicting environment signals"),
        ({"AUTH_MODE": ""}, "AUTH_MODE is not set"),
        ({"AUTH_MODE": "dev"}, "AUTH_MODE=dev is not permitted"),
        ({"AUTH_MODE": "dev", "ALLOW_DEV_AUTH_IN_PROD": "true"}, "ALLOW_DEV_AUTH_IN_PROD is no longer honoured"),
        ({"AUTH_MODE": "something"}, "AUTH_MODE=something is not permitted"),
        ({"ENABLE_DEV_AUTH": "true"}, "ENABLE_DEV_AUTH is enabled"),
        ({"ENABLE_DEV_AUTH": "1"}, "ENABLE_DEV_AUTH is enabled"),
        ({"DEMO_MODE": "1"}, "DEMO_MODE is enabled"),
        ({"DEMO_MODE": "true"}, "DEMO_MODE is enabled"),
        ({"SECRET_KEY": "dev-secret-change-in-production"}, "SECRET_KEY is unset or a known-weak"),
    ])
    def test_each_unsafe_production_setting_is_refused(self, override, needle):
        errors = production_configuration_errors({**RENDER, **override})
        assert any(needle in e for e in errors), errors

    @pytest.mark.parametrize("override", [{"DEMO_MODE": "0"}, {"DEMO_MODE": "false"}, {"ENABLE_DEV_AUTH": "no"},
                                          {"AUTH_MODE": " OIDC "}])
    def test_explicitly_disabled_flags_are_accepted(self, override):
        assert production_configuration_errors({**RENDER, **override}) == []

    def test_refusal_message_is_fatal_and_lists_every_error(self):
        msg = envmod.startup_refusal_message({**RENDER, "ENABLE_DEV_AUTH": "true", "DEMO_MODE": "1"})
        assert msg.startswith("FATAL: refusing to start") and "ENABLE_DEV_AUTH" in msg and "DEMO_MODE" in msg
        assert envmod.startup_refusal_message(RENDER) is None


# --------------------------------------------------------------------------- 2. runtime gates
@pytest.fixture
def production_at_runtime(monkeypatch):
    """A production signal set after every module was imported (ENVIRONMENT only, the RB-T38 shape)."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert is_production() is True
    return monkeypatch


class TestRuntimeGatesFailClosed:
    def test_dev_token_map_is_inert(self, production_at_runtime):
        from app import deps

        # Simulate a module imported before the production signal appeared (map populated, flag on).
        production_at_runtime.setattr(deps, "_DEV_AUTH_ACTIVE", True)
        production_at_runtime.setattr(deps, "_DEV_ROLE_MAP", {"dev-token": "admin"})
        assert deps.dev_token_role("dev-token") is None
        with pytest.raises(HTTPException) as exc:
            deps.get_current_user(authorization="Bearer dev-token", db=None)
        assert exc.value.status_code == 401

    def test_dev_token_rejected_by_legacy_get_current_user(self, production_at_runtime):
        from app import deps
        from app.auth import get_current_user

        production_at_runtime.setattr(deps, "_DEV_AUTH_ACTIVE", True)
        production_at_runtime.setattr(deps, "_DEV_ROLE_MAP", {"dev-token": "admin"})

        with pytest.raises(HTTPException) as exc:
            get_current_user(_request({"Authorization": "Bearer dev-token"}))
        assert exc.value.status_code == 401

    @pytest.mark.parametrize("reader", ["app.auth", "access_control", "enterprise_auth"])
    def test_demo_token_rejected_everywhere(self, production_at_runtime, reader):
        production_at_runtime.setenv("DEMO_MODE", "1")
        from app import deps

        production_at_runtime.setattr(deps, "_DEV_AUTH_ACTIVE", True)
        production_at_runtime.setattr(deps, "_DEV_ROLE_MAP", {"dev-token": "admin"})
        if reader == "app.auth":
            from app.auth import get_current_user

            with pytest.raises(HTTPException):
                get_current_user(_request({"Authorization": "Bearer demo-token"}))
        elif reader == "access_control":
            from app.enterprise_access_control import infer_actor_and_role

            assert infer_actor_and_role({"authorization": "Bearer demo-token"}) == ("unknown", "viewer")
            assert infer_actor_and_role({"authorization": "Bearer dev-token"}) == ("unknown", "viewer")
        else:
            from app import enterprise_auth

            assert enterprise_auth.is_demo_mode() is False

    def test_tenant_authz_dev_token_rejected(self, production_at_runtime):
        from app import deps
        from app.tenant_authz import _resolve_user_email_from_token

        production_at_runtime.setattr(deps, "_DEV_AUTH_ACTIVE", True)
        production_at_runtime.setattr(deps, "_DEV_ROLE_MAP", {"dev-token": "admin"})

        with pytest.raises(HTTPException) as exc:
            _resolve_user_email_from_token(_request({"Authorization": "Bearer dev-token"}))
        assert exc.value.status_code == 401

    def test_enterprise_dev_mode_refuses_header_identity(self, production_at_runtime):
        from app import enterprise_auth

        production_at_runtime.setenv("AUTH_MODE", "dev")
        with pytest.raises(HTTPException) as exc:
            enterprise_auth._require_dev_auth_context(_request({
                "Authorization": "Bearer dev-token", "X-LumenAI-Role": "admin", "X-LumenAI-Tenant-Id": "victim"}))
        assert exc.value.status_code == 401

    def test_enterprise_jwt_shape_check_runs_on_any_production_signal(self, production_at_runtime):
        from app import enterprise_auth

        production_at_runtime.delenv("ENVIRONMENT")
        production_at_runtime.setenv("APP_ENV", "PROD")
        with pytest.raises(HTTPException) as exc:
            enterprise_auth.require_enterprise_auth(_request({"Authorization": "Bearer dev-token"}))
        assert exc.value.status_code == 401 and "signed JWT" in exc.value.detail

    def test_portfolio_literal_dev_token_grants_nothing(self, production_at_runtime):
        from app.portfolio_authz import require_portfolio_access

        with pytest.raises(HTTPException) as exc:
            require_portfolio_access(current_user={}, authorization="Bearer dev-token")
        assert exc.value.status_code == 403

    def test_demo_reset_is_refused_and_deletes_nothing(self, production_at_runtime):
        from app.db.session import SessionLocal
        from app.main import app
        from app.models.pilot import PilotStatus

        production_at_runtime.setenv("DEMO_MODE", "1")
        db = SessionLocal()
        try:
            row = PilotStatus(tenant_id="demo", facility_id="pa1-remediation",
                              pilot_end_date=datetime.now(timezone.utc) + timedelta(days=30))
            db.add(row)
            db.commit()
            row_id = row.id
        finally:
            db.close()
        client = TestClient(app, raise_server_exceptions=False)
        for token in ("dev-token", "demo-token"):
            resp = client.get("/api/demo/reset", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403, resp.text
            assert "disabled in production" in resp.json()["detail"]
        db = SessionLocal()
        try:
            assert db.get(PilotStatus, row_id) is not None
            db.query(PilotStatus).filter(PilotStatus.id == row_id).delete()
            db.commit()
        finally:
            db.close()

    def test_settings_is_production_follows_the_canonical_determination(self, production_at_runtime):
        from app.config import get_settings

        assert get_settings().is_production is True


# --------------------------------------------------------------------------- 3. dev workflows kept
class TestDevelopmentWorkflowsPreserved:
    def test_dev_token_works_outside_production(self, monkeypatch):
        from app import deps

        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setattr(deps, "_DEV_AUTH_ACTIVE", True)
        monkeypatch.setattr(deps, "_DEV_ROLE_MAP", {"dev-token": "admin"})
        assert is_production() is False
        assert deps.dev_token_role("dev-token") == "admin"

    def test_demo_reset_works_outside_production(self, monkeypatch):
        from app.main import app

        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("DEMO_MODE", "1")
        resp = TestClient(app).get("/api/demo/reset", headers={"Authorization": "Bearer demo-token"})
        assert resp.status_code == 200 and resp.json()["status"] == "reset"


# --------------------------------------------------------------------------- 4. no new privilege
class TestNoNewPrivilegedPathway:
    @pytest.mark.parametrize("principal", [
        {"role": "platform_admin", "email": "pa@example.invalid"},
        {"role": "tenant_admin", "email": "ta@example.invalid"},
        {"role": "admin", "email": "admin@local"},
    ])
    def test_portfolio_role_and_email_grants_remain_inert(self, monkeypatch, principal):
        """PA1-04 is unchanged on purpose: activating all-tenant access needs PA-1 and GD-8."""
        from app.portfolio_authz import require_portfolio_access

        monkeypatch.delenv("ENVIRONMENT", raising=False)
        with pytest.raises(HTTPException) as exc:
            require_portfolio_access(current_user=principal, authorization="Bearer a.b.c")
        assert exc.value.status_code == 403

    def test_environment_module_grants_nothing(self):
        import inspect

        source = inspect.getsource(envmod)
        for forbidden in ("tenant_admin", "platform_admin", "BOOTSTRAP", "app.models", "Session", "grant_"):
            assert forbidden not in source


# --------------------------------------------------------------------------- 5. legitimate production auth kept
class TestLegitimateProductionAuthenticationPreserved:
    def test_oidc_jwt_passes_the_production_shape_check_and_maps_claims(self, production_at_runtime):
        """The RB-T40 shape check only rejects non-JWT bearers; a verified OIDC token is still accepted."""
        import base64
        import json

        from app import enterprise_auth

        def b64(obj):
            return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

        now = int(datetime.now(timezone.utc).timestamp())
        claims = {"sub": "oidc-subject-pa1", "email": "oidc.pa1@example.invalid", "iss": "https://issuer.example.com/",
                  "aud": "lumenai-api", "exp": now + 1800, "iat": now - 60, "roles": ["hospital_admin"],
                  "tenant_id": "tenant-oidc-pa1", "tenant_name": "OIDC Tenant"}
        token = f"{b64({'alg': 'RS256', 'typ': 'JWT', 'kid': 'k'})}.{b64(claims)}.signature"
        for name, value in {"AUTH_MODE": "oidc", "OIDC_ISSUER_URL": "https://issuer.example.com/",
                            "OIDC_AUDIENCE": "lumenai-api", "OIDC_JWKS_URL": "https://issuer.example.com/jwks",
                            "OIDC_ALGORITHMS": "RS256"}.items():
            production_at_runtime.setenv(name, value)
        production_at_runtime.setattr("app.enterprise_auth.validate_jwt_signature_with_jwks", lambda t: claims)
        from app.db import models
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            exists = db.query(models.TenantMembership).filter_by(
                tenant_id="tenant-oidc-pa1", user_email="oidc.pa1@example.invalid").first()
            if exists is None:
                db.add(models.TenantMembership(tenant_id="tenant-oidc-pa1", user_email="oidc.pa1@example.invalid",
                                               role="viewer", is_enabled=True))
                db.commit()
        finally:
            db.close()
        ctx = enterprise_auth.require_enterprise_auth(_request({"Authorization": f"Bearer {token}",
                                                                "X-LumenAI-Tenant-Id": "spoofed"}))
        assert ctx.tenant_id == "tenant-oidc-pa1" and ctx.actor in ("oidc.pa1@example.invalid", "oidc-subject-pa1")

    def test_signed_per_user_jwt_still_authenticates_in_production(self, production_at_runtime):
        from app import enterprise_auth

        production_at_runtime.setenv("AUTH_MODE", "dev")  # a process that skipped app.main's refusal
        ctx = enterprise_auth._require_dev_auth_context(
            _request({"Authorization": f"Bearer {_make_token('pa1-user@example.invalid')}"}))
        assert ctx.actor == "pa1-user@example.invalid"
        assert ctx.role != "admin"  # role resolved server-side, never from a header
