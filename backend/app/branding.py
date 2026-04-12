from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models


def get_branding(db: Session, tenant_id: str, tenant_name: str) -> dict:
    row = (
        db.query(models.TenantBranding)
        .filter(models.TenantBranding.tenant_id == tenant_id)
        .order_by(models.TenantBranding.id.desc())
        .first()
    )

    if row:
        return {
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant_name,
            "display_name": row.display_name or tenant_name,
            "logo_url": row.logo_url,
            "accent_color": row.accent_color or "#2563eb",
            "welcome_text": row.welcome_text,
            "export_prefix": row.export_prefix or tenant_id,
            "support_email": row.support_email,
            "source": "configured",
        }

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "display_name": tenant_name,
        "logo_url": "",
        "accent_color": "#2563eb",
        "welcome_text": f"Welcome to {tenant_name}",
        "export_prefix": tenant_id,
        "support_email": "",
        "source": "default",
    }
