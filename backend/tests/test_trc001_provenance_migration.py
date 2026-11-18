"""SEC-171-03: migration-guard regression tests (upgrade/downgrade/existing/missing-table).

The alembic migration modules import the ``op`` proxy and are not importable under the test
cwd (the local ``alembic/`` dir shadows the library), so the hardening LOGIC lives in
``app.db.migration_guards`` and is tested here directly against real database connections.
Deterministic cases use throwaway engines; schema-shape + association cases also run against
the configured engine, which is PostgreSQL 16 in that CI job.
"""
from __future__ import annotations

import sqlalchemy as sa

import pytest

from app.db.migration_guards import (
    MigrationSchemaError,
    assert_association_downgrade_allowed,
    assert_retained_downgrade_allowed,
    require_table,
    retained_has_research_provenance,
    verify_retained_provenance_columns,
)

REV = "e8b2c6d49f10"


def _retained_table(md: sa.MetaData, *, with_provenance: bool) -> sa.Table:
    cols = [
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.String(100)),
        sa.Column("sha256", sa.String(64)),
    ]
    if with_provenance:
        cols += [
            sa.Column("research_dataset_id", sa.String(255), nullable=False, server_default=""),
            sa.Column("research_owner_subject", sa.String(255), nullable=False, server_default=""),
            sa.Column("research_attestation_id", sa.Integer, nullable=True),
        ]
    return sa.Table("retained_images", md, *cols)


def _engine_with(*, table: bool, with_provenance: bool = True, index: bool = True):
    eng = sa.create_engine("sqlite://")
    if table:
        md = sa.MetaData()
        tbl = _retained_table(md, with_provenance=with_provenance)
        if with_provenance and index:
            sa.Index("ix_retained_images_research_dataset_id", tbl.c.research_dataset_id)
        md.create_all(eng)
    return eng


# ── missing-table failure (requirements 1-2) ─────────────────────────────────

def test_require_table_raises_when_missing():
    eng = _engine_with(table=False)
    with eng.connect() as conn, pytest.raises(MigrationSchemaError):
        require_table(conn, "retained_images", revision=REV)


def test_require_table_passes_when_present():
    eng = _engine_with(table=True)
    with eng.connect() as conn:
        require_table(conn, "retained_images", revision=REV)  # no raise


# ── post-condition verification (requirements 4-5) ───────────────────────────

def test_verify_columns_raises_when_missing():
    eng = _engine_with(table=True, with_provenance=False)
    with eng.connect() as conn, pytest.raises(MigrationSchemaError):
        verify_retained_provenance_columns(conn, revision=REV)


def test_verify_columns_passes_with_full_schema():
    eng = _engine_with(table=True, with_provenance=True, index=True)
    with eng.connect() as conn:
        verify_retained_provenance_columns(conn, revision=REV)  # no raise


def test_verify_columns_raises_when_index_missing():
    eng = _engine_with(table=True, with_provenance=True, index=False)
    with eng.connect() as conn, pytest.raises(MigrationSchemaError):
        verify_retained_provenance_columns(conn, revision=REV)


# ── downgrade data-loss protection + existing records (requirements 3, 6) ─────

def test_downgrade_refused_when_provenance_present_and_data_preserved():
    eng = _engine_with(table=True, with_provenance=True)
    with eng.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO retained_images (tenant_id, sha256, research_dataset_id, "
            "research_owner_subject) VALUES ('t','h','TRC-001','sub-1')"))
        conn.execute(sa.text(
            "INSERT INTO retained_images (tenant_id, sha256, research_dataset_id, "
            "research_owner_subject) VALUES ('t','h2','','')"))
    with eng.connect() as conn:
        assert retained_has_research_provenance(conn) is True
        with pytest.raises(MigrationSchemaError):
            assert_retained_downgrade_allowed(conn, revision=REV)
    # Existing rows are untouched by the (read-only) guard.
    with eng.connect() as conn:
        assert conn.execute(sa.text("SELECT COUNT(*) FROM retained_images")).scalar() == 2


def test_downgrade_allowed_with_override(monkeypatch):
    eng = _engine_with(table=True, with_provenance=True)
    with eng.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO retained_images (tenant_id, sha256, research_dataset_id, "
            "research_owner_subject) VALUES ('t','h','TRC-001','sub-1')"))
    monkeypatch.setenv("TRC001_ALLOW_PROVENANCE_DOWNGRADE", "1")
    with eng.connect() as conn:
        assert_retained_downgrade_allowed(conn, revision=REV)  # no raise with override


def test_downgrade_allowed_when_no_provenance():
    eng = _engine_with(table=True, with_provenance=True)
    with eng.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO retained_images (tenant_id, sha256, research_dataset_id, "
            "research_owner_subject) VALUES ('t','h','','')"))
    with eng.connect() as conn:
        assert retained_has_research_provenance(conn) is False
        assert_retained_downgrade_allowed(conn, revision=REV)  # no raise


# ── real configured engine (PostgreSQL 16 in that CI job) ────────────────────

def test_real_engine_schema_satisfies_guards():
    from app.db.session import engine
    with engine.connect() as conn:
        require_table(conn, "retained_images", revision=REV)
        verify_retained_provenance_columns(conn, revision=REV)


def test_association_downgrade_guard(monkeypatch):
    """The association downgrade guard refuses while ANY authorization row exists — active
    OR withdrawn (a migration is global). Uses a throwaway engine for deterministic isolation.

    SEC-171-03 (PR #171 assessment): this test previously asserted that withdrawn-only rows
    permit the downgrade. Withdrawn rows are the record of who was authorized and when it
    ended, so dropping them silently is no longer allowed; only the explicit override is."""
    monkeypatch.delenv("TRC001_ALLOW_PROVENANCE_DOWNGRADE", raising=False)
    eng = sa.create_engine("sqlite://")
    md = sa.MetaData()
    sa.Table("research_image_authorizations", md,
             sa.Column("id", sa.Integer, primary_key=True),
             sa.Column("status", sa.String(20)))
    md.create_all(eng)
    tbl = "research_image_authorizations"
    with eng.begin() as conn:
        conn.execute(sa.text(f"INSERT INTO {tbl} (status) VALUES ('active')"))
    with eng.connect() as conn, pytest.raises(MigrationSchemaError):
        assert_association_downgrade_allowed(conn, tbl, revision="f1a2b3c4d5e6")
    with eng.begin() as conn:
        conn.execute(sa.text(f"UPDATE {tbl} SET status='withdrawn'"))
    with eng.connect() as conn, pytest.raises(MigrationSchemaError, match="history"):
        assert_association_downgrade_allowed(conn, tbl, revision="f1a2b3c4d5e6")
    # The documented, explicit override still permits it (operator confirms archival).
    monkeypatch.setenv("TRC001_ALLOW_PROVENANCE_DOWNGRADE", "1")
    with eng.connect() as conn:
        assert_association_downgrade_allowed(conn, tbl, revision="f1a2b3c4d5e6")  # no raise
    monkeypatch.delenv("TRC001_ALLOW_PROVENANCE_DOWNGRADE", raising=False)
    # An empty table -> allowed (nothing to lose).
    with eng.begin() as conn:
        conn.execute(sa.text(f"DELETE FROM {tbl}"))
    with eng.connect() as conn:
        assert_association_downgrade_allowed(conn, tbl, revision="f1a2b3c4d5e6")  # no raise
    # Missing table -> allowed (nothing to lose).
    eng2 = sa.create_engine("sqlite://")
    with eng2.connect() as conn:
        assert_association_downgrade_allowed(conn, tbl, revision="f1a2b3c4d5e6")
