from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models


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
