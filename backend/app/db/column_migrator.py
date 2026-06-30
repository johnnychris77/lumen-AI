"""Lightweight, idempotent column back-fill for existing tables.

create_all() adds missing *tables* but never alters existing ones, so columns
added to a model after a table already exists in production are simply absent —
and any query/insert that references them returns a 500 (which, because the
error response is generated above the CORS middleware, surfaces in the browser
as a misleading "No 'Access-Control-Allow-Origin'" CORS error).

This adds any missing columns via ALTER TABLE ... ADD COLUMN, compiling each
column's type for the active dialect. Columns are added nullable (with a simple
DEFAULT when the model defines a scalar one) so the change is safe on tables
that already contain rows, on both PostgreSQL and SQLite.
"""
from __future__ import annotations

import logging

from sqlalchemy import inspect as sqla_inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _default_clause(col, dialect_name: str) -> str:
    """Return a ' DEFAULT <x>' clause for a simple scalar default, else ''."""
    default = getattr(col, "default", None)
    if default is None or not getattr(default, "is_scalar", False):
        return ""
    val = default.arg
    if isinstance(val, bool):
        if dialect_name == "postgresql":
            return f" DEFAULT {'true' if val else 'false'}"
        return f" DEFAULT {1 if val else 0}"
    if isinstance(val, (int, float)):
        return f" DEFAULT {val}"
    if isinstance(val, str):
        escaped = val.replace("'", "''")
        return f" DEFAULT '{escaped}'"
    return ""


def ensure_columns(engine: Engine, model) -> list[str]:
    """Add any columns defined on `model` that are missing from its DB table.

    Returns the list of column names added. Best-effort and non-fatal: a failure
    on one column is logged and skipped so startup is never blocked.
    """
    table = model.__table__
    added: list[str] = []
    try:
        inspector = sqla_inspect(engine)
        if table.name not in inspector.get_table_names():
            return added  # create_all will handle brand-new tables
        existing = {c["name"] for c in inspector.get_columns(table.name)}
    except Exception as exc:  # pragma: no cover - inspection failure is non-fatal
        logger.warning("Column back-fill skipped for %s: %s", table.name, exc)
        return added

    dialect = engine.dialect
    for col in table.columns:
        if col.name in existing:
            continue
        try:
            coltype = col.type.compile(dialect=dialect)
        except Exception:
            # Some custom types can't compile standalone — skip them safely.
            continue
        ddl = f'ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}'
        ddl += _default_clause(col, dialect.name)
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
            added.append(col.name)
        except Exception as exc:  # pragma: no cover - per-column failure is non-fatal
            logger.warning("Could not add column %s.%s: %s", table.name, col.name, exc)

    if added:
        logger.info("Back-filled columns on %s: %s", table.name, ", ".join(added))
    return added
