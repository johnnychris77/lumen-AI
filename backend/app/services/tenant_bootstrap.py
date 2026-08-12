from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from app.db import models

logger = logging.getLogger(__name__)


def ensure_bootstrap_admins(db: Session) -> list[str]:
    """Idempotently grant an ENABLED tenant_admin membership to each admin listed
    in the ``BOOTSTRAP_TENANT_ADMINS`` env var (comma-separated emails), in
    ``BOOTSTRAP_TENANT_ID`` (default ``default-tenant``).

    This closes the pilot gap where a user can log in (app JWT) but has no tenant
    membership, so every ``/api/enterprise/*`` route returns 403 "Enabled tenant
    membership required" (vendor/manufacturer baselines, audit KPIs, …). It is
    deliberately an explicit allow-list keyed off configuration — it NEVER grants
    membership to arbitrary users, so tenant isolation is preserved. Safe to run
    on every startup; existing memberships are left as-is (re-enabled if a listed
    admin was previously disabled). Returns the emails provisioned/confirmed.
    """
    raw = (os.getenv("BOOTSTRAP_TENANT_ADMINS", "") or "").strip()
    if not raw:
        return []
    tenant_id = (os.getenv("BOOTSTRAP_TENANT_ID", "") or "default-tenant").strip()

    provisioned: list[str] = []
    for email in [e.strip().lower() for e in raw.split(",") if e.strip()]:
        existing = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == email,
                models.TenantMembership.tenant_id == tenant_id,
            )
            .first()
        )
        if existing:
            if not existing.is_enabled:
                existing.is_enabled = True
                db.commit()
            provisioned.append(email)
            continue
        # Use the model the enterprise auth check actually queries
        # (app.db.models.TenantMembership): tenant_id / user_email / role /
        # is_enabled. "tenant_admin" is the highest tenant-scoped role.
        db.add(
            models.TenantMembership(
                user_email=email,
                tenant_id=tenant_id,
                role="tenant_admin",
                is_enabled=True,
            )
        )
        db.commit()
        provisioned.append(email)

    if provisioned:
        logger.info(
            "Bootstrapped tenant_admin membership in %s for: %s",
            tenant_id,
            ", ".join(provisioned),
        )
    return provisioned


DEFAULT_RETENTION = {
    "inspection": 365,
    "audit_log": 365,
    "digest_delivery": 365,
    "evidence_pack": 730,
}


def bootstrap_tenant(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    admin_email: str,
    default_slack_recipient: str = "",
    default_email_recipient: str = "",
    notes: str = "",
) -> dict:
    tenant_id = tenant_id.strip()
    tenant_name = tenant_name.strip()
    admin_email = admin_email.strip().lower()

    existing = (
        db.query(models.TenantOnboarding)
        .filter(models.TenantOnboarding.tenant_id == tenant_id)
        .order_by(models.TenantOnboarding.id.desc())
        .first()
    )
    if existing:
        return {
            "already_exists": True,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "admin_email": admin_email,
            "message": "Tenant already onboarded",
        }

    membership = (
        db.query(models.TenantMembership)
        .filter(
            models.TenantMembership.user_email == admin_email,
            models.TenantMembership.tenant_id == tenant_id,
        )
        .first()
    )
    if not membership:
        membership = models.TenantMembership(
            user_email=admin_email,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            role_name="tenant_admin",
            is_enabled=True,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)

    created_policies = []
    for artifact_type, retention_days in DEFAULT_RETENTION.items():
        existing_policy = (
            db.query(models.RetentionPolicy)
            .filter(
                models.RetentionPolicy.tenant_id == tenant_id,
                models.RetentionPolicy.artifact_type == artifact_type,
            )
            .order_by(models.RetentionPolicy.id.desc())
            .first()
        )
        if not existing_policy:
            row = models.RetentionPolicy(
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                artifact_type=artifact_type,
                retention_days=retention_days,
                legal_hold_enabled=False,
                notes="Bootstrap default",
                is_enabled=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            created_policies.append(row.artifact_type)

    created_subscriptions = []
    if default_slack_recipient:
        sub = models.DigestSubscription(
            name=f"{tenant_name} Executive Slack",
            role_scope="executive",
            site_name=tenant_id,
            channel="slack",
            recipients=default_slack_recipient,
            digest_type="weekly",
            is_enabled=True,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        created_subscriptions.append({"channel": "slack", "recipients": default_slack_recipient})

    if default_email_recipient:
        sub = models.DigestSubscription(
            name=f"{tenant_name} Executive Email",
            role_scope="executive",
            site_name=tenant_id,
            channel="email",
            recipients=default_email_recipient,
            digest_type="weekly",
            is_enabled=True,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        created_subscriptions.append({"channel": "email", "recipients": default_email_recipient})

    onboarding = models.TenantOnboarding(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        admin_email=admin_email,
        status="completed",
        notes=notes,
    )
    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)

    return {
        "already_exists": False,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "admin_email": admin_email,
        "membership_id": membership.id,
        "created_policies": created_policies,
        "created_subscriptions": created_subscriptions,
        "onboarding_id": onboarding.id,
        "message": "Tenant bootstrap completed",
    }
