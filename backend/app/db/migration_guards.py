"""SEC-171-03: importable, op-free migration guard logic.

The alembic migration scripts call these helpers so the hardening logic (explicit errors,
prerequisite/post-condition validation, and downgrade data-loss protection) is unit-testable
directly against a real database connection — the migration modules themselves import the
alembic ``op`` proxy and are not importable outside an alembic run.
"""
from __future__ import annotations

import os

import sqlalchemy as sa

_TRUTHY = {"1", "true", "yes", "on", "enabled"}

RETAINED_TABLE = "retained_images"
RETAINED_INDEX = "ix_retained_images_research_dataset_id"
RETAINED_NOT_NULL = ("research_dataset_id", "research_owner_subject")
RETAINED_NULLABLE = ("research_attestation_id",)
RETAINED_PROVENANCE_COLS = RETAINED_NOT_NULL + RETAINED_NULLABLE


class MigrationSchemaError(RuntimeError):
    """A prerequisite/post-condition for a migration was not met.

    Raising (instead of silently returning) guarantees a failed migration is reported as a
    failure and never falsely recorded as a successful schema upgrade."""


def downgrade_override_enabled() -> bool:
    return os.getenv("TRC001_ALLOW_PROVENANCE_DOWNGRADE", "").strip().lower() in _TRUTHY


def require_table(bind, table: str, *, revision: str = "") -> None:
    if not sa.inspect(bind).has_table(table):
        raise MigrationSchemaError(
            f"Migration {revision}: prerequisite table '{table}' is missing. The schema is not "
            "initialized as expected; refusing to proceed so no false success is recorded.")


def verify_retained_provenance_columns(bind, *, revision: str = "") -> None:
    """Verify the retained_images provenance columns, nullability, and index exist with the
    expected shape. Raises on any mismatch so a partial upgrade cannot look successful."""
    insp = sa.inspect(bind)
    final = {c["name"]: c for c in insp.get_columns(RETAINED_TABLE)}
    for name in RETAINED_PROVENANCE_COLS:
        if name not in final:
            raise MigrationSchemaError(
                f"Migration {revision}: expected column '{name}' is missing after upgrade.")
    for name in RETAINED_NOT_NULL:
        if final[name].get("nullable", True):
            raise MigrationSchemaError(
                f"Migration {revision}: column '{name}' must be NOT NULL after upgrade.")
    for name in RETAINED_NULLABLE:
        if not final[name].get("nullable", False):
            raise MigrationSchemaError(
                f"Migration {revision}: column '{name}' must be NULLABLE after upgrade.")
    if RETAINED_INDEX not in {i["name"] for i in insp.get_indexes(RETAINED_TABLE)}:
        raise MigrationSchemaError(
            f"Migration {revision}: expected index '{RETAINED_INDEX}' is missing after upgrade.")


def retained_has_research_provenance(bind) -> bool:
    """True if any retained_images row carries research provenance (would be lost on drop)."""
    cols = {c["name"] for c in sa.inspect(bind).get_columns(RETAINED_TABLE)}
    predicate = []
    if "research_dataset_id" in cols:
        predicate.append("COALESCE(research_dataset_id, '') <> ''")
    if "research_owner_subject" in cols:
        predicate.append("COALESCE(research_owner_subject, '') <> ''")
    if "research_attestation_id" in cols:
        predicate.append("research_attestation_id IS NOT NULL")
    if not predicate:
        return False
    return bind.execute(
        sa.text(f"SELECT 1 FROM {RETAINED_TABLE} WHERE {' OR '.join(predicate)} LIMIT 1")
    ).first() is not None


def assert_retained_downgrade_allowed(bind, *, revision: str = "") -> None:
    """Refuse a provenance-dropping downgrade when data would be silently lost."""
    if retained_has_research_provenance(bind) and not downgrade_override_enabled():
        raise MigrationSchemaError(
            f"Migration {revision} downgrade refused: '{RETAINED_TABLE}' holds research provenance "
            "that would be permanently lost. Set TRC001_ALLOW_PROVENANCE_DOWNGRADE=1 to override "
            "after confirming the data is archived.")


def association_has_active_rows(bind, table: str) -> bool:
    if not sa.inspect(bind).has_table(table):
        return False
    return bind.execute(
        sa.text(f"SELECT 1 FROM {table} WHERE status = 'active' LIMIT 1")).first() is not None


def assert_association_downgrade_allowed(bind, table: str, *, revision: str = "") -> None:
    if association_has_active_rows(bind, table) and not downgrade_override_enabled():
        raise MigrationSchemaError(
            f"Migration {revision} downgrade refused: '{table}' holds ACTIVE authorizations that "
            "gate research-image retention. Set TRC001_ALLOW_PROVENANCE_DOWNGRADE=1 to override "
            "after confirming the data is archived.")
