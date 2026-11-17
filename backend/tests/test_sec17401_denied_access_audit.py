"""SEC-174-01: durable, non-sensitive audit evidence for DENIED research-image access.

Every denial of research-image byte access must leave a durable audit record that survives the
request transaction (the request ends in an HTTP error, which must not roll the evidence away),
scoped correctly (tenant, actor, verified subject, resource id, decision, reason category) and
free of image bytes/tokens. Successful access is already audited; these tests focus on denials
and on the fail-closed behavior when the audit writer itself fails.

Synthetic images and synthetic identities only.
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
from app.models.audit_log import AuditLog
from app.models.governance_approval import GovernanceApproval
from app.models.research_image_authorization import (
    STATUS_ACTIVE,
    ResearchImageAuthorization,
)
from app.models.retained_image import RetainedImage
from app.models.user_role_assignment import UserRoleAssignment
from app.routes import trc001_research as api

client = TestClient(app)

TENANT = "sec17401-t"
TENANT_B = "sec17401-t2"
DATASET = "SEC17401-DS"
DENIED = "research_image_access_denied"
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}


def _jpeg(color=(10, 20, 30), size=(64, 48)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# File-unique actor emails: UserRoleAssignment.username is globally unique and shared across
# test files in the persistent test DB, so collisions with other suites are avoided here.
ACTOR_A = "sec17401-a@x"
ACTOR_B = "sec17401-b@x"
ACTOR_C = "sec17401-c@x"


def _ctx(*, actor, subject, tenant=TENANT, role="technician"):
    return build_oidc_auth_context(actor=actor, role=role, tenant_id=tenant, tenant_name="T",
                                   subject=subject, issuer="https://idp.local")


def _override(ctx):
    app.dependency_overrides[api.require_verified_oidc_context] = lambda: ctx


def _denied_audits(resource_id: int, *, tenant=TENANT) -> list[AuditLog]:
    """Query the audit log in a FRESH session — proving the event was durably committed and
    survived the denied request's transaction teardown."""
    s2 = SessionLocal()
    try:
        return (
            s2.query(AuditLog)
            .filter(AuditLog.action_type == DENIED,
                    AuditLog.resource_id == str(resource_id),
                    AuditLog.tenant_id == tenant)
            .all()
        )
    finally:
        s2.close()


@pytest.fixture()
def envkit(tmp_path, monkeypatch):
    from research.lens_vision.trc001_intake import TRC001_IMAGES
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
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
    monkeypatch.setenv("TRC001_DATASET_ID", DATASET)
    s = SessionLocal()
    seeded_users: list[str] = []
    # Shared persistent test DB: clear any leftovers from a previously aborted run first.
    for tn in (TENANT, TENANT_B):
        s.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.tenant_id == tn).delete(synchronize_session=False)
        s.query(RetainedImage).filter(RetainedImage.tenant_id == tn).delete(synchronize_session=False)
        s.query(GovernanceApproval).filter(GovernanceApproval.tenant_id == tn).delete(
            synchronize_session=False)
        # audit_logs is immutable by design (bulk UPDATE/DELETE blocked at the ORM layer),
        # so it is never purged here; per-resource_id queries isolate each test's events.
    for u in (ACTOR_A, ACTOR_B, ACTOR_C):
        s.query(UserRoleAssignment).filter(UserRoleAssignment.username == u).delete()
    s.commit()
    try:
        yield {"s": s, "hashes": hashes, "monkeypatch": monkeypatch, "users": seeded_users}
    finally:
        app.dependency_overrides.pop(api.require_verified_oidc_context, None)
        s.rollback()
        for tn in (TENANT, TENANT_B):
            s.query(ResearchImageAuthorization).filter(
                ResearchImageAuthorization.tenant_id == tn).delete(synchronize_session=False)
            s.query(RetainedImage).filter(RetainedImage.tenant_id == tn).delete(synchronize_session=False)
            s.query(GovernanceApproval).filter(GovernanceApproval.tenant_id == tn).delete(
                synchronize_session=False)
        for u in seeded_users:
            s.query(UserRoleAssignment).filter(UserRoleAssignment.username == u).delete()
        s.commit()
        s.close()


def _seed_user(envkit, username):
    s = envkit["s"]
    if s.query(UserRoleAssignment).filter(UserRoleAssignment.username == username).first() is None:
        s.add(UserRoleAssignment(username=username, role="technician"))
        s.commit()
    if username not in envkit["users"]:
        envkit["users"].append(username)


def _attest(envkit, ctx):
    _seed_user(envkit, ctx.actor)
    _override(ctx)
    return client.post("/api/research/trc001/owner-attestation", json={
        "ownership_asserted": True, "permissible_research_use": "research",
        "retention_authorized": True, "withdrawal_procedure": "email",
        "image_sha256": envkit["hashes"], "owner_signing_acknowledged": True})


def _intake(envkit, ctx):
    _override(ctx)
    return client.post("/api/research/trc001/intake")


def _withdraw(envkit, ctx):
    _override(ctx)
    return client.post("/api/research/trc001/owner-attestation/withdraw")


def _ingest(envkit, ctx) -> list[int]:
    assert _attest(envkit, ctx).status_code == 200
    rep = _intake(envkit, ctx).json()
    assert rep["status"] == "INGESTED", rep
    return sorted(i["retained_image_id"] for i in rep["images"])


def _research_get(ctx, image_id):
    _override(ctx)
    return client.get(f"/api/research/trc001/retained-image/{image_id}")


def _ml_bytes(image_id, *, tenant=TENANT):
    return client.get(f"/api/ml/images/{image_id}/bytes",
                      headers={**AUTH_OPERATOR, "x-tenant-id": tenant})


def _assert_clean_audit(rows, *, expect_reason=None, expect_subject=None):
    assert rows, "expected a durable denial audit event, found none"
    row = rows[-1]
    assert row.status == "denied"
    assert row.resource_type == "retained_image"
    blob = (row.details or "") + " " + (row.actor_email or "")
    low = blob.lower()
    # No sensitive content (property 10): never image bytes, bearer tokens, or raw JWTs.
    # NB: the legitimate reason category "no_active_attested_authorization" contains the word
    # "authorization", so we check for actual token/JWT/byte markers, not that substring.
    assert "eyj" not in low, "audit must not contain a JWT"
    assert "bearer " not in low, "audit must not contain a bearer token"
    assert "\xff\xd8" not in blob and "\x89png" not in low, "audit must not contain raw image bytes"
    assert len(row.details or "") < 2000, "audit details should be small structured fields, not a payload"
    details = json.loads(row.details) if row.details else {}
    # No image byte VALUE carried (the endpoint identifier may contain the words "image_bytes").
    assert "image_bytes" not in details, "audit details must not carry an image_bytes value"
    assert details.get("reason")
    if expect_reason:
        assert details.get("reason") == expect_reason
    if expect_subject is not None:
        assert details.get("subject") == expect_subject
    return row


# ── 1. Successful authorized retrieval is auditable (granted evidence exists) ─

def test_authorized_access_is_audited(envkit):
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    ids = _ingest(envkit, a)
    assert _research_get(a, ids[0]).status_code == 200
    s2 = SessionLocal()
    try:
        granted = (
            s2.query(AuditLog)
            .filter(AuditLog.resource_id == str(ids[0]), AuditLog.tenant_id == TENANT,
                    AuditLog.action_type == "trc001_research_image_access")
            .all()
        )
    finally:
        s2.close()
    assert granted, "authorized access must produce auditable evidence"


# ── 2. Same-tenant non-owner denial is durably audited ───────────────────────

def test_same_tenant_non_owner_denial_audited(envkit):
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    c = _ctx(actor=ACTOR_C, subject="sub-c")
    ids = _ingest(envkit, a)
    _seed_user(envkit, c.actor)
    assert _research_get(c, ids[0]).status_code == 403
    _assert_clean_audit(_denied_audits(ids[0]),
                        expect_reason="no_active_attested_authorization", expect_subject="sub-c")


# ── 3. Withdrawn-owner denial is audited ─────────────────────────────────────

def test_withdrawn_owner_denial_audited(envkit):
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    b = _ctx(actor=ACTOR_B, subject="sub-b")
    _ingest(envkit, a)
    ids = _ingest(envkit, b)  # two owners; B withdraws, A still active so the row survives
    _withdraw(envkit, b)
    assert _research_get(b, ids[0]).status_code == 403
    _assert_clean_audit(_denied_audits(ids[0]), expect_subject="sub-b")


# ── 4. Revoked-attestation denial is audited ─────────────────────────────────

def test_revoked_attestation_denial_audited(envkit):
    s = envkit["s"]
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    ids = _ingest(envkit, a)
    assoc = (
        s.query(ResearchImageAuthorization)
        .filter(ResearchImageAuthorization.retained_image_id == ids[0],
                ResearchImageAuthorization.status == STATUS_ACTIVE).first()
    )
    approval = s.query(GovernanceApproval).filter(GovernanceApproval.id == assoc.attestation_id).first()
    approval.status = "revoked"
    s.commit()
    assert _research_get(a, ids[0]).status_code == 403
    _assert_clean_audit(_denied_audits(ids[0]), expect_subject="sub-a")


# ── 5. Missing-association denial is audited ──────────────────────────────────

def test_missing_association_denial_audited(envkit):
    s = envkit["s"]
    from app.services.image_retention_service import strip_exif
    stored, _ = strip_exif(_jpeg(color=(3, 3, 3)), "image/jpeg")
    img = RetainedImage(tenant_id=TENANT, deident_name="noassoc", instrument_type="TRC-001",
                        content_type="image/jpeg", size_bytes=len(stored),
                        sha256=hashlib.sha256(stored).hexdigest(), exif_stripped=True,
                        source="trc001_research_intake", uploaded_by="x@x",
                        consent_recorded=True, image_bytes=stored)
    s.add(img)
    s.commit()
    assert _ml_bytes(img.id).status_code == 404
    _assert_clean_audit(_denied_audits(img.id), expect_reason="no_verified_owner_session")


# ── 6. Cross-tenant denial is audited but does not disclose existence ─────────

def test_cross_tenant_denial_audited_without_disclosure(envkit):
    a = _ctx(actor=ACTOR_A, subject="sub-a", tenant=TENANT)
    ids = _ingest(envkit, a)
    bt = _ctx(actor=ACTOR_A, subject="sub-a", tenant=TENANT_B)
    r = _research_get(bt, ids[0])
    assert r.status_code == 404  # no cross-tenant existence leak in the response
    # The denial is still audited under the CALLER's tenant (TENANT_B), reason cross_tenant.
    rows = _denied_audits(ids[0], tenant=TENANT_B)
    _assert_clean_audit(rows, expect_reason="cross_tenant_or_missing")


# ── 7. Audit database write failure is fail-closed (still denies, no 500) ─────

def test_audit_write_failure_fails_closed(envkit, monkeypatch):
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    c = _ctx(actor=ACTOR_C, subject="sub-c")
    ids = _ingest(envkit, a)
    _seed_user(envkit, c.actor)

    def _boom(*args, **kwargs):
        raise RuntimeError("audit backend unavailable")

    # Patch the single audit writer the helper calls lazily.
    monkeypatch.setattr("app.services.enterprise_audit_service.record_enterprise_audit_event", _boom)
    # Access is STILL denied (fail-closed); the request does not 500 on the audit failure.
    assert _ml_bytes(ids[0]).status_code == 404
    assert _research_get(c, ids[0]).status_code == 403


# ── 8. The denial audit survives the request's error path (durability) ───────

def test_denial_audit_survives_request_rollback(envkit):
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    c = _ctx(actor=ACTOR_C, subject="sub-c")
    ids = _ingest(envkit, a)
    _seed_user(envkit, c.actor)
    # The request ends in an HTTP error (403). A fresh session must still see the audit row,
    # proving it was committed and not rolled back with the request.
    assert _research_get(c, ids[0]).status_code == 403
    assert len(_denied_audits(ids[0])) >= 1


# ── 9. Repeated denied requests each produce evidence ────────────────────────

def test_repeated_denials_each_audited(envkit):
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    c = _ctx(actor=ACTOR_C, subject="sub-c")
    ids = _ingest(envkit, a)
    _seed_user(envkit, c.actor)
    for _ in range(3):
        assert _research_get(c, ids[0]).status_code == 403
    assert len(_denied_audits(ids[0])) >= 3


# ── 10. Audit records the actor/subject identity, never sensitive payloads ───

def test_denial_audit_identity_and_no_sensitive_payload(envkit):
    a = _ctx(actor=ACTOR_A, subject="sub-a")
    c = _ctx(actor=ACTOR_C, subject="sub-c")
    ids = _ingest(envkit, a)
    _seed_user(envkit, c.actor)
    assert _research_get(c, ids[0]).status_code == 403
    row = _assert_clean_audit(_denied_audits(ids[0]), expect_subject="sub-c")
    assert row.actor_email == ACTOR_C
    details = json.loads(row.details)
    assert details.get("endpoint") == "trc001_research.get_retained_research_image"
    # Decision and resource are recorded; no image bytes anywhere in the row.
    assert details.get("decision") == "denied"
    assert details.get("retained_image_id") == ids[0]
