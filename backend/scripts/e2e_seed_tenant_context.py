"""Seed a LOCAL throw-away database for the B5.1 browser test (P472-03 Batch 5).

Creates synthetic login accounts (no PHI, ``example.test`` addresses) with
tenant memberships, so ``frontend/tests/e2e/tenantContext.e2e.mjs`` can log in
through the real UI against a real backend:

* ``e2e-single@example.test`` — one membership (``e2e-hosp-a``)
* ``e2e-multi@example.test``  — two memberships (``e2e-hosp-a``, ``e2e-hosp-c``)
* ``e2e-nobody@example.test`` — no membership
* ``e2e-other@example.test``  — one membership in ``e2e-hosp-b`` (the "other tenant")

Usage (never against a shared or production database):

    E2E_PASSWORD=<local throw-away password> DATABASE_URL=sqlite:////tmp/e2e.db \
        python scripts/e2e_seed_tenant_context.py

Refuses to run when APP_ENV is production, when DATABASE_URL is unset, or
when E2E_PASSWORD is unset (no default credential is baked in).
"""
from __future__ import annotations

import os
import sys

USERS = {
    "e2e-single@example.test": ["e2e-hosp-a"],
    "e2e-multi@example.test": ["e2e-hosp-a", "e2e-hosp-c"],
    "e2e-nobody@example.test": [],
    "e2e-other@example.test": ["e2e-hosp-b"],
}


def main() -> int:
    if os.getenv("APP_ENV", "").lower() in {"production", "prod"}:
        print("refusing to seed: APP_ENV is production", file=sys.stderr)
        return 2
    if not os.getenv("DATABASE_URL"):
        print("refusing to seed: set DATABASE_URL to a local throw-away database", file=sys.stderr)
        return 2
    password = os.getenv("E2E_PASSWORD")
    if not password:
        print("refusing to seed: set E2E_PASSWORD (no default credential)", file=sys.stderr)
        return 2

    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the backend root, for `app`
    from passlib.hash import bcrypt

    from app.db import models
    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    from app.models.admin_credential import AdminCredential
    from app.models.user_role_assignment import UserRoleAssignment

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for user, tenants in USERS.items():
            if not db.query(AdminCredential).filter_by(username=user).first():
                db.add(AdminCredential(username=user, password_hash=bcrypt.hash(password), role="spd_manager"))
            if not db.query(UserRoleAssignment).filter_by(username=user).first():
                db.add(UserRoleAssignment(username=user, role="spd_manager", assigned_by="b5.1-e2e-seed"))
            for tenant in tenants:
                if not db.query(models.TenantMembership).filter_by(user_email=user, tenant_id=tenant).first():
                    db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role="tenant_admin", is_enabled=True))
        db.commit()
    finally:
        db.close()
    print("seeded", ", ".join(USERS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
