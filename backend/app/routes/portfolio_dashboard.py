from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.portfolio_dashboard import executive_portfolio_dashboard, portfolio_summary, qbr_rollup
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["portfolio-dashboard"])


@router.get("/portfolio-dashboard/summary")
def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return portfolio_summary(db)


@router.get("/portfolio-dashboard/qbr-rollup")
def get_qbr_rollup(
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return qbr_rollup(db)


@router.get("/portfolio-dashboard/executive")
def get_executive_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return executive_portfolio_dashboard(db)
