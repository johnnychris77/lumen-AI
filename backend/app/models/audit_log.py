from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, event
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base


class AuditImmutabilityError(RuntimeError):
    """Raised when code attempts to modify or delete an audit record.

    Audit records are append-only (Foundation Sprint 1, Section 10). The
    guards below enforce this at the ORM layer for both per-instance and
    bulk ORM operations. Raw SQL issued outside the ORM is not intercepted
    here — that boundary is documented in docs/foundation/AUDIT_ARCHITECTURE.md
    and is enforced operationally (database-role permissions) in managed
    deployments.
    """


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), default="Default Tenant", nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    request_method: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    request_path: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    client_ip: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    # Text, not String(4000): audit evidence must never be silently truncated.
    # SQLite ignored the old 4000 limit; PostgreSQL enforced it and rejected
    # real events (e.g. compliance evidence bundles) — found by the GPAE
    # Foundation PostgreSQL verification run.
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    compliance_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


@event.listens_for(AuditLog, "before_update")
def _block_audit_update(mapper, connection, target):
    raise AuditImmutabilityError(
        f"Audit records are immutable: refusing to update audit_logs id={target.id}."
    )


@event.listens_for(AuditLog, "before_delete")
def _block_audit_delete(mapper, connection, target):
    raise AuditImmutabilityError(
        f"Audit records are immutable: refusing to delete audit_logs id={target.id}."
    )


@event.listens_for(Session, "do_orm_execute")
def _block_audit_bulk_mutation(orm_execute_state):
    """Catch bulk ORM UPDATE/DELETE statements targeting audit_logs."""
    if not (orm_execute_state.is_update or orm_execute_state.is_delete):
        return
    mapper = orm_execute_state.bind_mapper
    if mapper is not None and mapper.class_ is AuditLog:
        raise AuditImmutabilityError(
            "Audit records are immutable: refusing bulk UPDATE/DELETE on audit_logs."
        )
