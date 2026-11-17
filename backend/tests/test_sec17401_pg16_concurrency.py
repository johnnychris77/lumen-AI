"""SEC-174-01 / P3: PostgreSQL 16 concurrency validation for the research-image
authorization gate (association + attestation), using real two-session transactions and
``pg_blocking_pids()`` for lock evidence rather than timing.

These tests REQUIRE PostgreSQL (row-level locks, ``FOR UPDATE`` waits, ``pg_blocking_pids``).
They skip on SQLite and run in the PostgreSQL 16 CI job. Concurrent ingestion-vs-withdrawal and
withdrawal-first-blocks-intake are already covered by the PR #172 suite
(``test_trc001_ingestion.py::test_sec17102_*``); this file focuses on the new per-owner
association/attestation decision under concurrency.

Synthetic image rows only; no real images, no fabricated governance (approvals are ordinary
rows created and mutated by the test, mirroring the real withdraw/revoke transitions).
"""
from __future__ import annotations

import threading
import time
import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.models.governance_approval import GovernanceApproval
from app.models.research_image_authorization import (
    STATUS_ACTIVE,
    ResearchImageAuthorization,
)
from app.models.retained_image import RetainedImage
from app.services.research_image_authorization_service import (
    RESEARCH_SOURCE,
    ResearchImageAccessError,
    authorize_image_access,
    delete_images_without_basis,
    image_has_active_authorization,
    upsert_active_authorization,
    withdraw_owner_authorizations,
)

pytestmark = pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="PostgreSQL 16 required for real transaction/locking evidence (pg_blocking_pids)",
)

DATASET = "SEC17401-PG-DS"


def _tenant() -> str:
    return f"sec17401pg-{uuid.uuid4().hex[:12]}"


def _seed_owner(s, *, tenant, subject, actor, dataset=DATASET, approved=True, image_id=None):
    """Seed (image +) approved attestation + ACTIVE association for one owner. Commits."""
    if image_id is None:
        img = RetainedImage(
            tenant_id=tenant, sha256=(uuid.uuid4().hex + uuid.uuid4().hex)[:64],
            source=RESEARCH_SOURCE, image_bytes=b"\x00\x01\x02\x03", content_type="image/jpeg",
            size_bytes=4, research_dataset_id=dataset, research_owner_subject=subject)
        s.add(img)
        s.flush()
        image_id = img.id
    appr = GovernanceApproval(
        tenant_id=tenant, tenant_name=tenant, request_type="research_owner_attestation",
        target_resource="research_dataset", target_resource_id=dataset, requested_by=actor,
        status="approved" if approved else "revoked", reviewed_by=actor)
    s.add(appr)
    s.flush()
    assoc = ResearchImageAuthorization(
        tenant_id=tenant, retained_image_id=image_id, research_dataset_id=dataset,
        owner_actor=actor, owner_subject=subject, attestation_id=appr.id, status=STATUS_ACTIVE)
    s.add(assoc)
    s.commit()
    return image_id, appr.id, assoc.id


def _cleanup(tenant):
    s = SessionLocal()
    try:
        s.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.tenant_id == tenant).delete(synchronize_session=False)
        s.query(RetainedImage).filter(RetainedImage.tenant_id == tenant).delete(synchronize_session=False)
        s.query(GovernanceApproval).filter(GovernanceApproval.tenant_id == tenant).delete(
            synchronize_session=False)
        s.commit()
    finally:
        s.close()


# ── Deterministic post-commit invariants (no stale decision) ─────────────────

def test_pg16_no_stale_authorization_after_committed_withdrawal():
    """After a withdrawal commits in one session, a FRESH authorization check in another
    session is denied — no stale ORM decision permits access post-withdrawal."""
    tenant = _tenant()
    s = SessionLocal()
    try:
        image_id, _, _ = _seed_owner(s, tenant=tenant, subject="sub-a", actor="a@x")
        # Baseline: authorized.
        authorize_image_access(s, tenant_id=tenant, owner_subject="sub-a", retained_image_id=image_id)

        a = SessionLocal()
        try:
            withdraw_owner_authorizations(
                a, tenant_id=tenant, research_dataset_id=DATASET, owner_actor="a@x", owner_subject="sub-a")
            a.commit()
        finally:
            a.close()

        b = SessionLocal()
        try:
            with pytest.raises(ResearchImageAccessError):
                authorize_image_access(b, tenant_id=tenant, owner_subject="sub-a", retained_image_id=image_id)
        finally:
            b.close()
    finally:
        s.close()
        _cleanup(tenant)


def test_pg16_revoked_attestation_denies_after_commit():
    """Revoking the attestation (status->revoked) in one session denies a fresh access check,
    even though the association row remains ACTIVE — attestation revalidation under real commit."""
    tenant = _tenant()
    s = SessionLocal()
    try:
        image_id, approval_id, _ = _seed_owner(s, tenant=tenant, subject="sub-a", actor="a@x")
        a = SessionLocal()
        try:
            appr = a.query(GovernanceApproval).filter(GovernanceApproval.id == approval_id).one()
            appr.status = "revoked"
            a.commit()
        finally:
            a.close()
        b = SessionLocal()
        try:
            with pytest.raises(ResearchImageAccessError):
                authorize_image_access(b, tenant_id=tenant, owner_subject="sub-a", retained_image_id=image_id)
            # Association row is still ACTIVE; only the attestation turned invalid.
            assert b.query(ResearchImageAuthorization).filter(
                ResearchImageAuthorization.retained_image_id == image_id,
                ResearchImageAuthorization.status == STATUS_ACTIVE).count() == 1
        finally:
            b.close()
    finally:
        s.close()
        _cleanup(tenant)


def test_pg16_shared_bytes_retained_while_other_owner_active():
    """Two owners share one image; one withdraws + runs deletion. Bytes are retained (other
    owner active), the remaining owner stays authorized, the withdrawn owner is denied."""
    tenant = _tenant()
    s = SessionLocal()
    try:
        image_id, _, _ = _seed_owner(s, tenant=tenant, subject="sub-a", actor="a@x")
        _seed_owner(s, tenant=tenant, subject="sub-b", actor="b@x", image_id=image_id)

        a = SessionLocal()
        try:
            affected = withdraw_owner_authorizations(
                a, tenant_id=tenant, research_dataset_id=DATASET, owner_actor="a@x", owner_subject="sub-a")
            result = delete_images_without_basis(
                a, affected, tenant_id=tenant, owner_subject="sub-a")
            a.commit()
        finally:
            a.close()
        assert image_id in result["retained"] and image_id not in result["deleted"]

        b = SessionLocal()
        try:
            assert b.query(RetainedImage).filter(RetainedImage.id == image_id).count() == 1
            assert image_has_active_authorization(b, image_id, tenant_id=tenant) is True
            authorize_image_access(b, tenant_id=tenant, owner_subject="sub-b", retained_image_id=image_id)
            with pytest.raises(ResearchImageAccessError):
                authorize_image_access(b, tenant_id=tenant, owner_subject="sub-a", retained_image_id=image_id)
        finally:
            b.close()
    finally:
        s.close()
        _cleanup(tenant)


# ── Real lock-contention evidence via pg_blocking_pids ───────────────────────

def test_pg16_withdraw_locks_association_blocks_concurrent_reactivation():
    """``withdraw_owner_authorizations`` holds a FOR UPDATE lock on the owner's association
    row; a concurrent ``upsert_active_authorization`` (reactivation) for the same row blocks on
    it (proved via pg_blocking_pids), then proceeds after commit to a consistent final state."""
    tenant = _tenant()
    s = SessionLocal()
    try:
        image_id, _, _ = _seed_owner(s, tenant=tenant, subject="sub-a", actor="a@x")
    finally:
        s.close()

    lock_held = threading.Event()
    release = threading.Event()
    reactivate_pid_ready = threading.Event()
    done = threading.Event()
    outcomes: dict = {}

    def withdrawer():
        a = SessionLocal()
        try:
            a.execute(text("SET lock_timeout = '12000ms'"))
            outcomes["withdraw_pid"] = a.execute(text("SELECT pg_backend_pid()")).scalar_one()
            withdraw_owner_authorizations(
                a, tenant_id=tenant, research_dataset_id=DATASET, owner_actor="a@x", owner_subject="sub-a")
            lock_held.set()  # FOR UPDATE on the association row now held until commit
            if not release.wait(timeout=15):
                raise TimeoutError("release not received")
            a.commit()
            outcomes["withdraw_committed"] = True
        except BaseException as exc:  # noqa: BLE001
            outcomes["withdraw_error"] = repr(exc)
            a.rollback()
        finally:
            a.close()

    def reactivator():
        b = SessionLocal()
        try:
            b.execute(text("SET lock_timeout = '12000ms'"))
            outcomes["reactivate_pid"] = b.execute(text("SELECT pg_backend_pid()")).scalar_one()
            reactivate_pid_ready.set()
            upsert_active_authorization(
                b, tenant_id=tenant, retained_image_id=image_id, research_dataset_id=DATASET,
                owner_actor="a@x", owner_subject="sub-a", attestation_id=None)
            b.commit()
            outcomes["reactivated"] = True
        except BaseException as exc:  # noqa: BLE001
            outcomes["reactivate_error"] = repr(exc)
            b.rollback()
        finally:
            b.close()
            done.set()

    tw = threading.Thread(target=withdrawer, daemon=True)
    tr = threading.Thread(target=reactivator, daemon=True)
    tw.start()
    try:
        assert lock_held.wait(timeout=15), outcomes
        tr.start()
        assert reactivate_pid_ready.wait(timeout=5), outcomes
        assert outcomes["withdraw_pid"] != outcomes["reactivate_pid"]
        observed = False
        deadline = time.monotonic() + 8
        with engine.connect() as observer:
            while time.monotonic() < deadline:
                blockers = observer.execute(
                    text("SELECT pg_blocking_pids(:pid)"),
                    {"pid": outcomes["reactivate_pid"]}).scalar_one()
                if outcomes["withdraw_pid"] in blockers:
                    observed = True
                    break
                if done.is_set():
                    break
                time.sleep(0.05)
        assert observed, f"reactivation was never blocked by the withdrawal lock: {outcomes}"
        assert not done.is_set(), outcomes
    finally:
        release.set()
        tw.join(timeout=20)
        tr.join(timeout=20)

    assert "withdraw_error" not in outcomes, outcomes
    assert "reactivate_error" not in outcomes, outcomes
    # Final state is consistent: exactly one association row, reactivated to ACTIVE by the
    # second writer (serialized after the committed withdrawal).
    v = SessionLocal()
    try:
        rows = v.query(ResearchImageAuthorization).filter(
            ResearchImageAuthorization.retained_image_id == image_id).all()
        assert len(rows) == 1
        assert rows[0].status == STATUS_ACTIVE
    finally:
        v.close()
        _cleanup(tenant)


def test_pg16_final_owner_delete_locks_retained_row():
    """Final-owner withdrawal's ``delete_images_without_basis`` holds a FOR UPDATE lock on the
    retained-image row; a concurrent ``SELECT ... FOR UPDATE`` on the same row blocks (proved via
    pg_blocking_pids), then observes the row deleted after the withdrawal commits."""
    tenant = _tenant()
    s = SessionLocal()
    try:
        image_id, _, _ = _seed_owner(s, tenant=tenant, subject="sub-a", actor="a@x")
    finally:
        s.close()

    lock_held = threading.Event()
    release = threading.Event()
    reader_pid_ready = threading.Event()
    done = threading.Event()
    outcomes: dict = {}

    def deleter():
        a = SessionLocal()
        try:
            a.execute(text("SET lock_timeout = '12000ms'"))
            outcomes["delete_pid"] = a.execute(text("SELECT pg_backend_pid()")).scalar_one()
            affected = withdraw_owner_authorizations(
                a, tenant_id=tenant, research_dataset_id=DATASET, owner_actor="a@x", owner_subject="sub-a")
            delete_images_without_basis(a, affected, tenant_id=tenant, owner_subject="sub-a")
            lock_held.set()  # FOR UPDATE on the retained row held until commit
            if not release.wait(timeout=15):
                raise TimeoutError("release not received")
            a.commit()
            outcomes["delete_committed"] = True
        except BaseException as exc:  # noqa: BLE001
            outcomes["delete_error"] = repr(exc)
            a.rollback()
        finally:
            a.close()

    def locking_reader():
        b = SessionLocal()
        try:
            b.execute(text("SET lock_timeout = '12000ms'"))
            outcomes["reader_pid"] = b.execute(text("SELECT pg_backend_pid()")).scalar_one()
            reader_pid_ready.set()
            # A concurrent consumer that takes a row lock must wait for the delete to commit.
            b.execute(
                text("SELECT id FROM retained_images WHERE id = :i FOR UPDATE"), {"i": image_id})
            outcomes["reader_rowcount_after"] = b.execute(
                text("SELECT COUNT(*) FROM retained_images WHERE id = :i"), {"i": image_id}).scalar_one()
            b.commit()
        except BaseException as exc:  # noqa: BLE001
            outcomes["reader_error"] = repr(exc)
            b.rollback()
        finally:
            b.close()
            done.set()

    td = threading.Thread(target=deleter, daemon=True)
    trd = threading.Thread(target=locking_reader, daemon=True)
    td.start()
    try:
        assert lock_held.wait(timeout=15), outcomes
        trd.start()
        assert reader_pid_ready.wait(timeout=5), outcomes
        observed = False
        deadline = time.monotonic() + 8
        with engine.connect() as observer:
            while time.monotonic() < deadline:
                blockers = observer.execute(
                    text("SELECT pg_blocking_pids(:pid)"),
                    {"pid": outcomes["reader_pid"]}).scalar_one()
                if outcomes["delete_pid"] in blockers:
                    observed = True
                    break
                if done.is_set():
                    break
                time.sleep(0.05)
        assert observed, f"concurrent row lock was never blocked by the delete: {outcomes}"
    finally:
        release.set()
        td.join(timeout=20)
        trd.join(timeout=20)

    assert "delete_error" not in outcomes, outcomes
    assert "reader_error" not in outcomes, outcomes
    # After the delete committed, the concurrent reader sees the row gone — no stale bytes.
    assert outcomes["reader_rowcount_after"] == 0, outcomes
    v = SessionLocal()
    try:
        assert v.query(RetainedImage).filter(RetainedImage.id == image_id).count() == 0
    finally:
        v.close()
        _cleanup(tenant)
