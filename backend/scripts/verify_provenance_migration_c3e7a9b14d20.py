"""Real Alembic migration test for c3e7a9b14d20 (dataset provenance columns).

Runs the ACTUAL migration upgrade() + downgrade() against a representative
existing 'dataset_registry_entries' table that holds LEGACY rows and does NOT
yet have the provenance columns (the pre-Stage-4 shape). Verifies:
  * upgrade adds all 9 provenance columns + 2 indexes;
  * legacy rows are preserved and BACKFILLED fail-closed
    (data_provenance_class='legacy_unverified', provenance_approval_status='pending');
  * no legacy row is relabelled clinical;
  * downgrade drops the 9 columns + indexes and PRESERVES all legacy data.

Also exercises the GUARD: running upgrade() when the table is absent is a no-op.

Run from the scratchpad dir (NOT backend/) so the local backend/alembic package
does not shadow the installed alembic distribution.
"""
import importlib.util
import os
import sys
import tempfile

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

BACKEND = "/home/user/lumen-AI/backend"
MIG_PATH = os.path.join(
    BACKEND, "alembic", "versions", "c3e7a9b14d20_add_dataset_provenance_classification.py"
)

PROV_COLS = [
    "data_provenance_class", "provenance_source_id", "provenance_source_version",
    "provenance_source_institution", "provenance_rights_evidence_ref",
    "provenance_specimen_id", "provenance_approval_status", "provenance_approved_by",
    "provenance_approved_at",
]
PROV_IDX = [
    "ix_dataset_registry_entries_data_provenance_class",
    "ix_dataset_registry_entries_provenance_approval_status",
]


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_c3e7a9b14d20", MIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cols(conn, table):
    insp = sa.inspect(conn)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _indexes(conn, table):
    insp = sa.inspect(conn)
    if not insp.has_table(table):
        return set()
    return {i["name"] for i in insp.get_indexes(table)}


def _create_legacy_table(conn):
    # Representative PRE-provenance schema + legacy rows.
    conn.exec_driver_sql(
        """
        CREATE TABLE dataset_registry_entries (
            id INTEGER PRIMARY KEY,
            lcid VARCHAR(40) NOT NULL,
            tenant_id VARCHAR(100) NOT NULL,
            dataset_version_id INTEGER,
            retained_image_id INTEGER NOT NULL,
            image_sha256 VARCHAR(64) NOT NULL,
            instrument_family VARCHAR(100) NOT NULL,
            manufacturer VARCHAR(100) NOT NULL,
            current_label VARCHAR(60) NOT NULL DEFAULT '',
            review_status VARCHAR(30) NOT NULL DEFAULT 'unlabeled',
            training_eligibility BOOLEAN NOT NULL DEFAULT 0,
            retention_status VARCHAR(20) NOT NULL DEFAULT 'active'
        )
        """
    )
    rows = [
        (1, "LCID-0001", "tenant-A", 10, 101, "a" * 64, "scissors", "Acme", "probable_retained_debris", "APPROVED", 1, "active"),
        (2, "LCID-0002", "tenant-A", 10, 102, "b" * 64, "forceps", "Beta", "", "unlabeled", 0, "active"),
        (3, "LCID-0003", "tenant-B", 11, 103, "c" * 64, "drill", "Gamma", "no_observable_abnormality", "APPROVED", 1, "purged"),
    ]
    for r in rows:
        conn.exec_driver_sql(
            "INSERT INTO dataset_registry_entries "
            "(id,lcid,tenant_id,dataset_version_id,retained_image_id,image_sha256,instrument_family,manufacturer,current_label,review_status,training_eligibility,retention_status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            r,
        )


def main():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "legacy.db")
    engine = sa.create_engine(f"sqlite:///{db_path}")
    mig = _load_migration()

    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        print(("PASS" if cond else "FAIL"), name)

    # ── Guard: upgrade on an ABSENT table is a no-op ────────────────────────
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        mig.op = Operations(ctx)
        mig.upgrade()  # table absent -> should no-op, not error
        check("guard_upgrade_noop_when_table_absent", not sa.inspect(conn).has_table("dataset_registry_entries"))
        conn.commit()

    # ── Representative legacy DB ─────────────────────────────────────────────
    with engine.connect() as conn:
        _create_legacy_table(conn)
        conn.commit()
        legacy_cols = _cols(conn, "dataset_registry_entries")
        check("legacy_table_has_no_provenance_cols", not (set(PROV_COLS) & legacy_cols))
        check("legacy_rowcount_3", conn.exec_driver_sql("SELECT COUNT(*) FROM dataset_registry_entries").scalar() == 3)

    # ── UPGRADE ──────────────────────────────────────────────────────────────
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        mig.op = Operations(ctx)
        mig.upgrade()
        conn.commit()
        cols = _cols(conn, "dataset_registry_entries")
        idx = _indexes(conn, "dataset_registry_entries")
        check("upgrade_added_all_9_columns", set(PROV_COLS).issubset(cols))
        check("upgrade_created_indexes", set(PROV_IDX).issubset(idx))
        # Backfill: every legacy row fail-closed.
        rows = conn.exec_driver_sql(
            "SELECT data_provenance_class, provenance_approval_status FROM dataset_registry_entries ORDER BY id"
        ).fetchall()
        check("backfill_all_legacy_unverified", all(r[0] == "legacy_unverified" for r in rows))
        check("backfill_all_pending", all(r[1] == "pending" for r in rows))
        # No legacy row became clinical.
        check("no_legacy_row_is_clinical", not any(r[0] == "real_clinical" for r in rows))
        # Original data preserved.
        orig = conn.exec_driver_sql(
            "SELECT id,lcid,image_sha256,tenant_id,current_label FROM dataset_registry_entries ORDER BY id"
        ).fetchall()
        check("upgrade_preserves_legacy_lcid", [o[1] for o in orig] == ["LCID-0001", "LCID-0002", "LCID-0003"])
        check("upgrade_preserves_legacy_sha", orig[0][2] == "a" * 64 and orig[2][2] == "c" * 64)
        check("upgrade_rowcount_still_3", len(orig) == 3)

    # ── Idempotency: a second upgrade is a no-op (add-missing only) ──────────
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        mig.op = Operations(ctx)
        mig.upgrade()
        conn.commit()
        check("second_upgrade_idempotent_rowcount", conn.exec_driver_sql("SELECT COUNT(*) FROM dataset_registry_entries").scalar() == 3)

    # ── DOWNGRADE ────────────────────────────────────────────────────────────
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        mig.op = Operations(ctx)
        mig.downgrade()
        conn.commit()
        cols = _cols(conn, "dataset_registry_entries")
        idx = _indexes(conn, "dataset_registry_entries")
        check("downgrade_dropped_all_provenance_cols", not (set(PROV_COLS) & cols))
        check("downgrade_dropped_indexes", not (set(PROV_IDX) & idx))
        # Legacy data preserved across the rollback.
        rows = conn.exec_driver_sql(
            "SELECT id,lcid,image_sha256,current_label FROM dataset_registry_entries ORDER BY id"
        ).fetchall()
        check("downgrade_preserves_rowcount_3", len(rows) == 3)
        check("downgrade_preserves_lcid", [r[1] for r in rows] == ["LCID-0001", "LCID-0002", "LCID-0003"])
        check("downgrade_preserves_sha", rows[0][2] == "a" * 64)
        check("downgrade_preserves_label", rows[0][3] == "probable_retained_debris")

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Migration test c3e7a9b14d20: {passed}/{total} checks passed ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
