import os
from datetime import UTC, datetime, timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _claims(**overrides):
    now = datetime.now(UTC)

    base = {
        "sub": "user-subject-123",
        "email": "user@example.com",
        "iss": "https://issuer.example.com/",
        "aud": "lumenai-api",
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "roles": ["hospital_admin"],
        "tenant_id": "tenant-a",
        "tenant_name": "Tenant A",
    }

    base.update(overrides)
    return base


def test_validate_jwt_claims_accepts_valid_claims():
    from app.auth.jwt_validator import validate_jwt_claims

    claims = _claims()

    result = validate_jwt_claims(
        claims,
        expected_issuer="https://issuer.example.com/",
        expected_audience="lumenai-api",
    )

    assert result["email"] == "user@example.com"


def test_validate_jwt_claims_rejects_missing_required_claim():
    from app.auth.jwt_validator import JWTValidationError, validate_jwt_claims

    claims = _claims()
    claims.pop("email")

    with pytest.raises(JWTValidationError) as exc:
        validate_jwt_claims(
            claims,
            expected_issuer="https://issuer.example.com/",
            expected_audience="lumenai-api",
        )

    assert "Missing required JWT claim: email" in str(exc.value)


def test_validate_jwt_claims_rejects_wrong_issuer():
    from app.auth.jwt_validator import JWTValidationError, validate_jwt_claims

    with pytest.raises(JWTValidationError) as exc:
        validate_jwt_claims(
            _claims(iss="https://wrong-issuer.example.com/"),
            expected_issuer="https://issuer.example.com/",
            expected_audience="lumenai-api",
        )

    assert "Invalid JWT issuer" in str(exc.value)


def test_validate_jwt_claims_rejects_wrong_audience():
    from app.auth.jwt_validator import JWTValidationError, validate_jwt_claims

    with pytest.raises(JWTValidationError) as exc:
        validate_jwt_claims(
            _claims(aud="wrong-api"),
            expected_issuer="https://issuer.example.com/",
            expected_audience="lumenai-api",
        )

    assert "Invalid JWT audience" in str(exc.value)


def test_validate_jwt_claims_accepts_audience_list():
    from app.auth.jwt_validator import validate_jwt_claims

    result = validate_jwt_claims(
        _claims(aud=["other-api", "lumenai-api"]),
        expected_issuer="https://issuer.example.com/",
        expected_audience="lumenai-api",
    )

    assert result["aud"] == ["other-api", "lumenai-api"]


def test_validate_jwt_claims_rejects_expired_token():
    from app.auth.jwt_validator import JWTValidationError, validate_jwt_claims

    expired = int((datetime.now(UTC) - timedelta(minutes=10)).timestamp())

    with pytest.raises(JWTValidationError) as exc:
        validate_jwt_claims(
            _claims(exp=expired),
            expected_issuer="https://issuer.example.com/",
            expected_audience="lumenai-api",
        )

    assert "JWT is expired" in str(exc.value)


def test_validate_jwt_claims_rejects_future_iat():
    from app.auth.jwt_validator import JWTValidationError, validate_jwt_claims

    future_iat = int((datetime.now(UTC) + timedelta(minutes=10)).timestamp())

    with pytest.raises(JWTValidationError) as exc:
        validate_jwt_claims(
            _claims(iat=future_iat),
            expected_issuer="https://issuer.example.com/",
            expected_audience="lumenai-api",
        )

    assert "issued-at time is in the future" in str(exc.value)


def test_map_claims_to_auth_context_payload():
    from app.auth.jwt_validator import map_claims_to_auth_context_payload

    payload = map_claims_to_auth_context_payload(_claims())

    assert payload["actor"] == "user@example.com"
    assert payload["subject"] == "user-subject-123"
    assert payload["role"] == "hospital_admin"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["tenant_name"] == "Tenant A"
    assert payload["auth_provider"] == "oidc"
    assert payload["issuer"] == "https://issuer.example.com/"


def test_map_claims_to_auth_context_payload_requires_tenant_claim():
    from app.auth.jwt_validator import (
        JWTValidationError,
        map_claims_to_auth_context_payload,
    )

    claims = _claims()
    claims.pop("tenant_id")
    claims.pop("tenant_name")

    with pytest.raises(JWTValidationError) as exc:
        map_claims_to_auth_context_payload(claims)

    assert "Missing required JWT tenant claim" in str(exc.value)


def test_map_claims_to_auth_context_payload_can_allow_default_tenant_for_dev_like_use():
    from app.auth.jwt_validator import map_claims_to_auth_context_payload

    claims = _claims()
    claims.pop("tenant_id")
    claims.pop("tenant_name")

    payload = map_claims_to_auth_context_payload(
        claims,
        require_tenant_claim=False,
    )

    assert payload["tenant_id"] == "default-tenant"
