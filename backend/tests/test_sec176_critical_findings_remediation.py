"""SEC-176 (P4.1): regression tests for the critical automated-review findings.

Each test reproduces a specific CONFIRMED finding and asserts the remediated behaviour.
All images are synthetic / rows are constructed in-session; no real research photographs,
no network, no real ingestion.

Findings covered:
  * Finding A  — unknown-ownership research rows must be PRESERVED on another owner's
                 withdrawal (never silently deleted), while still granting NO access.
  * Finding B  — the ``research_image_authorizations`` table must be registered at
                 application startup (before ``create_all``) so fresh deployments create it.
  * Finding C  — research-image retrieval must disclose the dataset scope the CALLER is
                 authorized for, not the image's stored provenance stamp.
  * Finding #7 — a verified-but-malformed OIDC token (e.g. missing tenant claim) must
                 fail closed as 401, never leak an unhandled 500.
  * Finding D  — (PG16-gated) the per-owner authorization row locks serialize a
                 concurrent withdrawal vs. re-attestation on PostgreSQL.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app.auth.context import build_oidc_auth_context
from app.auth.jwt_validator import JWTValidationError
from app.db.base import Base
from app.db.session import SessionLocal
from app.main import app
from app.models.governance_approval import GovernanceApproval
from app.models.research_image_authorization import (
    STATUS_ACTIVE,
    ResearchImageAuthorization,
)
from app.models.retained_image import RetainedImage
from app.routes import trc001_research as api
from app.services import research_image_authorization_service as svc

RESEARCH_SOURCE = svc.RESEARCH_SOURCE


def _unique_tenant() -> str:
    return f"sec176-{uuid.uuid4().hex[:12]}"


def _research_image(s, *, tenant_id: str, owner_subject: str, dataset_id: str = "",
                    source: str = RESEARCH_SOURCE) -> RetainedImage:
    img = RetainedImage(
        tenant_id=tenant_id, source=source, research_owner_subject=owner_subject,
        research_dataset_id=dataset_id, sha256=uuid.uuid4().hex * 2, content_type="image/jpeg",
        size_bytes=10, image_bytes=b"synthetic", label_status="unlabeled",
    )
    s.add(img)
    s.commit()
    return img


# ── Finding A: unknown-ownership research rows are preserved, not deleted ─────

def test_finding_a_unknown_ownership_row_is_preserved_on_withdrawal():
    """A research row with a BLANK ``research_owner_subject`` and no active association is
    PRESERVED (indeterminate ownership → fail-safe), not deleted, when another owner
    withdraws. It is still unreadable: there is no association granting access."""
    tenant = _unique_tenant()
    s = SessionLocal()
    try:
        img = _research_image(s, tenant_id=tenant, owner_subject="")  # unknown ownership
        result = svc.delete_images_without_basis(
            s, [img.id], tenant_id=tenant, owner_subject="some-withdrawing-owner")
        s.commit()
        assert result["retained"] == [img.id]
        assert result["deleted"] == []
        # Row survives…
        assert s.query(RetainedImage).filter(RetainedImage.id == img.id).first() is not None
        # …but remains unreadable: no active authorization exists for ANY subject.
        assert svc.image_has_active_authorization(s, img.id, tenant_id=tenant) is False
    finally:
        s.query(RetainedImage).filter(RetainedImage.tenant_id == tenant).delete(
            synchronize_session=False)
        s.commit()
        s.close()


def test_finding_a_own_known_owner_research_row_still_deletes():
    """Control: the fix does NOT over-preserve. A research row stamped with the withdrawing
    owner's OWN subject, with no active association and no other basis, still deletes —
    ensuring unknown-ownership preservation did not break normal reclamation."""
    tenant = _unique_tenant()
    subject = "sub-owner-known-123"
    s = SessionLocal()
    try:
        img = _research_image(s, tenant_id=tenant, owner_subject=subject)
        result = svc.delete_images_without_basis(
            s, [img.id], tenant_id=tenant, owner_subject=subject)
        s.commit()
        assert result["deleted"] == [img.id]
        assert result["retained"] == []
        assert s.query(RetainedImage).filter(RetainedImage.id == img.id).first() is None
    finally:
        s.query(RetainedImage).filter(RetainedImage.tenant_id == tenant).delete(
            synchronize_session=False)
        s.commit()
        s.close()


def test_finding_a_non_research_unknown_row_uses_independent_basis():
    """A non-research image with a blank owner subject is retained via its independent basis
    (source != research), NOT via the unknown-ownership rule — the two bases stay distinct."""
    tenant = _unique_tenant()
    s = SessionLocal()
    try:
        img = _research_image(s, tenant_id=tenant, owner_subject="", source="inspection")
        assert svc._has_unknown_ownership_provenance(img) is False
        assert svc._has_independent_basis(img) is True
        result = svc.delete_images_without_basis(
            s, [img.id], tenant_id=tenant, owner_subject="whoever")
        s.commit()
        assert result["retained"] == [img.id]
    finally:
        s.query(RetainedImage).filter(RetainedImage.tenant_id == tenant).delete(
            synchronize_session=False)
        s.commit()
        s.close()


# ── Finding B: association table registered at startup / created by create_all ─

def test_finding_b_table_registered_in_metadata_and_created_by_create_all(tmp_path):
    """The association model is registered in ``Base.metadata`` and a fresh ``create_all``
    (what the app does at startup) creates ``research_image_authorizations``."""
    assert "research_image_authorizations" in Base.metadata.tables
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    try:
        Base.metadata.create_all(bind=engine)
        tables = set(inspect(engine).get_table_names())
        assert "research_image_authorizations" in tables
    finally:
        engine.dispose()


def test_finding_b_startup_imports_model_before_create_all():
    """Source guard: ``app/main.py`` must import the association model during startup and
    BEFORE ``create_all`` so a fresh deployment creates the table (the original defect was
    the model being registered only in test conftest)."""
    main_src = Path(api.__file__).resolve().parent.parent / "main.py"
    text = main_src.read_text()
    import_marker = 'import_module("app.models.research_image_authorization")'
    create_all_call = "Base.metadata.create_all(bind=engine)"
    assert import_marker in text, "startup must register the research-authorization model"
    assert create_all_call in text, "startup must call Base.metadata.create_all(bind=engine)"
    assert text.index(import_marker) < text.index(create_all_call), (
        "model must be imported before create_all so the table is created at startup")


# ── Finding C: retrieval discloses caller's authorized dataset, not the stamp ─

def _seed_attested_authorization(s, *, tenant, image_id, subject, actor, dataset_id):
    approval = GovernanceApproval(
        tenant_id=tenant, tenant_name="T", request_type=api.REQ_OWNER_ATTESTATION,
        target_resource="dataset", target_resource_id=dataset_id, requested_by=actor,
        status="approved", reviewed_by=actor, requested_payload="{}")
    s.add(approval)
    s.commit()
    assoc = ResearchImageAuthorization(
        tenant_id=tenant, retained_image_id=image_id, research_dataset_id=dataset_id,
        owner_actor=actor, owner_subject=subject, attestation_id=approval.id,
        status=STATUS_ACTIVE)
    s.add(assoc)
    s.commit()
    return approval.id, assoc.id


def test_finding_c_retrieval_returns_caller_dataset_not_stamp():
    """The image carries a provenance STAMP of one dataset; the caller's active association
    authorizes a DIFFERENT dataset. Retrieval must disclose the caller's authorized dataset,
    never the stored stamp."""
    tenant = _unique_tenant()
    actor = "owner-c@x"
    subject = f"sub-{uuid.uuid4().hex[:10]}"
    stamp_ds = "STAMP-PROVENANCE-DS"
    caller_ds = "CALLER-AUTHORIZED-DS"
    s = SessionLocal()
    created_ids = {}
    try:
        img = _research_image(s, tenant_id=tenant, owner_subject=subject, dataset_id=stamp_ds)
        created_ids["image"] = img.id
        approval_id, _ = _seed_attested_authorization(
            s, tenant=tenant, image_id=img.id, subject=subject, actor=actor, dataset_id=caller_ds)
        created_ids["approval"] = approval_id

        ctx = build_oidc_auth_context(
            actor=actor, role="technician", tenant_id=tenant, tenant_name="T",
            subject=subject, issuer="https://idp.local")
        app.dependency_overrides[api.require_verified_oidc_context] = lambda: ctx
        client = TestClient(app)
        r = client.get(f"/api/research/trc001/retained-image/{img.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["research_dataset_id"] == caller_ds
        assert body["authorized_dataset_ids"] == [caller_ds]
        assert stamp_ds not in body["authorized_dataset_ids"]
        assert body["research_dataset_id"] != stamp_ds
    finally:
        app.dependency_overrides.pop(api.require_verified_oidc_context, None)
        s.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.tenant_id == tenant).delete(synchronize_session=False)
        s.query(RetainedImage).filter(RetainedImage.tenant_id == tenant).delete(
            synchronize_session=False)
        if "approval" in created_ids:
            s.query(GovernanceApproval).filter(
                GovernanceApproval.id == created_ids["approval"]).delete()
        s.commit()
        s.close()


def test_finding_c_helper_excludes_unattested_rows():
    """``authorized_dataset_ids_for_owner`` is fail-closed: an active association whose
    attestation is not approved contributes no dataset to the disclosed scope."""
    tenant = _unique_tenant()
    subject = f"sub-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    created = {}
    try:
        img = _research_image(s, tenant_id=tenant, owner_subject=subject, dataset_id="x")
        # pending (not approved) attestation → must not disclose its dataset
        pending = GovernanceApproval(
            tenant_id=tenant, tenant_name="T", request_type=api.REQ_OWNER_ATTESTATION,
            target_resource="dataset", target_resource_id="PENDING-DS", requested_by="o@x",
            status="pending", reviewed_by="o@x", requested_payload="{}")
        s.add(pending)
        s.commit()
        created["approval"] = pending.id
        s.add(ResearchImageAuthorization(
            tenant_id=tenant, retained_image_id=img.id, research_dataset_id="PENDING-DS",
            owner_actor="o@x", owner_subject=subject, attestation_id=pending.id,
            status=STATUS_ACTIVE))
        s.commit()
        datasets = svc.authorized_dataset_ids_for_owner(
            s, tenant_id=tenant, retained_image_id=img.id, owner_subject=subject)
        assert datasets == []
    finally:
        s.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.tenant_id == tenant).delete(synchronize_session=False)
        s.query(RetainedImage).filter(RetainedImage.tenant_id == tenant).delete(
            synchronize_session=False)
        if "approval" in created:
            s.query(GovernanceApproval).filter(
                GovernanceApproval.id == created["approval"]).delete()
        s.commit()
        s.close()


# ── Finding #7: verified-but-malformed OIDC token fails closed as 401 ─────────

def test_finding_7_malformed_claim_returns_401_not_500(monkeypatch):
    """A token that passes signature + issuer/audience validation but whose claim mapping
    raises ``JWTValidationError`` (e.g. missing tenant claim) must yield 401, not an
    unhandled 500. Server exceptions are surfaced (not re-raised) to observe the real code."""
    app.dependency_overrides.pop(api.require_verified_oidc_context, None)
    monkeypatch.setattr(api, "is_demo_mode", lambda: False)
    monkeypatch.setattr(api, "get_oidc_issuer", lambda: "https://idp.local")
    monkeypatch.setattr(api, "get_oidc_audience", lambda: "aud")
    monkeypatch.setattr(api, "validate_jwt_signature_with_jwks", lambda token: {"sub": "s"})
    monkeypatch.setattr(api, "validate_jwt_claims", lambda claims, **kw: claims)

    def _raise_missing_tenant(_validated):
        raise JWTValidationError("Missing required JWT tenant claim.")

    monkeypatch.setattr(api, "map_claims_to_auth_context_payload", _raise_missing_tenant)

    client = TestClient(app, raise_server_exceptions=False)
    r = client.post(
        "/api/research/trc001/intake", headers={"Authorization": "Bearer synthetic.jwt.token"})
    assert r.status_code == 401, r.text
    assert r.status_code != 500


# ── Finding D: PG16 row-lock serialization of withdrawal vs re-attestation ────

def test_finding_d_pg16_authorization_row_lock_serializes_withdrawal_vs_reattest(monkeypatch):
    """PG16-gated: ``withdraw_owner_authorizations`` and ``upsert_active_authorization`` both
    take ``with_for_update()`` on the owner's association row, so a concurrent re-attestation
    blocks on an in-progress withdrawal (proved via ``pg_blocking_pids``), never interleaving.
    Skips on SQLite (no row-lock semantics). Synthetic data only."""
    import threading
    import time

    from sqlalchemy import text

    from app.db.session import engine

    if engine.dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row-lock semantics")

    tenant = _unique_tenant()
    subject = f"sub-{uuid.uuid4().hex[:10]}"
    actor = "owner-d@x"
    dataset_id = f"TRC-001-D-{uuid.uuid4().hex[:8]}"
    setup = SessionLocal()
    try:
        img = _research_image(setup, tenant_id=tenant, owner_subject=subject, dataset_id=dataset_id)
        approval_id, _ = _seed_attested_authorization(
            setup, tenant=tenant, image_id=img.id, subject=subject, actor=actor,
            dataset_id=dataset_id)

        withdraw_locked = threading.Event()
        allow_withdraw_commit = threading.Event()
        reattest_pid_ready = threading.Event()
        outcomes: dict = {}

        def withdraw_first():
            session = SessionLocal()
            try:
                session.execute(text("SET lock_timeout = '12000ms'"))
                outcomes["withdraw_pid"] = session.execute(
                    text("SELECT pg_backend_pid()")).scalar_one()
                svc.withdraw_owner_authorizations(
                    session, tenant_id=tenant, research_dataset_id=dataset_id,
                    owner_actor=actor, owner_subject=subject)  # FOR UPDATE + flush
                withdraw_locked.set()
                if not allow_withdraw_commit.wait(timeout=15):
                    raise TimeoutError("withdraw commit release not received")
                session.commit()
                outcomes["withdraw_committed"] = True
            except BaseException as exc:  # noqa: BLE001
                outcomes["withdraw_error"] = repr(exc)
                session.rollback()
            finally:
                session.close()

        def reattest_second():
            session = SessionLocal()
            try:
                session.execute(text("SET lock_timeout = '12000ms'"))
                outcomes["reattest_pid"] = session.execute(
                    text("SELECT pg_backend_pid()")).scalar_one()
                reattest_pid_ready.set()
                svc.upsert_active_authorization(
                    session, tenant_id=tenant, retained_image_id=img.id,
                    research_dataset_id=dataset_id, owner_actor=actor, owner_subject=subject,
                    attestation_id=approval_id)  # contends for the same row FOR UPDATE
                session.commit()
                outcomes["reattest_done"] = True
            except BaseException as exc:  # noqa: BLE001
                outcomes["reattest_error"] = repr(exc)
                session.rollback()
            finally:
                session.close()

        t_withdraw = threading.Thread(target=withdraw_first, daemon=True)
        t_reattest = threading.Thread(target=reattest_second, daemon=True)
        t_withdraw.start()
        try:
            assert withdraw_locked.wait(timeout=10), outcomes
            t_reattest.start()
            assert reattest_pid_ready.wait(timeout=10), outcomes
            assert outcomes["reattest_pid"] != outcomes["withdraw_pid"]
            observed_blocker = False
            deadline = time.monotonic() + 8
            with engine.connect() as observer:
                while time.monotonic() < deadline:
                    blockers = observer.execute(
                        text("SELECT pg_blocking_pids(:pid)"),
                        {"pid": outcomes["reattest_pid"]}).scalar_one()
                    if outcomes["withdraw_pid"] in blockers:
                        observed_blocker = True
                        break
                    if "reattest_done" in outcomes or "reattest_error" in outcomes:
                        break
                    time.sleep(0.05)
            assert observed_blocker, f"re-attestation did not wait on the withdrawal lock: {outcomes}"
        finally:
            allow_withdraw_commit.set()
            t_withdraw.join(timeout=20)
            if t_reattest.ident is not None:
                t_reattest.join(timeout=20)

        assert outcomes.get("withdraw_committed") is True, outcomes
        assert "withdraw_error" not in outcomes, outcomes
        assert "reattest_error" not in outcomes, outcomes
    finally:
        setup.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.tenant_id == tenant).delete(synchronize_session=False)
        setup.query(RetainedImage).filter(RetainedImage.tenant_id == tenant).delete(
            synchronize_session=False)
        setup.query(GovernanceApproval).filter(
            GovernanceApproval.tenant_id == tenant).delete(synchronize_session=False)
        setup.commit()
        setup.close()
