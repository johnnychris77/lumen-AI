"""P14: SSO configuration routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth

router = APIRouter(prefix="/api/tenant", tags=["sso-config"])


class SSOConfigRequest(BaseModel):
    provider: str = "none"
    oidc_issuer_url: str = ""
    jwks_url: str = ""
    client_id: str = ""
    audience: str = ""
    redirect_uri: str = ""
    groups_claim: str = "groups"


VALID_PROVIDERS = {"azure_ad", "okta", "epic", "none"}


def _get_or_create_sso(db: Session, tenant_id: str):
    from app.models.sso_config import TenantSSOConfig
    cfg = db.query(TenantSSOConfig).filter(
        TenantSSOConfig.tenant_id == tenant_id
    ).first()
    if cfg is None:
        cfg = TenantSSOConfig(tenant_id=tenant_id)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.post("/sso-config")
def create_or_update_sso_config(
    body: SSOConfigRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Create or update SSO config — requires auth. Does NOT store client_secret."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id

    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Valid: {sorted(VALID_PROVIDERS)}",
        )

    from app.models.sso_config import TenantSSOConfig
    cfg = db.query(TenantSSOConfig).filter(
        TenantSSOConfig.tenant_id == tenant_id
    ).first()
    if cfg is None:
        cfg = TenantSSOConfig(tenant_id=tenant_id)
        db.add(cfg)

    cfg.provider = body.provider
    cfg.oidc_issuer_url = body.oidc_issuer_url
    cfg.jwks_url = body.jwks_url
    cfg.client_id = body.client_id
    cfg.audience = body.audience
    cfg.redirect_uri = body.redirect_uri
    cfg.groups_claim = body.groups_claim
    cfg.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cfg)

    return {
        "tenant_id": tenant_id,
        "provider": cfg.provider,
        "oidc_issuer_url": cfg.oidc_issuer_url,
        "jwks_url": cfg.jwks_url,
        "client_id": cfg.client_id[:4] + "****" if cfg.client_id else "",
        "audience": cfg.audience,
        "redirect_uri": cfg.redirect_uri,
        "groups_claim": cfg.groups_claim,
        "updated_at": cfg.updated_at.isoformat(),
    }


@router.get("/sso-config")
def get_sso_config(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Return current SSO config (masks sensitive fields) — requires auth."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    from app.models.sso_config import TenantSSOConfig
    cfg = db.query(TenantSSOConfig).filter(
        TenantSSOConfig.tenant_id == tenant_id
    ).first()
    if cfg is None:
        return {"tenant_id": tenant_id, "provider": "none", "configured": False}
    return {
        "tenant_id": tenant_id,
        "provider": cfg.provider,
        "oidc_issuer_url": cfg.oidc_issuer_url,
        "jwks_url": cfg.jwks_url,
        "client_id": cfg.client_id[:4] + "****" if cfg.client_id else "",
        "audience": cfg.audience,
        "redirect_uri": cfg.redirect_uri,
        "groups_claim": cfg.groups_claim,
        "configured": cfg.provider != "none",
        "updated_at": cfg.updated_at.isoformat(),
    }


@router.delete("/sso-config")
def delete_sso_config(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Remove SSO config (revert to password auth) — requires auth."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    from app.models.sso_config import TenantSSOConfig
    cfg = db.query(TenantSSOConfig).filter(
        TenantSSOConfig.tenant_id == tenant_id
    ).first()
    if cfg is not None:
        db.delete(cfg)
        db.commit()
    return {"tenant_id": tenant_id, "status": "removed", "provider": "none"}
