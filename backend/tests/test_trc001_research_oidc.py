"""TRC-001 research API — OIDC authentication integration tests (requirements 4-5).

These exercise the REAL `require_verified_oidc_context` dependency end-to-end — it is NOT
overridden. Tokens are genuine RS256 JWTs signed by a test RSA key; a controlled JWKS
fixture is provided by stubbing only the network key-fetch boundary
(`app.auth.jwks_validator._get_jwks_client`) to return the matching public key. Every
other step (header/alg allowlist, signature verification, issuer/audience/exp claim
validation, claim->context mapping, and enabled tenant-membership resolution) runs for
real with OIDC configuration enabled.

Only synthetic images are used; no real photographs or private kit.
"""
from __future__ import annotations

import hashlib
import io
import json
import time
import types

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import jwks_validator
from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.governance_approval import GovernanceApproval
from app.models.retained_image import RetainedImage
from app.models.user_role_assignment import UserRoleAssignment

client = TestClient(app)

ISS = "https://idp.trc001.test/"
AUD = "lumenai-research"
JWKS_URL = "https://idp.trc001.test/.well-known/jwks.json"
TENANT = "trc-oidc-tenant"
DATASET = "TRC-001-OIDC-DS"
EMAIL = "owner-oidc@x"
SUBJECT = "oidc-sub-owner-1"


def _mk_key():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())
    return priv, pem


_PRIV, _PRIV_PEM = _mk_key()
_PUB = _PRIV.public_key()
_PRIV2, _PRIV2_PEM = _mk_key()  # a DIFFERENT, wrong key for signature-failure tests


def _token(*, sub=SUBJECT, email=EMAIL, tenant_id=TENANT, role="technician", iss=ISS,
           aud=AUD, exp_delta=3600, kid="test-key-1", alg="RS256", key_pem=None):
    now = int(time.time())
    claims = {"iss": iss, "aud": aud, "sub": sub, "email": email, "lumenai_role": role,
              "tenant_id": tenant_id, "iat": now, "exp": now + exp_delta}
    return pyjwt.encode(claims, key_pem or _PRIV_PEM, algorithm=alg, headers={"kid": kid})


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _jpeg(color=(10, 20, 30), size=(64, 48)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


@pytest.fixture()
def oidc(monkeypatch, tmp_path):
    """Configure OIDC + a controlled JWKS fixture; seed membership; synthetic kit; cleanup."""
    from research.lens_vision.trc001_intake import TRC001_IMAGES
    monkeypatch.setenv("OIDC_ISSUER_URL", ISS)
    monkeypatch.setenv("OIDC_AUDIENCE", AUD)
    monkeypatch.setenv("OIDC_JWKS_URL", JWKS_URL)
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    monkeypatch.setenv("TRC001_DATASET_ID", DATASET)

    # Controlled JWKS fixture: key-fetch boundary returns our test public key.
    monkeypatch.setattr(
        jwks_validator, "_get_jwks_client",
        lambda url: types.SimpleNamespace(
            get_signing_key_from_jwt=lambda token: types.SimpleNamespace(key=_PUB)),
    )

    # Synthetic kit.
    images, hashes = [], []
    for image_id, spec in TRC001_IMAGES.items():
        data = _jpeg(color=(10, 20, 30) if "EXT" in image_id else (40, 50, 60))
        (tmp_path / f"{image_id}.jpg").write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        hashes.append(h)
        images.append({"image_id": image_id, "filename": f"{image_id}.jpg", "sha256": h,
                       "content_type": "image/jpeg", "width": 64, "height": 48,
                       "modality": spec["modality"]})
    (tmp_path / "manifest.json").write_text(json.dumps({"instrument_id": "TRC-001", "images": images}))
    monkeypatch.setenv("TRC001_PRIVATE_KIT_DIR", str(tmp_path))

    s = SessionLocal()
    s.add(models.TenantMembership(tenant_id=TENANT, user_email=EMAIL, role="technician", is_enabled=True))
    s.add(UserRoleAssignment(username=EMAIL, role="technician"))
    s.commit()
    created = {"retained": []}
    try:
        yield {"s": s, "hashes": hashes, "created": created}
    finally:
        s.query(models.TenantMembership).filter(models.TenantMembership.user_email == EMAIL).delete()
        s.query(UserRoleAssignment).filter(UserRoleAssignment.username == EMAIL).delete()
        s.query(GovernanceApproval).filter(
            GovernanceApproval.request_type == api_req(), GovernanceApproval.target_resource_id == DATASET).delete()
        s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                      RetainedImage.source == "trc001_research_intake").delete()
        s.commit()
        s.close()


def api_req():
    from app.routes.trc001_research import REQ_OWNER_ATTESTATION
    return REQ_OWNER_ATTESTATION


def _attest_body(hashes):
    return {"ownership_asserted": True, "permissible_research_use": "independent nonclinical research",
            "retention_authorized": True, "withdrawal_procedure": "email governance to withdraw",
            "image_sha256": hashes, "owner_signing_acknowledged": True}


# ── valid verified token: full chain succeeds ───────────────────────────────

def test_valid_oidc_token_accepted(oidc):
    r = client.post("/api/research/trc001/owner-attestation",
                    headers=_bearer(_token()), json=_attest_body(oidc["hashes"]))
    assert r.status_code == 200, r.text
    assert r.json()["basis"] == "owner_attested"


# ── requirement 5 rejections (OIDC configured) ───────────────────────────────

def test_invalid_signature_rejected(oidc):
    # Signed with the WRONG private key; JWKS returns the correct public key.
    tok = _token(key_pem=_PRIV2_PEM)
    r = client.post("/api/research/trc001/owner-attestation", headers=_bearer(tok),
                    json=_attest_body(oidc["hashes"]))
    assert r.status_code == 401


def test_expired_token_rejected(oidc):
    tok = _token(exp_delta=-3600)
    r = client.post("/api/research/trc001/owner-attestation", headers=_bearer(tok),
                    json=_attest_body(oidc["hashes"]))
    assert r.status_code == 401


def test_wrong_issuer_rejected(oidc):
    tok = _token(iss="https://evil-idp.test/")
    r = client.post("/api/research/trc001/owner-attestation", headers=_bearer(tok),
                    json=_attest_body(oidc["hashes"]))
    assert r.status_code == 401


def test_wrong_audience_rejected(oidc):
    tok = _token(aud="some-other-audience")
    r = client.post("/api/research/trc001/owner-attestation", headers=_bearer(tok),
                    json=_attest_body(oidc["hashes"]))
    assert r.status_code == 401


def test_missing_tenant_membership_rejected(oidc):
    # Valid token, but the actor is not an enabled member of the token's tenant.
    tok = _token(tenant_id="tenant-with-no-membership")
    r = client.post("/api/research/trc001/owner-attestation", headers=_bearer(tok),
                    json=_attest_body(oidc["hashes"]))
    assert r.status_code == 403


def test_application_hs256_jwt_rejected(oidc):
    # An application-local HS256 JWT (alg outside the RS256 allowlist) is rejected.
    tok = _token(alg="HS256", key_pem="app-local-shared-secret")
    r = client.post("/api/research/trc001/owner-attestation", headers=_bearer(tok),
                    json=_attest_body(oidc["hashes"]))
    assert r.status_code == 401


def test_alg_none_unsigned_rejected(oidc):
    now = int(time.time())
    claims = {"iss": ISS, "aud": AUD, "sub": SUBJECT, "email": EMAIL, "tenant_id": TENANT,
              "iat": now, "exp": now + 3600}
    tok = pyjwt.encode(claims, key=None, algorithm="none", headers={"kid": "test-key-1"})
    r = client.post("/api/research/trc001/owner-attestation", headers=_bearer(tok),
                    json=_attest_body(oidc["hashes"]))
    assert r.status_code == 401


def test_mismatched_subject_blocks_intake(oidc):
    # Attest under subject S1, then present a verified token for the same actor but a
    # DIFFERENT subject S2 at intake -> runner refuses (subject binding), BLOCKED.
    s = oidc["s"]
    a = client.post("/api/research/trc001/owner-attestation",
                    headers=_bearer(_token(sub="subject-S1")), json=_attest_body(oidc["hashes"]))
    assert a.status_code == 200
    r = client.post("/api/research/trc001/intake", headers=_bearer(_token(sub="subject-S2")))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "BLOCKED_AUTHORIZATION" and body["imported_count"] == 0
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0


def test_full_oidc_happy_path_intake(oidc):
    # End-to-end with matching subject: attest then intake -> INGESTED, unknown GT.
    s = oidc["s"]
    assert client.post("/api/research/trc001/owner-attestation",
                       headers=_bearer(_token()), json=_attest_body(oidc["hashes"])).status_code == 200
    r = client.post("/api/research/trc001/intake", headers=_bearer(_token()))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "INGESTED" and body["imported_count"] == 2
    for img in body["images"]:
        assert img["ground_truth_status"] == "unknown" and img["research_training_eligible"] is False
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() >= 2
