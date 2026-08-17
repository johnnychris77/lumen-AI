"""One membership per (user_email, tenant_id) — enforced at the DB level.

Covers the de-dup + index creation on a legacy table (no constraint), the
idempotent skip when it is already enforced, and that duplicates are blocked on
the real application engine.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.db import models
from app.db.session import SessionLocal, engine as app_engine
from app.db.tenant_membership_index import (
    _pair_already_enforced,
    ensure_tenant_membership_unique_index,
)

_LEGACY_DDL = (
    "CREATE TABLE tenant_memberships ("
    "id INTEGER PRIMARY KEY, tenant_id VARCHAR(255), user_email VARCHAR(255), "
    "role VARCHAR(100), is_enabled BOOLEAN, created_at TIMESTAMP, tenant_region VARCHAR(50))"
)


def test_dedupe_keeps_enabled_lowest_id_then_adds_index():
    """A legacy table with duplicates is de-duped (keeping the enabled row) and
    then gets a unique index that blocks further duplicates."""
    engine = create_engine("sqlite://")  # isolated in-memory DB
    with engine.begin() as c:
        c.execute(text(_LEGACY_DDL))
        # (a@x, t1) duplicated: id=1 disabled, id=2 enabled -> keep id=2.
        # (b@x, t2) unique -> untouched.
        c.execute(
            text(
                "INSERT INTO tenant_memberships (id, tenant_id, user_email, role, is_enabled) "
                "VALUES (1,'t1','a@x','viewer',0),(2,'t1','a@x','tenant_admin',1),(3,'t2','b@x','viewer',1)"
            )
        )

    ensure_tenant_membership_unique_index(engine)

    with engine.connect() as c:
        ids = {r[0] for r in c.execute(text("SELECT id FROM tenant_memberships")).fetchall()}
    assert ids == {2, 3}, "kept the enabled row for the duplicated pair; left the unique row"
    assert _pair_already_enforced(engine) is True

    # A new duplicate is now rejected by the DB.
    with pytest.raises(IntegrityError):
        with engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO tenant_memberships (id, tenant_id, user_email, role, is_enabled) "
                    "VALUES (9,'t1','a@x','viewer',1)"
                )
            )


def test_idempotent_second_run_is_noop():
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text(_LEGACY_DDL))
        c.execute(
            text(
                "INSERT INTO tenant_memberships (id, tenant_id, user_email, role, is_enabled) "
                "VALUES (1,'t1','a@x','viewer',1)"
            )
        )
    ensure_tenant_membership_unique_index(engine)
    # Second run must be a clean no-op (already enforced) and not raise.
    ensure_tenant_membership_unique_index(engine)
    assert _pair_already_enforced(engine) is True


def test_missing_table_is_safe():
    engine = create_engine("sqlite://")  # no tables at all
    ensure_tenant_membership_unique_index(engine)  # must not raise


def test_real_engine_blocks_duplicate_membership():
    """On the application engine the constraint blocks a second membership for the
    same (user_email, tenant_id). (conftest truncates the table per test.)"""
    ensure_tenant_membership_unique_index(app_engine)
    email = "dup-index-test@example.com"
    tenant = "uniq-index-test-tenant"
    db = SessionLocal()
    try:
        db.add(models.TenantMembership(tenant_id=tenant, user_email=email, role="viewer", is_enabled=True))
        db.commit()
        db.add(models.TenantMembership(tenant_id=tenant, user_email=email, role="operator", is_enabled=True))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        # Leave the table clean regardless of the per-test truncation.
        db.query(models.TenantMembership).filter(
            models.TenantMembership.user_email == email
        ).delete()
        db.commit()
        db.close()
