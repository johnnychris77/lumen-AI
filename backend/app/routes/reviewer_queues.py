"""Project Canvas — Section 20: Assignment and Queues REST surface.

Thin HTTP layer over `app.services.reviewer_queue_service` — read-only, no
new assignment/workload data invented at this layer either.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.annotation_database import ROLES_MAY_VIEW
from app.services import reviewer_queue_service
from app.authz import require_roles

router = APIRouter(tags=["reviewer-queues"])


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


@router.get("/reviewer-queues")
def get_reviewer_queues(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES_MAY_VIEW)),
):
    tenant_id = _tenant(current_user, request)
    return reviewer_queue_service.get_queues(db, tenant_id=tenant_id, actor=_actor(current_user))
