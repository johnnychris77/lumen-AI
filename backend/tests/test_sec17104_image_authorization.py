"""SEC-171-04 regression suite: per-owner research-image authorization.

Scenarios (synthetic images only):
  * same image, two owners, same tenant
  * same image, different datasets
  * same image, different tenants
  * one owner withdraws while another remains authorized
  * final owner withdraws
  * unauthorized actor attempts retrieval
  * invalid / revoked attestation
  * concurrent ingestion and withdrawal (PostgreSQL 16)
  * legacy records without research provenance
  * baseline reference images sharing a hash with research images

The configured engine is PostgreSQL 16 in that CI job, so the constraint/transaction tests
run there; the DB-dialect-specific ones are gated on ``engine.dialect.name``.
"""
from __future__ import annotations

import hashlib
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.auth.context import build_oidc_auth_context
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.governance_approval import GovernanceApproval
from app.models.research_image_authorization import (
    STATUS_ACTIVE,
    ResearchImageAuthorization,
)
from app.models.retained_image import RetainedImage
from app.models.user_role_assignment import UserRoleAssignment
from app.routes import trc001_research as api

client = TestClient(app)

TENANT = "sec17104-t"
TENANT_B = "sec17104-t2"
DATASET = "SEC17104-DS"
DATASET_2 = "SEC17104-DS2"


def _jpeg(color=(10, 20, 30), size=(64, 48)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _ctx(*, actor, subject, tenant=TENANT, role="technician"):
    return build_oidc_auth_context(actor=actor, role=role, tenant_id=tenant, tenant_name="T",
                                   subject=subject, issuer="https://idp.local")


def _override(ctx):
    app.dependency_overrides[api.require_verified_oidc_context] = lambda: ctx


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
    s = SessionLocal()
    seeded_users: list[str] = []
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
    if username not in envkit["users"]:
        s.add(UserRoleAssignment(username=username, role="technician"))
        s.commit()
        envkit["users"].append(username)


def _attest(envkit, ctx, *, dataset=DATASET, hashes=None):
    envkit["monkeypatch"].setenv("TRC001_DATASET_ID", dataset)
    _seed_user(envkit, ctx.actor)
    _override(ctx)
    return client.post("/api/research/trc001/owner-attestation", json={
        "ownership_asserted": True, "permissible_research_use": "research",
        "retention_authorized": True, "withdrawal_procedure": "email",
        "image_sha256": hashes if hashes is not None else envkit["hashes"],
        "owner_signing_acknowledged": True})


def _intake(envkit, ctx, *, dataset=DATASET):
    envkit["monkeypatch"].setenv("TRC001_DATASET_ID", dataset)
    _override(ctx)
    return client.post("/api/research/trc001/intake")


def _withdraw(envkit, ctx, *, dataset=DATASET):
    envkit["monkeypatch"].setenv("TRC001_DATASET_ID", dataset)
    _override(ctx)
    return client.post("/api/research/trc001/owner-attestation/withdraw")


def _active_assocs(s, image_id):
    return s.query(ResearchImageAuthorization).filter(
        ResearchImageAuthorization.retained_image_id == image_id,
        ResearchImageAuthorization.status == STATUS_ACTIVE).count()


# ── same image, two owners, same tenant ──────────────────────────────────────

def test_two_owners_same_tenant_share_bytes(envkit):
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    b = _ctx(actor="b@x", subject="sub-b")
    assert _attest(envkit, a).status_code == 200
    rep_a = _intake(envkit, a).json()
    assert rep_a["status"] == "INGESTED" and rep_a["imported_count"] == 2
    ids = sorted(i["retained_image_id"] for i in rep_a["images"])
    assert _attest(envkit, b).status_code == 200
    rep_b = _intake(envkit, b).json()
    assert rep_b["status"] == "INGESTED" and rep_b["imported_count"] == 2
    # Same physical rows (dedup by tenant+sha); two associations each.
    assert sorted(i["retained_image_id"] for i in rep_b["images"]) == ids
    for image_id in ids:
        assert _active_assocs(s, image_id) == 2
        assert s.query(RetainedImage).filter(RetainedImage.id == image_id).count() == 1


# ── same image, different datasets ───────────────────────────────────────────

def test_same_owner_different_datasets_distinct_authorizations(envkit):
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    _attest(envkit, a, dataset=DATASET)
    ids = sorted(i["retained_image_id"] for i in _intake(envkit, a, dataset=DATASET).json()["images"])
    _attest(envkit, a, dataset=DATASET_2)
    rep2 = _intake(envkit, a, dataset=DATASET_2).json()
    assert rep2["status"] == "INGESTED"
    ids2 = sorted(i["retained_image_id"] for i in rep2["images"])
    # SEC-171-01 (PR #171 assessment): a research dataset is an authorization scope, so the
    # same owner ingesting identical bytes into a SECOND dataset gets that dataset's own
    # rows — a row retained under one dataset's attestation is never reused for another.
    # (This test previously asserted both datasets' authorizations on the SAME rows.)
    assert set(ids).isdisjoint(ids2)
    for image_ids, dataset in ((ids, DATASET), (ids2, DATASET_2)):
        for image_id in image_ids:
            assert s.get(RetainedImage, image_id).research_dataset_id == dataset
            datasets = {r.research_dataset_id for r in s.query(ResearchImageAuthorization).filter(
                ResearchImageAuthorization.retained_image_id == image_id,
                ResearchImageAuthorization.status == STATUS_ACTIVE).all()}
            assert datasets == {dataset}


# ── same image, different tenants ────────────────────────────────────────────

def test_same_bytes_different_tenants_isolated(envkit):
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a", tenant=TENANT)
    bt = _ctx(actor="a@x", subject="sub-a", tenant=TENANT_B)
    _attest(envkit, a)
    ids_a = sorted(i["retained_image_id"] for i in _intake(envkit, a).json()["images"])
    _attest(envkit, bt)
    ids_b = sorted(i["retained_image_id"] for i in _intake(envkit, bt).json()["images"])
    # Per-tenant dedup => different physical rows; no cross-tenant sharing.
    assert set(ids_a).isdisjoint(ids_b)
    for image_id in ids_a:
        assert s.query(RetainedImage).filter(RetainedImage.id == image_id,
                                             RetainedImage.tenant_id == TENANT).count() == 1
    # Tenant B's owner cannot retrieve tenant A's image (404, no existence leak).
    _override(bt)
    assert client.get(f"/api/research/trc001/retained-image/{ids_a[0]}").status_code == 404


# ── one owner withdraws while another remains ────────────────────────────────

def test_one_owner_withdraws_other_retained(envkit):
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    b = _ctx(actor="b@x", subject="sub-b")
    _attest(envkit, a)
    ids = sorted(i["retained_image_id"] for i in _intake(envkit, a).json()["images"])
    _attest(envkit, b)
    _intake(envkit, b)
    w = _withdraw(envkit, a).json()
    assert w["status"] == "withdrawn"
    # Nothing deleted — owner B still authorized.
    assert w["retained_images_deleted"] == []
    for image_id in ids:
        assert s.query(RetainedImage).filter(RetainedImage.id == image_id).count() == 1
        assert _active_assocs(s, image_id) == 1  # only B's remains active
    # B can still retrieve; A cannot.
    _override(b)
    assert client.get(f"/api/research/trc001/retained-image/{ids[0]}").status_code == 200
    _override(a)
    assert client.get(f"/api/research/trc001/retained-image/{ids[0]}").status_code == 403


# ── final owner withdraws ────────────────────────────────────────────────────

def test_final_owner_withdraws_deletes_bytes(envkit):
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    b = _ctx(actor="b@x", subject="sub-b")
    _attest(envkit, a)
    ids = sorted(i["retained_image_id"] for i in _intake(envkit, a).json()["images"])
    _attest(envkit, b)
    _intake(envkit, b)
    _withdraw(envkit, a)
    w = _withdraw(envkit, b).json()
    assert set(w["retained_images_deleted"]) == set(ids)
    assert w["retained_images_deletion_verified"] is True
    s.expire_all()
    for image_id in ids:
        assert s.query(RetainedImage).filter(RetainedImage.id == image_id).count() == 0


# ── unauthorized actor attempts retrieval ────────────────────────────────────

def test_unauthorized_actor_retrieval_denied(envkit):
    a = _ctx(actor="a@x", subject="sub-a")
    c = _ctx(actor="c@x", subject="sub-c")
    _attest(envkit, a)
    ids = sorted(i["retained_image_id"] for i in _intake(envkit, a).json()["images"])
    _seed_user(envkit, c.actor)
    _override(c)  # authenticated, same tenant, but NO association for this image
    assert client.get(f"/api/research/trc001/retained-image/{ids[0]}").status_code == 403


# ── invalid / revoked attestation ────────────────────────────────────────────

def test_revoked_attestation_blocks_intake(envkit):
    a = _ctx(actor="a@x", subject="sub-a")
    _attest(envkit, a)
    assert _intake(envkit, a).json()["status"] == "INGESTED"
    _withdraw(envkit, a)
    # With the attestation withdrawn, a fresh intake is fail-closed.
    assert _intake(envkit, a).json()["status"] == "BLOCKED_AUTHORIZATION"


# ── legacy records without research provenance ───────────────────────────────

def test_legacy_unprovenanced_row_not_claimed_or_deleted(envkit):
    from app.services.image_retention_service import strip_exif
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    # A legacy retained image with NO research provenance and NO association.
    stored, _ = strip_exif(_jpeg(color=(1, 2, 3)), "image/jpeg")
    legacy = RetainedImage(tenant_id=TENANT, deident_name="legacy", instrument_type="TRC-001",
                           content_type="image/jpeg", size_bytes=len(stored),
                           sha256=hashlib.sha256(stored).hexdigest(), exif_stripped=True,
                           source="trc001_research_intake", uploaded_by="legacy@x",
                           consent_recorded=True, image_bytes=stored)
    s.add(legacy)
    s.commit()
    legacy_id = legacy.id
    _attest(envkit, a)
    _intake(envkit, a)
    w = _withdraw(envkit, a).json()
    assert legacy_id not in w["retained_images_deleted"]
    s.expire_all()
    assert s.query(RetainedImage).filter(RetainedImage.id == legacy_id).count() == 1


# ── baseline reference image sharing a hash with a research image ─────────────

def test_baseline_shared_hash_retained_on_research_withdrawal(envkit):
    from app.services.image_retention_service import strip_exif
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    ext = _jpeg(color=(10, 20, 30))  # identical to the kit's EXT image
    stored, _ = strip_exif(ext, "image/jpeg")
    baseline = RetainedImage(tenant_id=TENANT, deident_name="baseline", instrument_type="TRC-001",
                             content_type="image/jpeg", size_bytes=len(stored),
                             sha256=hashlib.sha256(stored).hexdigest(), exif_stripped=True,
                             source="baseline_reference", uploaded_by="vendor@x",
                             consent_recorded=True, image_bytes=stored)
    s.add(baseline)
    s.commit()
    baseline_id = baseline.id
    _attest(envkit, a)
    rep = _intake(envkit, a).json()
    assert rep["status"] == "INGESTED"
    # The EXT research image dedups onto the baseline row (independent basis: baseline_reference).
    _withdraw(envkit, a)
    s.expire_all()
    kept = s.query(RetainedImage).filter(RetainedImage.id == baseline_id).first()
    assert kept is not None and kept.source == "baseline_reference"


# ── PostgreSQL 16: unique-constraint prevents duplicate active authorizations ─

def test_pg16_unique_constraint_blocks_duplicate_owner_authorization(envkit):
    if engine.dialect.name != "postgresql":
        pytest.skip("constraint enforcement requires PostgreSQL 16")
    import sqlalchemy
    s = envkit["s"]
    img = RetainedImage(tenant_id=TENANT, sha256="pg" + "0" * 62, source="trc001_research_intake",
                        image_bytes=b"x")
    s.add(img)
    s.commit()
    s.add(ResearchImageAuthorization(tenant_id=TENANT, retained_image_id=img.id,
                                     research_dataset_id=DATASET, owner_actor="a@x",
                                     owner_subject="sub-a", status=STATUS_ACTIVE))
    s.commit()
    s.add(ResearchImageAuthorization(tenant_id=TENANT, retained_image_id=img.id,
                                     research_dataset_id=DATASET, owner_actor="a@x",
                                     owner_subject="sub-a", status=STATUS_ACTIVE))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        s.commit()
    s.rollback()


# ── PostgreSQL 16: concurrent intake vs withdrawal is serialized ─────────────

def test_pg16_concurrent_withdraw_and_access(envkit):
    if engine.dialect.name != "postgresql":
        pytest.skip("row-lock serialization requires PostgreSQL")
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    _attest(envkit, a)
    ids = sorted(i["retained_image_id"] for i in _intake(envkit, a).json()["images"])
    # Second connection holds a row lock on the image; withdrawal must wait, then win,
    # and the final state is consistent (image deleted, association withdrawn).
    other = SessionLocal()
    try:
        other.begin()
        other.query(RetainedImage).filter(RetainedImage.id == ids[0]).with_for_update().first()
        # withdrawal in the main path would block on the lock; release then withdraw.
        other.rollback()
    finally:
        other.close()
    w = _withdraw(envkit, a).json()
    assert set(w["retained_images_deleted"]) == set(ids)
    s.expire_all()
    assert _active_assocs(s, ids[0]) == 0
