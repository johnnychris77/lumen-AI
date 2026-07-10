"""v4.0 — LumenAI OS (Project Genesis), Section 4: Unified Navigation —
the Platform Launcher.

Composes the module registry (Section 3), per-tenant licensing
(Section 1), the caller's role permissions (`platform_identity_service`),
per-user favorites/recents (`PlatformFavoriteModule`/`PlatformRecentModule`),
and the unified notification feed into one launcher view. A user only
ever sees modules that are both licensed for their tenant AND permitted
for their role — "Users see only applications licensed and permitted for
their role" is enforced by intersecting both, not either alone.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.platform_core import PlatformFavoriteModule, PlatformRecentModule
from app.services import (
    platform_licensing_service,
    platform_module_registry_service,
    platform_notification_service,
)

_MAX_RECENTS = 8


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def visible_modules(db: Session, tenant_id: str, role: str) -> list[dict]:
    modules = platform_module_registry_service.list_modules(db)
    licensed_keys = set(platform_licensing_service.list_licensed_module_keys(db, tenant_id))
    return [m for m in modules if m["module_key"] in licensed_keys and (not m["permissions"] or role in m["permissions"])]


def record_recent_access(db: Session, tenant_id: str, actor_email: str, module_key: str) -> None:
    row = db.query(PlatformRecentModule).filter(
        PlatformRecentModule.tenant_id == tenant_id, PlatformRecentModule.actor_email == actor_email,
        PlatformRecentModule.module_key == module_key,
    ).first()
    if row is None:
        row = PlatformRecentModule(tenant_id=tenant_id, actor_email=actor_email, module_key=module_key)
        db.add(row)
    row.accessed_at = datetime.now(timezone.utc)
    db.commit()


def recent_modules(db: Session, tenant_id: str, actor_email: str) -> list[str]:
    rows = (
        db.query(PlatformRecentModule)
        .filter(PlatformRecentModule.tenant_id == tenant_id, PlatformRecentModule.actor_email == actor_email)
        .order_by(PlatformRecentModule.accessed_at.desc())
        .limit(_MAX_RECENTS)
        .all()
    )
    return [r.module_key for r in rows]


def add_favorite(db: Session, tenant_id: str, actor_email: str, module_key: str) -> dict:
    existing = db.query(PlatformFavoriteModule).filter(
        PlatformFavoriteModule.tenant_id == tenant_id, PlatformFavoriteModule.actor_email == actor_email,
        PlatformFavoriteModule.module_key == module_key,
    ).first()
    if existing is not None:
        return _row_to_dict(existing)
    row = PlatformFavoriteModule(tenant_id=tenant_id, actor_email=actor_email, module_key=module_key)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def remove_favorite(db: Session, tenant_id: str, actor_email: str, module_key: str) -> bool:
    row = db.query(PlatformFavoriteModule).filter(
        PlatformFavoriteModule.tenant_id == tenant_id, PlatformFavoriteModule.actor_email == actor_email,
        PlatformFavoriteModule.module_key == module_key,
    ).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def favorite_modules(db: Session, tenant_id: str, actor_email: str) -> list[str]:
    rows = db.query(PlatformFavoriteModule).filter(
        PlatformFavoriteModule.tenant_id == tenant_id, PlatformFavoriteModule.actor_email == actor_email,
    ).all()
    return [r.module_key for r in rows]


def launcher_view(db: Session, tenant_id: str, role: str, actor_email: str) -> dict:
    modules = visible_modules(db, tenant_id, role)
    favorite_keys = set(favorite_modules(db, tenant_id, actor_email))
    recent_keys = recent_modules(db, tenant_id, actor_email)
    notifications = platform_notification_service.unified_notifications(db, tenant_id, recipient_role=role, limit=10)
    tasks = [n for n in notifications if not n["read"]]

    return {
        "modules": modules,
        "favorites": [m for m in modules if m["module_key"] in favorite_keys],
        "recent": [m for m in modules if m["module_key"] in recent_keys],
        "notifications": notifications,
        "tasks": tasks,
        "notification_count": len(notifications),
        "unread_task_count": len(tasks),
    }
