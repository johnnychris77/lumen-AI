"""Regression tests for the header-role privilege-escalation hardening.

Before this fix:
  * app.auth.get_current_user read identity/role straight from client headers
    and never raised — routes "protected" by it were effectively open.
  * enterprise_access_control.infer_actor_and_role granted `admin` to any
    request whose Authorization header merely CONTAINED "dev-token", and
    honored an arbitrary X-LumenAI-Role header. That feeds a BLOCKING policy
    gate in run_reset_app's middleware.

These tests lock in that role now comes only from a verifiable source
(dev-token map / validated JWT), never from the X-LumenAI-Role header.
"""
import pytest


def test_get_current_user_rejects_missing_bearer():
    from fastapi import HTTPException, Request

    from app.auth import get_current_user

    scope = {
        "type": "http",
        "headers": [(b"x-lumenai-role", b"admin")],  # header alone must not authenticate
    }
    with pytest.raises(HTTPException) as exc:
        get_current_user(Request(scope))
    assert exc.value.status_code == 401


def test_get_current_user_ignores_header_role_for_dev_token():
    """A valid dev-token authenticates, but the caller's real (mapped) role
    wins over any X-LumenAI-Role the client asserts."""
    from fastapi import Request

    from app.auth import get_current_user

    # viewer-token maps to the viewer role; the header claims admin.
    scope = {
        "type": "http",
        "headers": [
            (b"authorization", b"Bearer viewer-token"),
            (b"x-lumenai-role", b"admin"),
        ],
    }
    user = get_current_user(Request(scope))
    assert user["role"] == "viewer", "header role must not escalate a dev token"


def test_infer_actor_and_role_does_not_grant_admin_from_bare_dev_token_string():
    """The old code returned admin whenever the header CONTAINED 'dev-token'
    and honored X-LumenAI-Role. Neither may grant privilege now."""
    from app.enterprise_access_control import infer_actor_and_role

    # Attacker crafts a bogus bearer that merely contains the substring, plus
    # an admin role header. Must resolve to the un-privileged default.
    headers = {
        "authorization": "Bearer not-a-real-dev-token-abc",
        "x-lumenai-role": "admin",
    }
    actor, role = infer_actor_and_role(headers)
    assert role == "viewer"
    assert actor == "unknown"


def test_infer_actor_and_role_resolves_real_dev_token_role():
    from app.enterprise_access_control import infer_actor_and_role

    # operator-token maps to operator; header claiming admin is ignored.
    headers = {
        "authorization": "Bearer operator-token",
        "x-lumenai-role": "admin",
    }
    _actor, role = infer_actor_and_role(headers)
    assert role == "operator"


def test_infer_actor_and_role_unauthenticated_is_viewer():
    from app.enterprise_access_control import infer_actor_and_role

    assert infer_actor_and_role({}) == ("unknown", "viewer")
