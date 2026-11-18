"""SEC-171-03 — shared migration lifecycle and research-endpoint deployment isolation.

Finding under test: PR #171 changes a table shared with production (``retained_images``)
and mounts research endpoints in the production application.

Properties asserted here:

* **Upgrade** preserves every pre-existing retained image (row and bytes) and infers no
  ownership for it.
* **Downgrade** never silently destroys research ownership provenance or authorization
  history while leaving the image bytes behind.
* **Database compatibility**: the migration converges a database whose columns were
  added by the application's own startup back-fill (how production actually receives
  schema changes) to the same shape as a database upgraded by Alembic.
* **Deployment isolation**: the research endpoints do nothing unless the deployment is
  explicitly designated a research environment, and importing the application does not
  load the research stack.

The Alembic tests run the REAL ``alembic`` command against a throwaway PostgreSQL schema
(the migration chain is PostgreSQL-only: an earlier, unrelated revision uses
``ALTER COLUMN ... TYPE``, which SQLite rejects). Synthetic bytes only.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from app.auth.context import build_oidc_auth_context
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.governance_approval import GovernanceApproval
from app.models.retained_image import RetainedImage
from app.routes import trc001_research as api
from fastapi.testclient import TestClient

client = TestClient(app)

BACKEND_DIR = Path(__file__).resolve().parents[1]
PRE_REVISION = "c3e7a9b14d20"          # immediately before the PR #171 migration
PROVENANCE_REVISION = "e8b2c6d49f10"   # the PR #171 migration
ASSOCIATION_REVISION = "f1a2b3c4d5e6"  # later per-owner association table (if present)
PROVENANCE_COLUMNS = ("research_dataset_id", "research_owner_subject", "research_attestation_id")
ENABLE_FLAG = "TRC001_RESEARCH_API_ENABLED"
TENANT = "sec171-03-tenant"

_IS_POSTGRES = engine.dialect.name == "postgresql"
requires_postgres = pytest.mark.skipif(
    not _IS_POSTGRES, reason="the Alembic chain is PostgreSQL-only")


# ── real Alembic against a throwaway PostgreSQL schema ────────────────────────

class _Scratch:
    """An isolated schema reached through ``search_path`` so the real migration chain
    can run without touching the suite's own tables."""

    def __init__(self) -> None:
        self.schema = f"sec171_{uuid.uuid4().hex[:12]}"
        with engine.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{self.schema}"'))
        base = engine.url.render_as_string(hide_password=False)
        joiner = "&" if "?" in base else "?"
        self.url = f"{base}{joiner}options=-csearch_path={self.schema}"
        self.engine = sa.create_engine(self.url)

    def alembic(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        executable = shutil.which("alembic")
        assert executable, "the alembic command is not installed"
        run_env = {**os.environ, "DATABASE_URL": self.url, **(env or {})}
        return subprocess.run(
            [executable, *args], cwd=BACKEND_DIR, env=run_env,
            capture_output=True, text=True, timeout=240, check=False)

    def upgrade(self, revision: str) -> None:
        result = self.alembic("upgrade", revision)
        assert result.returncode == 0, result.stderr[-2000:]

    def columns(self, table: str = "retained_images") -> dict:
        return {c["name"]: c for c in sa.inspect(self.engine).get_columns(table)}

    def has_revision(self, revision: str) -> bool:
        return revision in self.alembic("history").stdout

    def close(self) -> None:
        self.engine.dispose()
        with engine.begin() as conn:
            conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE'))


@pytest.fixture()
def scratch():
    db = _Scratch()
    try:
        yield db
    finally:
        db.close()


def _filler(column: dict):
    python_type = None
    try:
        python_type = column["type"].python_type
    except NotImplementedError:
        python_type = str
    if python_type is bool:
        return False
    if python_type in (int, float):
        return 0
    if python_type is bytes:
        return b""
    if python_type.__name__ in ("datetime", "date"):
        return sa.func.now()
    return ""


def _insert_image(conn, columns: dict, **values) -> int:
    """Insert a ``retained_images`` row valid for WHATEVER shape the table has at the
    current revision: every required column without a default gets a neutral filler."""
    row = {}
    for name, column in columns.items():
        if name == "id" or name in values:
            continue
        if not column.get("nullable", True) and column.get("default") is None:
            row[name] = _filler(column)
    row.update(values)
    names = ", ".join(row)
    placeholders = ", ".join(
        "now()" if not isinstance(v, (str, int, float, bool, bytes, type(None))) else f":{k}"
        for k, v in row.items())
    params = {k: v for k, v in row.items() if isinstance(v, (str, int, float, bool, bytes, type(None)))}
    return conn.execute(
        sa.text(f"INSERT INTO retained_images ({names}) VALUES ({placeholders}) RETURNING id"), params
    ).scalar_one()


def _image_state(conn) -> dict:
    rows = conn.execute(sa.text("SELECT id, tenant_id, sha256, image_bytes FROM retained_images")).all()
    return {r.id: (r.tenant_id, r.sha256, hashlib.sha256(bytes(r.image_bytes or b"")).hexdigest())
            for r in rows}


def _seed_historical_images(db: _Scratch, count: int = 3) -> dict:
    with db.engine.begin() as conn:
        columns = db.columns()
        for index in range(count):
            payload = f"synthetic-historical-image-{index}".encode()
            _insert_image(conn, columns, tenant_id=TENANT, source="inspection",
                          sha256=hashlib.sha256(payload).hexdigest(), image_bytes=payload)
        return _image_state(conn)


@requires_postgres
def test_upgrade_preserves_historical_images_and_infers_no_ownership(scratch):
    scratch.upgrade(PRE_REVISION)
    assert not set(PROVENANCE_COLUMNS) & set(scratch.columns())
    before = _seed_historical_images(scratch)

    scratch.upgrade("head")

    with scratch.engine.connect() as conn:
        assert _image_state(conn) == before, "an upgrade changed or lost historical images"
        inferred = conn.execute(sa.text(
            "SELECT count(*) FROM retained_images WHERE COALESCE(research_dataset_id, '') <> '' "
            "OR COALESCE(research_owner_subject, '') <> '' OR research_attestation_id IS NOT NULL"
        )).scalar_one()
    assert inferred == 0, "the upgrade inferred research ownership for historical images"


@requires_postgres
def test_round_trip_without_research_rows_is_lossless(scratch):
    scratch.upgrade(PRE_REVISION)
    before = _seed_historical_images(scratch)
    scratch.upgrade("head")

    down = scratch.alembic("downgrade", PRE_REVISION)
    assert down.returncode == 0, down.stderr[-2000:]
    with scratch.engine.connect() as conn:
        assert _image_state(conn) == before
    scratch.upgrade("head")
    with scratch.engine.connect() as conn:
        assert _image_state(conn) == before


@requires_postgres
def test_downgrade_never_strips_ownership_from_retained_research_bytes(scratch):
    """Dropping the provenance columns while a research row still holds bytes leaves
    bytes that no owner withdrawal can ever find or delete."""
    scratch.upgrade("head")
    payload = b"synthetic-research-image"
    with scratch.engine.begin() as conn:
        image_id = _insert_image(
            conn, scratch.columns(), tenant_id=TENANT, source="trc001_research_intake",
            sha256=hashlib.sha256(payload).hexdigest(), image_bytes=payload,
            research_dataset_id="SEC171-03-DATASET", research_owner_subject="sub-synthetic-owner")

    result = scratch.alembic("downgrade", PRE_REVISION)

    columns = scratch.columns()
    with scratch.engine.connect() as conn:
        bytes_remain = conn.execute(
            sa.text("SELECT count(*) FROM retained_images WHERE id = :i AND image_bytes IS NOT NULL"),
            {"i": image_id}).scalar_one() == 1
    provenance_intact = all(name in columns for name in PROVENANCE_COLUMNS)
    assert not (bytes_remain and not provenance_intact), (
        "the downgrade dropped research ownership provenance and left the image bytes in place")
    if provenance_intact:
        assert result.returncode != 0, "a refused downgrade must be reported as a failure"
        with scratch.engine.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT research_dataset_id, research_owner_subject FROM retained_images WHERE id = :i"
            ), {"i": image_id}).one()
        assert tuple(row) == ("SEC171-03-DATASET", "sub-synthetic-owner")


@requires_postgres
def test_downgrade_never_discards_authorization_history(scratch):
    """Withdrawn per-owner authorizations are the record of who was authorized and when.
    A downgrade must not silently drop them."""
    if not scratch.has_revision(ASSOCIATION_REVISION):
        pytest.skip("the per-owner association table is not part of this revision chain")
    scratch.upgrade("head")
    payload = b"synthetic-research-image-history"
    with scratch.engine.begin() as conn:
        image_id = _insert_image(
            conn, scratch.columns(), tenant_id=TENANT, source="trc001_research_intake",
            sha256=hashlib.sha256(payload).hexdigest(), image_bytes=payload)
        conn.execute(sa.text(
            "INSERT INTO research_image_authorizations (tenant_id, retained_image_id, "
            "research_dataset_id, owner_actor, owner_subject, status, withdrawn_at) "
            "VALUES (:t, :i, 'SEC171-03-DATASET', 'synthetic-owner@x', 'sub-synthetic-owner', "
            "'withdrawn', now())"), {"t": TENANT, "i": image_id})

    result = scratch.alembic("downgrade", PROVENANCE_REVISION)

    still_there = sa.inspect(scratch.engine).has_table("research_image_authorizations")
    assert still_there, "the downgrade silently dropped withdrawn-authorization history"
    assert result.returncode != 0, "a refused downgrade must be reported as a failure"


@requires_postgres
def test_upgrade_converges_a_database_backfilled_by_application_startup(scratch):
    """Production receives schema changes from the startup column back-fill, not from
    Alembic. Alembic must still be able to upgrade such a database, and must leave it in
    the same shape as a database it upgraded itself."""
    from app.db.column_migrator import ensure_columns

    scratch.upgrade(PRE_REVISION)
    before = _seed_historical_images(scratch)
    added = ensure_columns(scratch.engine, RetainedImage)       # what startup does
    assert set(PROVENANCE_COLUMNS) <= set(added)

    result = scratch.alembic("upgrade", "head")

    assert result.returncode == 0, (
        "Alembic cannot upgrade a database whose provenance columns were added by the "
        f"application's startup back-fill:\n{result.stderr[-1500:]}")
    columns = scratch.columns()
    for name in ("research_dataset_id", "research_owner_subject"):
        assert columns[name]["nullable"] is False, f"{name} is nullable after the upgrade"
    assert columns["research_attestation_id"]["nullable"] is True
    indexes = {i["name"] for i in sa.inspect(scratch.engine).get_indexes("retained_images")}
    assert "ix_retained_images_research_dataset_id" in indexes
    with scratch.engine.connect() as conn:
        assert _image_state(conn) == before
        nulls = conn.execute(sa.text(
            "SELECT count(*) FROM retained_images WHERE research_dataset_id IS NULL "
            "OR research_owner_subject IS NULL")).scalar_one()
    assert nulls == 0


def test_startup_backfill_preserves_historical_images_on_any_database():
    """The path production actually uses (create_all + column back-fill), exercised on a
    throwaway SQLite database shaped like a pre-PR ``retained_images`` table."""
    from app.db.column_migrator import ensure_columns

    scratch_engine = sa.create_engine("sqlite://")
    legacy_columns = [c.copy() for c in RetainedImage.__table__.columns
                      if c.name not in PROVENANCE_COLUMNS]
    legacy = sa.Table("retained_images", sa.MetaData(), *legacy_columns)
    legacy.create(scratch_engine)
    payload = b"synthetic-historical-image"
    digest = hashlib.sha256(payload).hexdigest()
    with scratch_engine.begin() as conn:
        conn.execute(legacy.insert().values(
            tenant_id=TENANT, sha256=digest, image_bytes=payload, source="inspection",
            deident_name="x", instrument_type="x", content_type="image/jpeg", size_bytes=len(payload),
            exif_stripped=True, consent_recorded=True, uploaded_by="x", label_status="unlabeled"))

    added = ensure_columns(scratch_engine, RetainedImage)

    assert set(PROVENANCE_COLUMNS) <= set(added)
    with scratch_engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT sha256, image_bytes, research_dataset_id, research_owner_subject, "
            "research_attestation_id FROM retained_images")).one()
    assert row.sha256 == digest and bytes(row.image_bytes) == payload
    assert (row.research_dataset_id or "") == "" and (row.research_owner_subject or "") == ""
    assert row.research_attestation_id is None


# ── research-endpoint deployment isolation ───────────────────────────────────

RESEARCH_REQUESTS = [
    ("post", "/api/research/trc001/owner-attestation", {
        "ownership_asserted": True, "permissible_research_use": "synthetic",
        "retention_authorized": True, "withdrawal_procedure": "synthetic",
        "image_sha256": ["a" * 64, "b" * 64], "owner_signing_acknowledged": True}),
    ("post", "/api/research/trc001/owner-attestation/withdraw", None),
    ("post", "/api/research/trc001/intake", None),
    ("get", "/api/research/trc001/retained-image/1", None),
]


@pytest.fixture()
def verified_owner(monkeypatch, tmp_path):
    """The strongest caller the API accepts — a verified OIDC owner — so a refusal can
    only come from the deployment gate, never from missing authentication."""
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    monkeypatch.setenv("TRC001_DATASET_ID", f"SEC171-03-{uuid.uuid4().hex[:8]}")
    monkeypatch.setenv("TRC001_PRIVATE_KIT_DIR", str(tmp_path))
    ctx = build_oidc_auth_context(
        actor="sec171-03-owner@x", role="technician", tenant_id=TENANT, tenant_name="T",
        subject="sub-sec171-03-owner", issuer="https://idp.local")
    app.dependency_overrides[api.require_verified_oidc_context] = lambda: ctx
    try:
        yield ctx
    finally:
        app.dependency_overrides.pop(api.require_verified_oidc_context, None)
        s = SessionLocal()
        s.query(GovernanceApproval).filter(GovernanceApproval.tenant_id == TENANT).delete(
            synchronize_session=False)
        s.commit()
        s.close()


def _research_side_effects() -> int:
    s = SessionLocal()
    try:
        return (
            s.query(GovernanceApproval).filter(GovernanceApproval.tenant_id == TENANT).count()
            + s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT).count())
    finally:
        s.close()


@pytest.mark.parametrize("flag_value", [None, "", "0", "false", "no", "off", "disabled", "production"])
def test_research_api_is_inert_unless_the_deployment_is_designated_research(
    verified_owner, monkeypatch, flag_value,
):
    if flag_value is None:
        monkeypatch.delenv(ENABLE_FLAG, raising=False)
    else:
        monkeypatch.setenv(ENABLE_FLAG, flag_value)

    for method, path, body in RESEARCH_REQUESTS:
        response = getattr(client, method)(path, **({"json": body} if body is not None else {}))
        if response.status_code == 404 and method == "get" and "retained-image" in path:
            routes = {getattr(r, "path", "") for r in app.routes}
            if not any("retained-image" in r for r in routes):
                continue  # this route does not exist on this revision
        assert response.status_code == 404, (
            f"{method.upper()} {path} answered {response.status_code} on a deployment that is "
            "not designated a research environment")
    assert _research_side_effects() == 0, "a disabled research API still wrote records"


def test_research_api_works_when_the_deployment_is_designated_research(verified_owner, monkeypatch):
    monkeypatch.setenv(ENABLE_FLAG, "1")
    method, path, body = RESEARCH_REQUESTS[0]
    response = getattr(client, method)(path, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["institutional_approved"] is False
    assert response.json()["independent_ownership_verified"] is False


def test_disabled_research_api_does_not_reveal_authentication_state(monkeypatch):
    """With the gate closed, an unauthenticated caller and a verified one get the same
    answer, so the endpoints' existence is not an oracle."""
    monkeypatch.delenv(ENABLE_FLAG, raising=False)
    app.dependency_overrides.pop(api.require_verified_oidc_context, None)
    response = client.post("/api/research/trc001/intake")
    assert response.status_code == 404


def test_importing_the_application_does_not_load_the_research_stack():
    code = (
        "import sys; import app.main; "
        "loaded = sorted(m for m in sys.modules if m == 'research' or m.startswith('research.')); "
        "print('LOADED=' + ','.join(loaded))"
    )
    env = {**os.environ, ENABLE_FLAG: ""}
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND_DIR, env=env,
        capture_output=True, text=True, timeout=240, check=False)
    assert result.returncode == 0, result.stderr[-1500:]
    marker = [line for line in result.stdout.splitlines() if line.startswith("LOADED=")]
    assert marker and marker[-1] == "LOADED=", f"research modules loaded at startup: {marker}"
