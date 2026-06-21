"""
End-to-end JWKS integration tests using a locally generated RSA key pair.

No external network calls are made. PyJWKClient is patched to return a
signing key derived from the locally generated RSA private key, so the
full pyjwt.decode() path (signature verification, algorithm check,
claim validation) executes against a real cryptographic signature.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")

# ---------------------------------------------------------------------------
# RSA key pair generated once for the entire module
# ---------------------------------------------------------------------------

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()
_PUBLIC_KEY_PEM = _PUBLIC_KEY.public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

_KID = "integration-test-key"
_ISSUER = "https://issuer.example.com/"
_AUDIENCE = "lumenai-api"


def _make_token(
    *,
    algorithm: str = "RS256",
    kid: str | None = _KID,
    iss: str = _ISSUER,
    aud: str = _AUDIENCE,
    extra_claims: dict | None = None,
    sign_with=None,
) -> str:
    now = datetime.now(UTC)
    headers: dict = {"alg": algorithm, "typ": "JWT"}
    if kid is not None:
        headers["kid"] = kid

    payload: dict = {
        "sub": "test-user",
        "email": "test@example.com",
        "iss": iss,
        "aud": aud,
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "roles": ["hospital_admin"],
        "tenant_id": "tenant-integration",
        "tenant_name": "Integration Tenant",
    }
    if extra_claims:
        payload.update(extra_claims)

    key = sign_with if sign_with is not None else _PRIVATE_KEY
    return pyjwt.encode(payload, key, algorithm=algorithm, headers=headers)


def _mock_jwks_client(public_key_pem: str):
    """Return a mock PyJWKClient that yields the given PEM public key."""
    mock_signing_key = MagicMock()
    mock_signing_key.key = pyjwt.algorithms.RSAAlgorithm.from_jwk(
        json.dumps(
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": _KID,
                **json.loads(
                    pyjwt.algorithms.RSAAlgorithm(pyjwt.algorithms.RSAAlgorithm.SHA256)
                    .to_jwk(_PUBLIC_KEY)
                ),
            }
        )
    )
    mock_client = MagicMock()
    mock_client.uri = "https://issuer.example.com/.well-known/jwks.json"
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    return mock_client


@pytest.fixture(autouse=True)
def oidc_env(monkeypatch):
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
    monkeypatch.setenv("OIDC_ISSUER_URL", _ISSUER)
    monkeypatch.setenv("OIDC_AUDIENCE", _AUDIENCE)


def _call_validator(token: str) -> dict:
    from app.auth.jwks_validator import validate_jwt_signature_with_jwks

    client = _mock_jwks_client(_PUBLIC_KEY_PEM)
    with patch("app.auth.jwks_validator._get_jwks_client", return_value=client):
        return validate_jwt_signature_with_jwks(token)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_rs256_token_succeeds():
    token = _make_token()
    claims = _call_validator(token)
    assert claims["sub"] == "test-user"
    assert claims["iss"] == _ISSUER
    assert claims["aud"] == _AUDIENCE
    assert claims["tenant_id"] == "tenant-integration"


def test_wrong_audience_fails():
    from app.auth.jwks_validator import JWKSSignatureValidationError

    token = _make_token(aud="wrong-audience")
    with pytest.raises(JWKSSignatureValidationError) as exc:
        _call_validator(token)
    assert "audience" in str(exc.value).lower()


def test_wrong_issuer_fails():
    from app.auth.jwks_validator import JWKSSignatureValidationError

    token = _make_token(iss="https://evil.example.com/")
    with pytest.raises(JWKSSignatureValidationError) as exc:
        _call_validator(token)
    # Caught by pre-check before JWKS call
    assert "issuer" in str(exc.value).lower()


def test_missing_kid_fails():
    from app.auth.jwks_validator import JWKSSignatureValidationError

    token = _make_token(kid=None)
    with pytest.raises(JWKSSignatureValidationError) as exc:
        _call_validator(token)
    assert "kid" in str(exc.value).lower()


def test_hs256_algorithm_confusion_fails():
    from app.auth.jwks_validator import JWKSSignatureValidationError

    # HS256 token signed with a symmetric secret — must be rejected by allowlist
    token = _make_token(algorithm="HS256", sign_with="supersecret")
    with pytest.raises(JWKSSignatureValidationError) as exc:
        _call_validator(token)
    assert "not allowed" in str(exc.value).lower()


def test_expired_token_fails():
    from app.auth.jwks_validator import JWKSSignatureValidationError

    past = datetime.now(UTC) - timedelta(hours=2)
    token = _make_token(
        extra_claims={
            "exp": int((past - timedelta(hours=1)).timestamp()),
            "iat": int((past - timedelta(hours=2)).timestamp()),
        }
    )
    with pytest.raises(JWKSSignatureValidationError) as exc:
        _call_validator(token)
    assert "expired" in str(exc.value).lower()


def test_tampered_signature_fails():
    from app.auth.jwks_validator import JWKSSignatureValidationError

    token = _make_token()
    header, payload, sig = token.split(".")
    tampered = f"{header}.{payload}.invalidsignatureXXX"

    # Use a client that does NOT mock get_signing_key — it must use the real public key
    # but the signature is wrong so pyjwt.decode raises InvalidSignatureError.
    real_client = MagicMock()
    real_signing_key = MagicMock()
    real_signing_key.key = _PUBLIC_KEY
    real_client.uri = "https://issuer.example.com/.well-known/jwks.json"
    real_client.get_signing_key_from_jwt.return_value = real_signing_key

    from app.auth.jwks_validator import validate_jwt_signature_with_jwks

    with patch("app.auth.jwks_validator._get_jwks_client", return_value=real_client):
        with pytest.raises(JWKSSignatureValidationError) as exc:
            validate_jwt_signature_with_jwks(tampered)
    assert "signature" in str(exc.value).lower() or "decode" in str(exc.value).lower()
