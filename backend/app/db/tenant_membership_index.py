"""Idempotent enforcement of one membership per (user_email, tenant_id).

`create_all()` adds the `UniqueConstraint` declared on the model only for tables
it creates fresh; it never alters an existing `tenant_memberships` table. So on a
database that predates the constraint we must add it ourselves — but a plain
`ADD CONSTRAINT`/`CREATE UNIQUE INDEX` fails if duplicate rows already exist.

This module: (1) skips when a unique constraint/index already covers the pair
(fresh DBs created by create_all land here — nothing to do), otherwise
(2) de-duplicates any existing `(user_email, tenant_id)` groups, keeping the most
authoritative row, then (3) creates the unique index. Best-effort and non-fatal:
failures are logged so startup is never blocked, and it is safe to run on every
boot (idempotent) on both SQLite and PostgreSQL.
"""
from __future__ import annotations

import logging

from sqlalchemy import bindparam, inspect as sqla_inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

TABLE = "tenant_memberships"
INDEX_NAME = "uq_tenant_membership_user_tenant"
_PAIR = {"user_email", "tenant_id"}


def _pair_already_enforced(engine: Engine) -> bool:
    """True if a unique constraint OR unique index already covers the pair."""
    insp = sqla_inspect(engine)
    try:
        for uc in insp.get_unique_constraints(TABLE):
            if set(uc.get("column_names") or []) == _PAIR:
                return True
    except Exception:  # pragma: no cover - dialect may not support; fall through
        pass
    try:
        for ix in insp.get_indexes(TABLE):
            if ix.get("unique") and set(ix.get("column_names") or []) == _PAIR:
                return True
    except Exception:  # pragma: no cover
        pass
    return False


def _dedupe(engine: Engine) -> int:
    """Delete duplicate rows, keeping the most authoritative per pair.

    Preference order for the row to KEEP: enabled before disabled, then lowest
    id (the earliest-created). Returns the number of rows deleted.
    """
    deleted = 0
    with engine.begin() as conn:
        dup_pairs = conn.execute(
            text(
                f"SELECT user_email, tenant_id FROM {TABLE} "
                "GROUP BY user_email, tenant_id HAVING COUNT(*) > 1"
            )
        ).fetchall()
        for user_email, tenant_id in dup_pairs:
            ids = [
                r[0]
                for r in conn.execute(
                    text(
                        f"SELECT id FROM {TABLE} "
                        "WHERE user_email = :e AND tenant_id = :t "
                        "ORDER BY is_enabled DESC, id ASC"
                    ),
                    {"e": user_email, "t": tenant_id},
                ).fetchall()
            ]
            drop = ids[1:]  # keep ids[0]
            if not drop:
                continue
            conn.execute(
                text(f"DELETE FROM {TABLE} WHERE id IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                ),
                {"ids": drop},
            )
            deleted += len(drop)
    return deleted


def ensure_tenant_membership_unique_index(engine: Engine) -> None:
    try:
        insp = sqla_inspect(engine)
        if TABLE not in insp.get_table_names():
            return  # create_all will make it with the constraint already on it
        if _pair_already_enforced(engine):
            return
        removed = _dedupe(engine)
        if removed:
            logger.warning(
                "Removed %d duplicate tenant_memberships row(s) before adding the "
                "unique (user_email, tenant_id) index.",
                removed,
            )
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} "
                    f"ON {TABLE} (user_email, tenant_id)"
                )
            )
        logger.info("Ensured unique index %s on %s(user_email, tenant_id).", INDEX_NAME, TABLE)
    except Exception as exc:  # pragma: no cover - non-fatal, must not block startup
        logger.warning("Could not ensure tenant_membership unique index: %s", exc)
