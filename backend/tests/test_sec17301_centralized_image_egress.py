"""SEC-173-01 regression suite: centralized, fail-closed authorization for every path
that can return (or internally consume) a retained research image's bytes.

Verifies the remediation of the cross-endpoint authorization weakness found in the
independent audit: research-intake bytes (``source == trc001_research_intake``) are
reachable ONLY through the OIDC owner-authorized research API, and are denied — fail
closed — through the generic tenant/role-scoped endpoints (ml images, dataset registry,
inspections, baseline comparison) that previously served or consumed them with only a
tenant check.

Synthetic images only. No real images, no fabricated governance records (attestations are
created through the real attest/intake flow; a "revoked" case flips an already-created
approval's status, it does not invent one).
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
from app.models.research_image_authorization import (
    STATUS_ACTIVE,
    ResearchImageAuthorization,
)
from app.models.retained_image import RetainedImage
from app.models.user_role_assignment import UserRoleAssignment
from app.routes import trc001_research as api
from app.services.research_image_authorization_service import (
    RESEARCH_SOURCE,
    ResearchImageAccessError,
    assert_image_bytes_readable,
    may_read_image_bytes,
)

client = TestClient(app)

TENANT = "sec17301-t"
TENANT_B = "sec17301-t2"
DATASET = "SEC17301-DS"

# Generic (non-OIDC) callers: app-local dev tokens, exactly as the ML/inspection surface
# authenticates in the existing suites. None of these is an OIDC owner-verified session.
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}


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


def _seed_retained(s, *, tenant, source, color=(7, 7, 7)) -> RetainedImage:
    """Seed a retained image with an explicit source (synthetic bytes)."""
    from app.services.image_retention_service import strip_exif
    stored, _ = strip_exif(_jpeg(color=color), "image/jpeg")
    img = RetainedImage(
        tenant_id=tenant, deident_name=f"seed-{source}", instrument_type="TRC-001",
        content_type="image/jpeg", size_bytes=len(stored),
        sha256=hashlib.sha256(stored).hexdigest(), exif_stripped=True,
        source=source, uploaded_by="seed@x", consent_recorded=True, image_bytes=stored)
    s.add(img)
    s.commit()
    return img


@pytest.fixture()
def envkit(tmp_path, monkeypatch):
    """Configure a synthetic TRC-001 kit and seed a technician; dependency-override the
    verified-OIDC dependency (the real signature path is covered elsewhere)."""
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


def _attest(envkit, ctx, *, hashes=None):
    _seed_user(envkit, ctx.actor)
    _override(ctx)
    return client.post("/api/research/trc001/owner-attestation", json={
        "ownership_asserted": True, "permissible_research_use": "research",
        "retention_authorized": True, "withdrawal_procedure": "email",
        "image_sha256": hashes if hashes is not None else envkit["hashes"],
        "owner_signing_acknowledged": True})


def _intake(envkit, ctx):
    _override(ctx)
    return client.post("/api/research/trc001/intake")


def _withdraw(envkit, ctx):
    _override(ctx)
    return client.post("/api/research/trc001/owner-attestation/withdraw")


def _ingest_owner(envkit, ctx) -> list[int]:
    assert _attest(envkit, ctx).status_code == 200
    rep = _intake(envkit, ctx).json()
    assert rep["status"] == "INGESTED", rep
    return sorted(i["retained_image_id"] for i in rep["images"])


def _research_get(ctx, image_id):
    _override(ctx)
    return client.get(f"/api/research/trc001/retained-image/{image_id}")


def _ml_bytes(image_id, *, tenant, headers=AUTH_OPERATOR):
    return client.get(f"/api/ml/images/{image_id}/bytes",
                      headers={**headers, "x-tenant-id": tenant})


# ── 1. Authorized research owner retrieves their image ───────────────────────

def test_authorized_owner_retrieves(envkit):
    a = _ctx(actor="a@x", subject="sub-a")
    ids = _ingest_owner(envkit, a)
    assert _research_get(a, ids[0]).status_code == 200


# ── 2. Same-tenant non-owner is denied (research 403 AND generic 404) ─────────

def test_same_tenant_non_owner_denied_everywhere(envkit):
    a = _ctx(actor="a@x", subject="sub-a")
    c = _ctx(actor="c@x", subject="sub-c")
    ids = _ingest_owner(envkit, a)
    _seed_user(envkit, c.actor)
    # Research API: present-but-unauthorized -> 403.
    assert _research_get(c, ids[0]).status_code == 403
    # Generic ML bytes endpoint (same tenant, operator role): the cross-endpoint bypass is
    # closed -> 404 (no existence leak), even though the row exists in this tenant.
    assert _ml_bytes(ids[0], tenant=TENANT).status_code == 404


# ── 3. Cross-tenant caller cannot retrieve bytes ─────────────────────────────

def test_cross_tenant_denied(envkit):
    a = _ctx(actor="a@x", subject="sub-a", tenant=TENANT)
    ids = _ingest_owner(envkit, a)
    bt = _ctx(actor="a@x", subject="sub-a", tenant=TENANT_B)
    assert _research_get(bt, ids[0]).status_code == 404       # no cross-tenant existence leak
    assert _ml_bytes(ids[0], tenant=TENANT_B).status_code == 404  # wrong tenant -> not found


# ── 4. Withdrawn owner cannot retrieve ───────────────────────────────────────

def test_withdrawn_owner_denied(envkit):
    a = _ctx(actor="a@x", subject="sub-a")
    ids = _ingest_owner(envkit, a)
    assert _withdraw(envkit, a).json()["status"] == "withdrawn"
    assert _research_get(a, ids[0]).status_code in (403, 404)  # row deleted (final owner) or unauthorized
    assert _ml_bytes(ids[0], tenant=TENANT).status_code == 404


# ── 5. Two owners with active associations can each retrieve shared bytes ─────

def test_two_owners_each_authorized(envkit):
    a = _ctx(actor="a@x", subject="sub-a")
    b = _ctx(actor="b@x", subject="sub-b")
    ids = _ingest_owner(envkit, a)
    assert sorted(_ingest_owner(envkit, b)) == ids  # same physical rows (dedup)
    assert _research_get(a, ids[0]).status_code == 200
    assert _research_get(b, ids[0]).status_code == 200
    # A third, non-owner tenant member is still denied through the generic endpoint.
    assert _ml_bytes(ids[0], tenant=TENANT).status_code == 404


# ── 6. Withdrawal of one owner does not affect the other ─────────────────────

def test_one_withdraws_other_unaffected(envkit):
    a = _ctx(actor="a@x", subject="sub-a")
    b = _ctx(actor="b@x", subject="sub-b")
    ids = _ingest_owner(envkit, a)
    _ingest_owner(envkit, b)
    _withdraw(envkit, a)
    assert _research_get(a, ids[0]).status_code == 403   # A revoked
    assert _research_get(b, ids[0]).status_code == 200   # B retained


# ── 7. Missing association fails closed ───────────────────────────────────────

def test_missing_association_fails_closed(envkit):
    s = envkit["s"]
    # A research-source row with NO association at all.
    img = _seed_retained(s, tenant=TENANT, source=RESEARCH_SOURCE, color=(3, 3, 3))
    a = _ctx(actor="a@x", subject="sub-a")
    assert _research_get(a, img.id).status_code == 403
    assert _ml_bytes(img.id, tenant=TENANT).status_code == 404


# ── 8. Revoked attestation fails closed (even while the association is active) ─

def test_revoked_attestation_fails_closed(envkit):
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    ids = _ingest_owner(envkit, a)
    assoc = (
        s.query(ResearchImageAuthorization)
        .filter(ResearchImageAuthorization.retained_image_id == ids[0],
                ResearchImageAuthorization.status == STATUS_ACTIVE)
        .first()
    )
    assert assoc is not None and assoc.attestation_id is not None
    # Authorized before revocation.
    assert _research_get(a, ids[0]).status_code == 200
    # Revoke the governance attestation WITHOUT touching the (still-active) association row.
    approval = s.query(GovernanceApproval).filter(GovernanceApproval.id == assoc.attestation_id).first()
    approval.status = "revoked"
    s.commit()
    # Fail-closed: access is denied once the attestation is no longer valid.
    assert _research_get(a, ids[0]).status_code == 403
    assert _ml_bytes(ids[0], tenant=TENANT).status_code == 404


# ── 9. Legacy research-source row without a valid association fails closed ─────

def test_legacy_research_row_without_association_fails_closed(envkit):
    s = envkit["s"]
    img = _seed_retained(s, tenant=TENANT, source=RESEARCH_SOURCE, color=(9, 1, 1))
    assert _ml_bytes(img.id, tenant=TENANT).status_code == 404
    assert _research_get(_ctx(actor="x@x", subject="sub-x"), img.id).status_code == 403


# ── 10. Non-research image behavior is unchanged (still served by the generic endpoint) ─

def test_non_research_image_unchanged(envkit):
    s = envkit["s"]
    img = _seed_retained(s, tenant=TENANT, source="ml_capture", color=(5, 6, 7))
    r = _ml_bytes(img.id, tenant=TENANT)
    assert r.status_code == 200
    assert r.content == img.image_bytes  # exact bytes served, as before


# ── 11. ML list endpoint excludes research-intake rows ───────────────────────

def test_ml_list_excludes_research(envkit):
    s = envkit["s"]
    research = _seed_retained(s, tenant=TENANT, source=RESEARCH_SOURCE, color=(2, 2, 2))
    normal = _seed_retained(s, tenant=TENANT, source="ml_capture", color=(4, 4, 4))
    r = client.get("/api/ml/images", headers={**AUTH_OPERATOR, "x-tenant-id": TENANT})
    assert r.status_code == 200
    returned_ids = {row["id"] for row in r.json()["images"]}
    assert normal.id in returned_ids
    assert research.id not in returned_ids


# ── 12. ML training-export manifest excludes research-intake rows ─────────────

def test_ml_export_excludes_research(envkit):
    s = envkit["s"]
    research = _seed_retained(s, tenant=TENANT, source=RESEARCH_SOURCE, color=(2, 3, 4))
    r = client.get("/api/ml/dataset/export?gold_only=false",
                   headers={**AUTH_ADMIN, "x-tenant-id": TENANT})
    assert r.status_code == 200
    export_ids = {rec["image_id"] for rec in r.json()["records"]}
    assert research.id not in export_ids


# ── 13. Centralized gate: dataset/inspection byte-load points deny research bytes ─

def test_service_gate_denies_research_for_non_oidc_callers(envkit):
    s = envkit["s"]
    research = _seed_retained(s, tenant=TENANT, source=RESEARCH_SOURCE, color=(1, 1, 9))
    normal = _seed_retained(s, tenant=TENANT, source="inspection", color=(9, 9, 1))
    # assess_quality / inspection report / training all call this gate with a non-OIDC actor.
    with pytest.raises(ResearchImageAccessError):
        assert_image_bytes_readable(s, research, tenant_id=TENANT,
                                    caller_subject="op@local.dev", caller_auth_provider="dev")
    assert may_read_image_bytes(s, research, tenant_id=TENANT,
                                caller_subject="op@local.dev", caller_auth_provider="dev") is False
    # Non-research bytes stay readable (behavior unchanged for normal images).
    assert may_read_image_bytes(s, normal, tenant_id=TENANT,
                                caller_subject="op@local.dev", caller_auth_provider="dev") is True


# ── 14. Centralized gate: OIDC owner with active+attested authorization is allowed; a
#        revoked attestation flips the decision to deny (attestation revalidation). ─────

def test_service_gate_owner_allowed_until_attestation_revoked(envkit):
    s = envkit["s"]
    a = _ctx(actor="a@x", subject="sub-a")
    ids = _ingest_owner(envkit, a)
    img = s.query(RetainedImage).filter(RetainedImage.id == ids[0]).first()
    assert may_read_image_bytes(s, img, tenant_id=TENANT,
                                caller_subject="sub-a", caller_auth_provider="oidc") is True
    assoc = (
        s.query(ResearchImageAuthorization)
        .filter(ResearchImageAuthorization.retained_image_id == ids[0],
                ResearchImageAuthorization.status == STATUS_ACTIVE)
        .first()
    )
    approval = s.query(GovernanceApproval).filter(GovernanceApproval.id == assoc.attestation_id).first()
    approval.status = "revoked"
    s.commit()
    assert may_read_image_bytes(s, img, tenant_id=TENANT,
                                caller_subject="sub-a", caller_auth_provider="oidc") is False


# ── 15. Dataset training eligibility: a research-source entry is never eligible ─

def test_eligible_entries_excludes_research_source(envkit):
    from app.models.dataset_governance import APPROVED, DatasetRegistryEntry
    from app.services.ml.dataset_builder import eligible_entries
    s = envkit["s"]
    research = _seed_retained(s, tenant=TENANT, source=RESEARCH_SOURCE, color=(6, 6, 6))
    version_id = 917301
    # An entry that satisfies EVERY ordinary eligibility flag, but points at research bytes.
    entry = DatasetRegistryEntry(
        tenant_id=TENANT, dataset_version_id=version_id, retained_image_id=research.id,
        review_status=APPROVED, training_eligibility=True, phi_verification="verified",
        image_quality="good", current_label="normal", image_sha256=research.sha256)
    s.add(entry)
    s.commit()
    try:
        eligible, excluded = eligible_entries(s, tenant_id=TENANT, dataset_version_id=version_id)
        assert all(e.retained_image_id != research.id for e in eligible)
        assert excluded.get("research_source_not_training_eligible", 0) >= 1
    finally:
        s.query(DatasetRegistryEntry).filter(
            DatasetRegistryEntry.dataset_version_id == version_id).delete(synchronize_session=False)
        s.commit()


# ── 16. Baseline comparison byte load refuses a research-source row ───────────

def test_baseline_loader_refuses_research_source(envkit):
    from app.models.baseline_image_library import BaselineImageLink
    from app.services.baseline_image_library_service import (
        ImageIdentityMismatchError,
        load_and_verify_baseline_bytes,
    )
    s = envkit["s"]
    research = _seed_retained(s, tenant=TENANT, source=RESEARCH_SOURCE, color=(8, 2, 2))
    link = BaselineImageLink(
        tenant_id=TENANT, baseline_library_entry_id=1, lcid_image_id=1,
        retained_image_id=research.id, image_sha256=research.sha256)
    s.add(link)
    s.commit()
    try:
        with pytest.raises(ImageIdentityMismatchError):
            load_and_verify_baseline_bytes(s, link=link, accessed_by="op@x")
    finally:
        s.query(BaselineImageLink).filter(BaselineImageLink.id == link.id).delete(
            synchronize_session=False)
        s.commit()
