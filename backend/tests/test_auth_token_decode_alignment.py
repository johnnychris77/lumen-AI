"""A token signed by auth_simple must be decodable by the deps auth path.

Regression: deps._decode_jwt returned None whenever SECRET_KEY was unset, while
auth_simple signs login tokens with a fixed fallback secret in that case. The
mismatch silently 401'd every /api/history* endpoint, so the dashboard showed
"—" for Total Inspections and Inspection History stayed empty.
"""
from app.routers.auth_simple import _make_token
from app.deps import _decode_jwt, _signing_secret


def test_login_token_decodes_in_deps():
    token = _make_token("alice@hospital.org")
    payload = _decode_jwt(token)
    assert payload is not None, "token signed by auth_simple must decode in deps"
    assert payload.get("sub") == "alice@hospital.org"


def test_signing_secret_resolves():
    # Must resolve to a non-empty secret so decode never silently no-ops.
    assert _signing_secret()
