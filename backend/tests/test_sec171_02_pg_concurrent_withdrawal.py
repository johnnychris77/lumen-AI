"""SEC-171-02 — concurrent owner-attestation withdrawal (deterministic PostgreSQL tests).

Finding under test: an intake that has already passed the owner-attestation
authorization check can persist image bytes after the owner withdraws, because the
check and the write are not in one protected transaction.

Property asserted here: once a withdrawal has committed, no image bytes scoped to the
withdrawn owner and dataset exist — whichever side reached the database first.

The race is driven without sleeps as timing assumptions. The intake is paused at an
exact point *after* authorization has passed, the withdrawal is started on a second
connection, and a third connection reads ``pg_blocking_pids`` to decide which of the
only two safe outcomes is unfolding:

* the withdrawal is blocked by the intake's row lock (it then runs after the intake
  commits and deletes what the intake wrote), or
* the withdrawal completes first (the intake must then be refused when it resumes).

Anything else — the withdrawal completing while the intake goes on to commit bytes —
is the vulnerability, and the final-state assertions fail.

PostgreSQL only: SQLite has neither row locks nor concurrent writers. Synthetic JPEGs
only; no TRC-001 operator photograph is read, loaded or committed.
"""
from __future__ import annotations

import hashlib
import io
import json
import threading
import time
import uuid

import pytest
from app.auth.context import build_oidc_auth_context
from app.db.session import SessionLocal, engine
from app.models.governance_approval import GovernanceApproval
from app.models.retained_image import RetainedImage
from app.models.user_role_assignment import UserRoleAssignment
from app.services.image_retention_service import strip_exif
from research.lens_vision import scientific_authorization as sa
from research.lens_vision import trc001_intake as intake_module
from research.lens_vision.trc001_intake import TRC001_IMAGES, run_trc001_intake
from sqlalchemy import text

TENANT = "sec171-02-tenant"
RESEARCH_SOURCE = "trc001_research_intake"
OWNER = "sec171-02-owner@x"
OWNER_SUBJECT = "sub-sec171-02-owner"
_KIT_SIZE = (64, 48)
_IS_POSTGRES = engine.dialect.name == "postgresql"

requires_postgres = pytest.mark.skipif(
    not _IS_POSTGRES, reason="requires PostgreSQL row locks and concurrent writers")


def _jpeg(color) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", _KIT_SIZE, color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _association_model():
    try:
        from app.models.research_image_authorization import ResearchImageAuthorization
    except ImportError:
        return None
    return ResearchImageAuthorization


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    monkeypatch.setenv("TRC001_RESEARCH_API_ENABLED", "1")
    dataset_id = f"SEC171-02-{uuid.uuid4().hex[:10]}"
    monkeypatch.setenv("TRC001_DATASET_ID", dataset_id)

    images, stored_hashes = [], []
    for index, (image_id, spec) in enumerate(TRC001_IMAGES.items()):
        seed = int(uuid.uuid4().hex[:4], 16)
        data = _jpeg(((seed + index * 41) % 256, (seed // 5) % 256, (seed // 11 + index) % 256))
        (tmp_path / f"{image_id}.jpg").write_bytes(data)
        images.append({"image_id": image_id, "filename": f"{image_id}.jpg",
                       "sha256": hashlib.sha256(data).hexdigest(), "content_type": "image/jpeg",
                       "width": _KIT_SIZE[0], "height": _KIT_SIZE[1], "modality": spec["modality"]})
        # What the retention service will actually store (EXIF-stripped re-encode).
        stored_hashes.append(hashlib.sha256(strip_exif(data, "image/jpeg")[0]).hexdigest())
    (tmp_path / "manifest.json").write_text(json.dumps({"instrument_id": "TRC-001", "images": images}))

    s = SessionLocal()
    if s.query(UserRoleAssignment).filter(UserRoleAssignment.username == OWNER).first() is None:
        s.add(UserRoleAssignment(username=OWNER, role="technician"))
        s.commit()
    payload = {
        "ownership_asserted": True,
        "permissible_research_use": "synthetic test fixture — no real asset",
        "retention_authorized": True,
        "withdrawal_procedure": "synthetic test fixture",
        "attestation_signed": True,
        "declarant_actor": OWNER,
        "declarant_subject": OWNER_SUBJECT,
        "independent_ownership_verified": False,
        "institutional_approved": False,
        "image_sha256": [i["sha256"] for i in images],
    }
    attestation = GovernanceApproval(
        tenant_id=TENANT, tenant_name="T", request_type=sa.REQ_OWNER_ATTESTATION,
        target_resource="dataset", target_resource_id=dataset_id, requested_by=OWNER,
        status="approved", reviewed_by=OWNER, requested_payload=json.dumps(payload))
    s.add(attestation)
    s.commit()
    ctx = {"s": s, "kit": str(tmp_path), "dataset_id": dataset_id,
           "attestation_id": attestation.id, "stored_hashes": stored_hashes}
    try:
        yield ctx
    finally:
        s.rollback()
        assoc = _association_model()
        if assoc is not None:
            s.query(assoc).filter(assoc.tenant_id == TENANT).delete(synchronize_session=False)
        s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT).delete(synchronize_session=False)
        s.query(GovernanceApproval).filter(GovernanceApproval.tenant_id == TENANT).delete(
            synchronize_session=False)
        s.query(UserRoleAssignment).filter(UserRoleAssignment.username == OWNER).delete()
        s.commit()
        s.close()


def _auth():
    return build_oidc_auth_context(actor=OWNER, role="technician", tenant_id=TENANT,
                                   tenant_name="T", subject=OWNER_SUBJECT, issuer="https://idp.local")


def _scoped_bytes_remaining(env) -> int:
    """Rows still holding the withdrawn owner's research bytes, read on a NEW connection
    with raw SQL so no ORM session state can mask a committed row."""
    with engine.connect() as conn:
        by_scope = conn.execute(
            text("SELECT count(*) FROM retained_images WHERE tenant_id = :t "
                 "AND research_dataset_id = :d AND image_bytes IS NOT NULL"),
            {"t": TENANT, "d": env["dataset_id"]}).scalar_one()
        by_hash = conn.execute(
            text("SELECT count(*) FROM retained_images WHERE tenant_id = :t AND source = :src "
                 "AND sha256 = ANY(:hashes) AND image_bytes IS NOT NULL"),
            {"t": TENANT, "src": RESEARCH_SOURCE, "hashes": env["stored_hashes"]}).scalar_one()
    return max(int(by_scope), int(by_hash))


def _attestation_status(env) -> str:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT status FROM governance_approvals WHERE id = :i"),
            {"i": env["attestation_id"]}).scalar_one()


def _dedicated_session():
    """A session pinned to ONE database connection for its whole life, so the backend
    pid observed in ``pg_blocking_pids`` is the pid that runs every statement (a pooled
    session may change connection after each commit)."""
    connection = engine.connect()
    connection.execute(text("SET lock_timeout = '20000ms'"))
    connection.commit()
    return connection, SessionLocal(bind=connection)


def _backend_pid(connection) -> int:
    pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
    connection.commit()
    return pid


def _race(env, monkeypatch, *, pause_on_decode_call: int) -> dict:
    """Pause the intake at the given ``_validate_decode`` call — a point that is always
    AFTER the owner-attestation authorization has passed — then run a withdrawal on a
    second connection and observe, from a third, how PostgreSQL orders the two.

    ``_validate_decode`` runs twice per image (before retention, and again on the
    stored bytes), so call 1 is "before any image is persisted" and call 3 is
    "between the first and second image"."""
    from app.routes.trc001_research import withdraw_owner_attestation

    auth = _auth()
    original_decode = intake_module._validate_decode
    calls = {"n": 0}
    at_hook, release = threading.Event(), threading.Event()
    withdrawal_done = threading.Event()
    out: dict = {}

    def paused_decode(data):
        calls["n"] += 1
        if calls["n"] == pause_on_decode_call:
            at_hook.set()
            if not release.wait(timeout=30):
                raise TimeoutError("test never released the paused intake")
        return original_decode(data)

    monkeypatch.setattr(intake_module, "_validate_decode", paused_decode)

    def intake():
        connection, session = _dedicated_session()
        try:
            out["intake_pid"] = _backend_pid(connection)
            out["intake"] = run_trc001_intake(
                session, kit_dir=env["kit"], tenant_id=TENANT, dataset_id=env["dataset_id"],
                auth=auth, authorization_basis="owner_attested")
        except BaseException as exc:  # noqa: BLE001 - surfaced through `out`
            out["intake_error"] = repr(exc)
        finally:
            session.rollback()
            session.close()
            connection.close()
            at_hook.set()

    def withdraw():
        connection, session = _dedicated_session()
        try:
            out["withdrawal_pid"] = _backend_pid(connection)
            out["withdrawal_pid_ready"] = True
            out["withdrawal"] = withdraw_owner_attestation(auth=auth, db=session)
        except BaseException as exc:  # noqa: BLE001 - surfaced through `out`
            out["withdrawal_error"] = repr(exc)
        finally:
            session.rollback()
            session.close()
            connection.close()
            withdrawal_done.set()

    t_intake = threading.Thread(target=intake, daemon=True)
    t_withdraw = threading.Thread(target=withdraw, daemon=True)
    t_intake.start()
    try:
        assert at_hook.wait(timeout=30), f"intake never reached the hook: {out}"
        assert "intake_error" not in out, out
        assert calls["n"] == pause_on_decode_call, (
            f"intake finished before decode call {pause_on_decode_call}: {out}")
        t_withdraw.start()

        # Decide the ordering from PostgreSQL's own lock graph, not from timing.
        blocked_by_intake = False
        deadline = time.monotonic() + 20
        with engine.connect() as observer:
            while time.monotonic() < deadline:
                if withdrawal_done.is_set():
                    break
                if out.get("withdrawal_pid_ready"):
                    blockers = observer.execute(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": out["withdrawal_pid"]}
                    ).scalar_one()
                    observer.commit()
                    if out["intake_pid"] in blockers:
                        blocked_by_intake = True
                        break
                time.sleep(0.02)
        out["withdrawal_blocked_by_intake"] = blocked_by_intake
        out["withdrawal_completed_first"] = withdrawal_done.is_set() and not blocked_by_intake
        assert blocked_by_intake or withdrawal_done.is_set(), (
            f"withdrawal neither completed nor blocked on the intake within the deadline: {out}")
    finally:
        release.set()
        t_intake.join(timeout=40)
        if t_withdraw.ident is not None:
            t_withdraw.join(timeout=40)

    assert not t_intake.is_alive() and not t_withdraw.is_alive(), out
    assert "intake_error" not in out, out
    assert "withdrawal_error" not in out, out
    return out


def _assert_withdrawal_was_not_bypassed(env, out: dict) -> None:
    # The withdrawal committed ...
    assert out["withdrawal"]["status"] == "withdrawn", out
    assert _attestation_status(env) == "withdrawn"
    # ... so no bytes scoped to the withdrawn owner + dataset may exist afterwards.
    remaining = _scoped_bytes_remaining(env)
    assert remaining == 0, (
        f"{remaining} image row(s) scoped to the withdrawn owner still hold bytes after the "
        f"withdrawal committed (withdrawal_completed_first={out['withdrawal_completed_first']}, "
        f"blocked_by_intake={out['withdrawal_blocked_by_intake']})")
    assert out["withdrawal"]["retained_images_deletion_verified"] is True, out
    # Only two orderings are safe. If the withdrawal completed first, every image the
    # intake handled after resuming must have been refused.
    if out["withdrawal_completed_first"]:
        resumed = [i for i in out["intake"].images if i.ingestion_attempted]
        persisted_after = [i for i in resumed if i.ingestion_successful]
        # Images committed BEFORE the pause are legitimately reported as ingested (they
        # were then deleted by the withdrawal); none may be committed after it.
        with engine.connect() as conn:
            for image in persisted_after:
                still_there = conn.execute(
                    text("SELECT count(*) FROM retained_images WHERE id = :i"),
                    {"i": image.retained_image_id}).scalar_one()
                assert still_there == 0, f"image {image.image_id} was committed after the withdrawal"


@requires_postgres
def test_withdrawal_before_any_image_is_persisted_cannot_be_bypassed(env, monkeypatch):
    """Authorization has passed; no image is persisted yet; the owner withdraws."""
    out = _race(env, monkeypatch, pause_on_decode_call=1)
    _assert_withdrawal_was_not_bypassed(env, out)


@requires_postgres
def test_withdrawal_between_the_two_images_cannot_be_bypassed(env, monkeypatch):
    """The first image is committed; the owner withdraws before the second is persisted."""
    out = _race(env, monkeypatch, pause_on_decode_call=3)
    _assert_withdrawal_was_not_bypassed(env, out)
    # The second image must not have been committed after the withdrawal.
    second = out["intake"].images[1]
    assert not (out["withdrawal_completed_first"] and second.ingestion_successful), second.to_dict()


@requires_postgres
def test_protection_is_a_database_lock_held_by_the_intake_transaction(env, monkeypatch):
    """Transactional protection, not best-effort ordering: while the intake holds an
    authorization it is about to act on, PostgreSQL itself must make the withdrawal wait."""
    from app.services import image_retention_service

    original_retain = image_retention_service.retain_image
    at_write, release = threading.Event(), threading.Event()
    out: dict = {}
    auth = _auth()

    def paused_retain(*args, **kwargs):
        at_write.set()
        if not release.wait(timeout=30):
            raise TimeoutError("test never released the paused intake")
        return original_retain(*args, **kwargs)

    monkeypatch.setattr(image_retention_service, "retain_image", paused_retain)

    def intake():
        connection, session = _dedicated_session()
        try:
            out["intake_pid"] = _backend_pid(connection)
            out["intake"] = run_trc001_intake(
                session, kit_dir=env["kit"], tenant_id=TENANT, dataset_id=env["dataset_id"],
                auth=auth, authorization_basis="owner_attested")
        except BaseException as exc:  # noqa: BLE001
            out["intake_error"] = repr(exc)
        finally:
            session.rollback()
            session.close()
            connection.close()
            at_write.set()

    thread = threading.Thread(target=intake, daemon=True)
    thread.start()
    try:
        assert at_write.wait(timeout=30), out
        assert "intake_error" not in out, out
        # A second connection tries to take the withdrawal's lock without waiting.
        with engine.connect() as probe:
            probe.execute(text("SET lock_timeout = '1ms'"))
            try:
                probe.execute(
                    text("SELECT id FROM governance_approvals WHERE id = :i FOR UPDATE NOWAIT"),
                    {"i": env["attestation_id"]})
                lock_was_free = True
            except Exception:  # noqa: BLE001 - lock_not_available is the expected outcome
                lock_was_free = False
            probe.rollback()
        assert not lock_was_free, (
            "the intake was about to write image bytes without holding a lock on the "
            "attestation it was authorized by; a withdrawal could commit underneath it")
    finally:
        release.set()
        thread.join(timeout=40)
    assert not thread.is_alive() and "intake_error" not in out, out


def test_sequential_withdrawal_leaves_no_scoped_bytes(env):
    """Control (all databases): ingest, withdraw, then verify absence on a new connection."""
    from app.routes.trc001_research import withdraw_owner_attestation

    report = run_trc001_intake(
        env["s"], kit_dir=env["kit"], tenant_id=TENANT, dataset_id=env["dataset_id"],
        auth=_auth(), authorization_basis="owner_attested")
    assert report.status == "INGESTED", report.to_dict()
    ids = [i.retained_image_id for i in report.images]

    result = withdraw_owner_attestation(auth=_auth(), db=env["s"])

    assert result["retained_images_deletion_verified"] is True
    with engine.connect() as conn:
        for image_id in ids:
            assert conn.execute(
                text("SELECT count(*) FROM retained_images WHERE id = :i"), {"i": image_id}
            ).scalar_one() == 0
        assert conn.execute(
            text("SELECT count(*) FROM retained_images WHERE tenant_id = :t AND source = :src"),
            {"t": TENANT, "src": RESEARCH_SOURCE}).scalar_one() == 0
    # A later intake under the withdrawn attestation is refused and retains nothing.
    again = run_trc001_intake(
        env["s"], kit_dir=env["kit"], tenant_id=TENANT, dataset_id=env["dataset_id"],
        auth=_auth(), authorization_basis="owner_attested")
    assert again.status == "BLOCKED_AUTHORIZATION", again.to_dict()
    assert all(i.retained_image_id is None for i in again.images)
