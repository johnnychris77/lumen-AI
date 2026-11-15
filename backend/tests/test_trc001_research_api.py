"""TRC-001 authenticated research-intake API — negative + happy-path tests.

Covers requirement 8: missing authentication, constructed/dev AuthContext (dev/app-local
token rejected at the boundary), cross-tenant access, mismatched subject, absent
attestation, hash mismatch, withdrawal, and missing private kit. Images used here are
LOCALLY GENERATED synthetic JPEGs — never the real TRC-001 photographs.

The cryptographic OIDC verification itself is exercised by the real dependency's rejection
paths (missing / dev / app-local tokens -> 401). For the governance/intake behaviour the
verified-context dependency is overridden with a genuine OIDC-style AuthContext, so the
tests target the route logic rather than re-implementing a JWKS provider.
"""
from __future__ import annotations

import hashlib
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.auth.context import build_oidc_auth_context
from app.db.session import SessionLocal
from app.main import app
from app.models.governance_approval import GovernanceApproval
from app.models.retained_image import RetainedImage
from app.models.user_role_assignment import UserRoleAssignment
from app.routes import trc001_research as api

client = TestClient(app)

DATASET = "TRC-001-API-DS"
TENANT = "trc-api-tenant"
OTHER_TENANT = "trc-api-other"
OWNER = "owner-api@x"
OWNER_SUBJECT = "sub-owner-api-123"


def _jpeg(color=(10, 20, 30), size=(64, 48)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _ctx(*, actor=OWNER, role="technician", tenant_id=TENANT, subject=OWNER_SUBJECT):
    return build_oidc_auth_context(actor=actor, role=role, tenant_id=tenant_id,
                                   tenant_name="T", subject=subject, issuer="https://idp.local")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Server-side config + a synthetic kit; real DB session with cleanup."""
    from research.lens_vision.trc001_intake import TRC001_IMAGES
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    monkeypatch.setenv("TRC001_DATASET_ID", DATASET)
    # Build a synthetic runner-schema kit.
    images = []
    for image_id, spec in TRC001_IMAGES.items():
        data = _jpeg(color=(10, 20, 30) if "EXT" in image_id else (40, 50, 60))
        (tmp_path / f"{image_id}.jpg").write_bytes(data)
        images.append({"image_id": image_id, "filename": f"{image_id}.jpg",
                       "sha256": hashlib.sha256(data).hexdigest(), "content_type": "image/jpeg",
                       "width": 64, "height": 48, "modality": spec["modality"]})
    (tmp_path / "manifest.json").write_text(json.dumps({"instrument_id": "TRC-001", "images": images}))
    monkeypatch.setenv("TRC001_PRIVATE_KIT_DIR", str(tmp_path))
    kit_hashes = [i["sha256"] for i in images]

    s = SessionLocal()
    created = {"users": [], "approvals": [], "retained": []}
    try:
        yield {"s": s, "created": created, "kit_hashes": kit_hashes, "tmp_path": tmp_path}
    finally:
        app.dependency_overrides.pop(api.require_verified_oidc_context, None)
        for i in created["retained"]:
            s.query(RetainedImage).filter(RetainedImage.id == i).delete()
        for a in created["approvals"]:
            s.query(GovernanceApproval).filter(GovernanceApproval.id == a).delete()
        for u in created["users"]:
            s.query(UserRoleAssignment).filter(UserRoleAssignment.username == u).delete()
        s.commit()
        s.close()


def _seed_user(env, username=OWNER, role="technician"):
    s, created = env["s"], env["created"]
    if username not in created["users"]:
        s.add(UserRoleAssignment(username=username, role=role))
        s.commit()
        created["users"].append(username)


def _override(ctx):
    app.dependency_overrides[api.require_verified_oidc_context] = lambda: ctx


def _track_new_rows(env):
    """Record approval + retained rows created by the API for cleanup."""
    s, created = env["s"], env["created"]
    for row in s.query(GovernanceApproval).filter(
            GovernanceApproval.request_type == api.REQ_OWNER_ATTESTATION,
            GovernanceApproval.target_resource_id == DATASET).all():
        if row.id not in created["approvals"]:
            created["approvals"].append(row.id)
    for row in s.query(RetainedImage).filter(RetainedImage.source == "trc001_research_intake").all():
        if row.id not in created["retained"]:
            created["retained"].append(row.id)


def _attest(env, *, hashes=None, signing=True, ctx=None):
    body = {
        "ownership_asserted": True,
        "permissible_research_use": "independent nonclinical LumenAI research",
        "retention_authorized": True,
        "withdrawal_procedure": "owner emails governance to withdraw; records deleted",
        "image_sha256": hashes if hashes is not None else env["kit_hashes"],
        "owner_signing_acknowledged": signing,
    }
    _override(ctx or _ctx())
    r = client.post("/api/research/trc001/owner-attestation", json=body)
    _track_new_rows(env)
    return r


# ── requirement 1-2: authentication is mandatory and OIDC-only ───────────────

def test_missing_authentication_rejected():
    app.dependency_overrides.pop(api.require_verified_oidc_context, None)
    r = client.post("/api/research/trc001/intake")
    assert r.status_code == 401
    r2 = client.post("/api/research/trc001/owner-attestation", json={})
    assert r2.status_code in (401, 422)  # auth runs before/around body validation; never 200


def test_dev_or_app_local_token_rejected():
    # A development / application-local bearer token is NOT a verified OIDC token.
    app.dependency_overrides.pop(api.require_verified_oidc_context, None)
    r = client.post("/api/research/trc001/intake", headers={"Authorization": "Bearer dev-token"})
    assert r.status_code == 401


# ── requirement 3-4 + 7: attestation + happy-path intake ─────────────────────

def test_owner_attestation_and_intake_happy_path(env):
    _seed_user(env)
    r = _attest(env)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["basis"] == "owner_attested"
    assert body["independent_ownership_verified"] is False and body["institutional_approved"] is False

    _override(_ctx())
    ri = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert ri.status_code == 200, ri.text
    rep = ri.json()
    assert rep["status"] == "INGESTED" and rep["imported_count"] == 2
    assert rep["authorization_basis"] == "owner_attested"
    for img in rep["images"]:
        assert img["retained_image_id"] is not None and img["ingestion_successful"] is True
        assert img["ground_truth_status"] == "unknown" and img["baseline_review"] == "pending_review"
        assert img["research_training_eligible"] is False


def test_attestation_requires_explicit_signing_action(env):
    r = _attest(env, signing=False)
    assert r.status_code == 422


# ── requirement 8 negatives on the intake action ─────────────────────────────

def test_intake_absent_attestation_blocked(env):
    _seed_user(env)
    _override(_ctx())
    r = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert r.status_code == 200
    assert r.json()["status"] == "BLOCKED_AUTHORIZATION" and r.json()["imported_count"] == 0


def test_intake_hash_mismatch_blocked(env):
    _seed_user(env)
    _attest(env, hashes=["ab" * 32, "cd" * 32])  # not the kit's hashes
    _override(_ctx())
    r = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert r.json()["status"] == "BLOCKED_AUTHORIZATION" and r.json()["imported_count"] == 0


def test_intake_cross_tenant_blocked(env):
    # Attestation recorded under TENANT; intake attempted under OTHER_TENANT.
    _seed_user(env, username=OWNER)
    _seed_user(env, username=OWNER)  # same actor
    _attest(env, ctx=_ctx(tenant_id=TENANT))
    _override(_ctx(tenant_id=OTHER_TENANT))
    r = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert r.json()["status"] == "BLOCKED_AUTHORIZATION" and r.json()["imported_count"] == 0


def test_intake_mismatched_subject_blocked(env):
    _seed_user(env)
    _attest(env, ctx=_ctx(subject="sub-A"))          # attestation bound to subject sub-A
    _override(_ctx(subject="sub-B-different"))         # intake presents a different subject
    r = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert r.json()["status"] == "BLOCKED_AUTHORIZATION" and r.json()["imported_count"] == 0


def test_intake_after_withdrawal_blocked(env):
    _seed_user(env)
    _attest(env)
    _override(_ctx())
    assert client.post("/api/research/trc001/intake").json()["status"] == "INGESTED"
    _track_new_rows(env)
    # Withdraw, then intake must fail closed.
    _override(_ctx())
    w = client.post("/api/research/trc001/owner-attestation/withdraw")
    assert w.status_code == 200 and w.json()["status"] == "withdrawn"
    _override(_ctx())
    r = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert r.json()["status"] == "BLOCKED_AUTHORIZATION" and r.json()["imported_count"] == 0


def test_intake_missing_kit_configuration_blocked(env, monkeypatch):
    _seed_user(env)
    _attest(env)
    monkeypatch.delenv("TRC001_PRIVATE_KIT_DIR", raising=False)  # kit location not configured
    _override(_ctx())
    r = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert r.status_code == 409  # server refuses without a configured kit location


def test_client_cannot_supply_dataset_or_path(env):
    # The intake action accepts no dataset_id/kit_dir from the client body; extra fields are ignored.
    _seed_user(env)
    _attest(env)
    _override(_ctx())
    r = client.post("/api/research/trc001/intake",
                    json={"kit_dir": "/etc", "dataset_id": "attacker-ds", "tenant_id": OTHER_TENANT})
    _track_new_rows(env)
    assert r.status_code == 200 and r.json()["status"] == "INGESTED"  # server config used, not client input
