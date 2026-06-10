from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/api/public/module-status", tags=["public-module-status"])


ModuleStatusValue = Literal["available", "degraded", "unavailable"]
PublicStatusValue = Literal["public", "protected", "not_configured"]


class PublicModuleStatus(BaseModel):
    module: str
    status: ModuleStatusValue
    public_status: PublicStatusValue
    requires_authentication: bool
    description: str
    checked_at: str


class PublicModuleStatusCollection(BaseModel):
    modules: list[PublicModuleStatus]
    checked_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _module_status(
    module: str,
    description: str,
    public_status: PublicStatusValue = "protected",
    status: ModuleStatusValue = "available",
    requires_authentication: bool = True,
) -> PublicModuleStatus:
    return PublicModuleStatus(
        module=module,
        status=status,
        public_status=public_status,
        requires_authentication=requires_authentication,
        description=description,
        checked_at=_now_iso(),
    )


@router.get("/vendor", response_model=PublicModuleStatus)
def get_vendor_module_status() -> PublicModuleStatus:
    return _module_status(
        module="Vendor Governance",
        description="Vendor governance workflows are available for authenticated enterprise users.",
    )


@router.get("/capa", response_model=PublicModuleStatus)
def get_capa_module_status() -> PublicModuleStatus:
    return _module_status(
        module="CAPA Workflow",
        description="CAPA workflow services are available for authenticated enterprise users.",
    )


@router.get("/audit", response_model=PublicModuleStatus)
def get_audit_module_status() -> PublicModuleStatus:
    return _module_status(
        module="Audit Command Center",
        description="Audit command center services are available for authenticated enterprise users.",
    )


@router.get("/evidence", response_model=PublicModuleStatus)
def get_evidence_module_status() -> PublicModuleStatus:
    return _module_status(
        module="Compliance Evidence",
        description="Compliance evidence bundle services are available for authenticated enterprise users.",
    )


@router.get("/all", response_model=PublicModuleStatusCollection)
def get_all_module_statuses() -> PublicModuleStatusCollection:
    checked_at = _now_iso()
    modules = [
        PublicModuleStatus(
            module="Vendor Governance",
            status="available",
            public_status="protected",
            requires_authentication=True,
            description="Vendor governance workflows are available for authenticated enterprise users.",
            checked_at=checked_at,
        ),
        PublicModuleStatus(
            module="CAPA Workflow",
            status="available",
            public_status="protected",
            requires_authentication=True,
            description="CAPA workflow services are available for authenticated enterprise users.",
            checked_at=checked_at,
        ),
        PublicModuleStatus(
            module="Audit Command Center",
            status="available",
            public_status="protected",
            requires_authentication=True,
            description="Audit command center services are available for authenticated enterprise users.",
            checked_at=checked_at,
        ),
        PublicModuleStatus(
            module="Compliance Evidence",
            status="available",
            public_status="protected",
            requires_authentication=True,
            description="Compliance evidence bundle services are available for authenticated enterprise users.",
            checked_at=checked_at,
        ),
    ]

    return PublicModuleStatusCollection(modules=modules, checked_at=checked_at)
