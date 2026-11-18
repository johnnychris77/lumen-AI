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
        from app.models.research_image_authorization import ResearchImageAuthorization
        app.dependency_overrides.pop(api.require_verified_oidc_context, None)
        s.rollback()
        s.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.tenant_id.in_([TENANT, OTHER_TENANT])).delete(
            synchronize_session=False)
        s.query(RetainedImage).filter(
            RetainedImage.tenant_id.in_([TENANT, OTHER_TENANT])).delete(synchronize_session=False)
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


def _no_trc_rows(s):
    return s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0


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
        retained = env["s"].get(RetainedImage, img["retained_image_id"])
        assert retained.research_dataset_id == DATASET
        assert retained.research_owner_subject == OWNER_SUBJECT
        assert retained.uploaded_by == OWNER
        assert retained.research_attestation_id == body["attestation_id"]


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


def test_multiple_attestations_then_withdrawal_blocks_and_deletes(env):
    # Requirement 1-3: several approved attestations, one withdrawal revokes them all
    # (actor+subject-bound), intake returns BLOCKED_AUTHORIZATION and retains zero new
    # images, and the previously-retained images are deleted + deletion verified.
    s = env["s"]
    _seed_user(env)
    # Three approved attestations for the same actor+subject (all over the same hashes).
    for _ in range(3):
        assert _attest(env).status_code == 200
    approved_before = s.query(GovernanceApproval).filter(
        GovernanceApproval.request_type == api.REQ_OWNER_ATTESTATION,
        GovernanceApproval.target_resource_id == DATASET,
        GovernanceApproval.status == "approved").count()
    assert approved_before == 3

    # Ingest once (retains 2 images) while attestations are active.
    _override(_ctx())
    assert client.post("/api/research/trc001/intake").json()["status"] == "INGESTED"
    _track_new_rows(env)
    retained_before = s.query(RetainedImage).filter(
        RetainedImage.tenant_id == TENANT, RetainedImage.source == "trc001_research_intake").count()
    assert retained_before >= 2

    # Single withdrawal must revoke ALL approved attestations and delete retained images.
    _override(_ctx())
    w = client.post("/api/research/trc001/owner-attestation/withdraw").json()
    assert w["status"] == "withdrawn" and len(w["attestation_ids"]) == 3
    assert w["retained_images_deletion_verified"] is True and w["retained_images_remaining"] == 0

    s.expire_all()
    assert s.query(GovernanceApproval).filter(
        GovernanceApproval.request_type == api.REQ_OWNER_ATTESTATION,
        GovernanceApproval.target_resource_id == DATASET,
        GovernanceApproval.status == "approved").count() == 0
    assert _no_trc_rows(s)  # zero retained images remain

    # Intake now fails closed and retains zero new images.
    _override(_ctx())
    r = client.post("/api/research/trc001/intake")
    _track_new_rows(env)
    assert r.json()["status"] == "BLOCKED_AUTHORIZATION" and r.json()["imported_count"] == 0
    assert _no_trc_rows(s)


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


def test_attestation_is_atomic_with_audit(env, monkeypatch):
    # Requirement 6: if the audit write fails, the approved attestation must NOT persist.
    s = env["s"]

    def _boom(*a, **k):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(api, "record_enterprise_audit_event", _boom)
    before = s.query(GovernanceApproval).filter(
        GovernanceApproval.request_type == api.REQ_OWNER_ATTESTATION,
        GovernanceApproval.target_resource_id == DATASET).count()
    _override(_ctx())
    r = client.post("/api/research/trc001/owner-attestation", json={
        "ownership_asserted": True, "permissible_research_use": "x",
        "retention_authorized": True, "withdrawal_procedure": "y",
        "image_sha256": env["kit_hashes"], "owner_signing_acknowledged": True})
    assert r.status_code == 500
    s.expire_all()
    after = s.query(GovernanceApproval).filter(
        GovernanceApproval.request_type == api.REQ_OWNER_ATTESTATION,
        GovernanceApproval.target_resource_id == DATASET).count()
    assert after == before  # no approved record persisted without its audit evidence
    _track_new_rows(env)


def test_withdrawal_keeps_other_owners_datasets_subjects_and_legacy(env):
    """Synthetic foreign images in the same tenant must survive withdrawal."""
    s = env["s"]
    _seed_user(env)
    assert _attest(env).status_code == 200
    _override(_ctx())
    result = client.post("/api/research/trc001/intake").json()
    assert result["status"] == "INGESTED" and result["imported_count"] == 2
    owned_ids = {x["retained_image_id"] for x in result["images"]}
    _track_new_rows(env)

    others = [
        ("other-owner@x", "other-sub", DATASET, TENANT),
        (OWNER, OWNER_SUBJECT, "other-dataset", TENANT),
        (OWNER, "other-sub", DATASET, TENANT),
        (OWNER, OWNER_SUBJECT, DATASET, OTHER_TENANT),
        (OWNER, "", "", TENANT),
    ]
    foreign_ids = []
    for i, (actor, subject, dataset, tenant) in enumerate(others):
        payload = _jpeg(color=(100 + i, 120 + i, 140 + i))
        row = RetainedImage(
            tenant_id=tenant, deident_name=f"synthetic-other-{i}",
            instrument_type="TRC-001", content_type="image/jpeg",
            size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
            exif_stripped=True, source="trc001_research_intake",
            uploaded_by=actor, research_dataset_id=dataset,
            research_owner_subject=subject, consent_recorded=True,
            image_bytes=payload,
        )
        s.add(row)
        s.flush()
        foreign_ids.append(row.id)
    s.commit()
    _track_new_rows(env)

    _override(_ctx())
    response = client.post("/api/research/trc001/owner-attestation/withdraw")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["retained_images_deletion_verified"] is True
    assert set(result["retained_images_deleted"]) == owned_ids

    s.expire_all()
    assert s.query(RetainedImage).filter(RetainedImage.id.in_(owned_ids)).count() == 0
    assert s.query(RetainedImage).filter(RetainedImage.id.in_(foreign_ids)).count() == len(foreign_ids)
    assert client.post("/api/research/trc001/intake").json()["status"] == "BLOCKED_AUTHORIZATION"


def test_same_tenant_two_owners_share_bytes_without_reassignment(env):
    """SEC-171-04: a second owner attesting to identical bytes never reassigns the first
    owner's record, and withdrawing one owner never deletes the other owner's image.

    SEC-171-01 (PR #171 assessment): the foreign row here belongs to a DIFFERENT research
    dataset. A dataset is an authorization scope, so this owner's intake no longer attaches
    an authorization to that row (as this test previously asserted) — it stores its own row
    in its own dataset and leaves the foreign row completely untouched. Sharing one row
    between two verified owners of the SAME dataset is covered by
    tests/test_sec17104_image_authorization.py."""
    from app.models.research_image_authorization import (
        STATUS_ACTIVE,
        ResearchImageAuthorization,
    )
    from app.services.image_retention_service import strip_exif

    s = env["s"]
    original = (env["tmp_path"] / "TRC-001-EXT-001.jpg").read_bytes()
    stored, _ = strip_exif(original, "image/jpeg")
    foreign = RetainedImage(
        tenant_id=TENANT, deident_name="synthetic-foreign-same-bytes",
        instrument_type="TRC-001", content_type="image/jpeg",
        size_bytes=len(stored), sha256=hashlib.sha256(stored).hexdigest(),
        exif_stripped=True, source="trc001_research_intake",
        uploaded_by="foreign@x", research_dataset_id="foreign-dataset",
        research_owner_subject="foreign-subject", consent_recorded=True,
        image_bytes=stored,
    )
    s.add(foreign)
    s.commit()
    foreign_id = foreign.id
    _track_new_rows(env)

    _seed_user(env)
    assert _attest(env).status_code == 200
    _override(_ctx())
    response = client.post("/api/research/trc001/intake")
    assert response.status_code == 200
    outcome = response.json()
    # Both images ingest as this owner's OWN rows; the foreign dataset's row is not reused.
    assert outcome["status"] == "INGESTED" and outcome["imported_count"] == 2
    my_ids = [i["retained_image_id"] for i in outcome["images"]]
    assert foreign_id not in my_ids
    _track_new_rows(env)

    s.expire_all()
    # The foreign owner's record is untouched — no ownership transfer by matching hash.
    foreign = s.get(RetainedImage, foreign_id)
    assert foreign is not None
    assert foreign.uploaded_by == "foreign@x" and foreign.research_dataset_id == "foreign-dataset"
    assert foreign.research_owner_subject == "foreign-subject"
    # This owner holds NO authorization on the foreign dataset's row ...
    assert s.query(ResearchImageAuthorization).filter(
        ResearchImageAuthorization.retained_image_id == foreign_id).count() == 0
    # ... and an ACTIVE one on each of their own rows.
    for image_id in my_ids:
        my_assoc = s.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.tenant_id == TENANT,
            ResearchImageAuthorization.retained_image_id == image_id,
            ResearchImageAuthorization.owner_subject == OWNER_SUBJECT,
            ResearchImageAuthorization.status == STATUS_ACTIVE).first()
        assert my_assoc is not None and my_assoc.owner_actor == OWNER

    # Withdrawing this owner deletes only their own rows; the foreign image survives.
    _override(_ctx())
    withdrawal = client.post("/api/research/trc001/owner-attestation/withdraw")
    assert withdrawal.status_code == 200
    assert sorted(withdrawal.json()["retained_images_deleted"]) == sorted(my_ids)
    assert withdrawal.json()["retained_images_deletion_verified"] is True
    s.expire_all()
    assert s.get(RetainedImage, foreign_id) is not None
    for image_id in my_ids:
        assert s.get(RetainedImage, image_id) is None
