"""Typed authenticated-principal contract (Pilot Zero Directive 002, Phase 2).

Replaces the ad-hoc ``types.SimpleNamespace`` identity previously returned by
``app.deps.get_current_user`` — which carried only ``id``/``email``/``role``
and, critically, **no tenant** — with one typed contract that both the
development and JWT authentication paths implement.

Design rules enforced here:

* Tenant authority comes from **verified membership**, never from a client
  header. ``tenant_memberships`` / ``active_tenant_id`` are populated by the
  authentication layer from the ``tenant_memberships`` table for the
  authenticated identity; this module has no way to accept a header value.
* Development identities are visibly labeled (``authentication_method ==
  "development"``, ``is_development is True``).
* Backward compatibility: the fields every existing call site reads
  (``id``, ``email``, ``username``, ``role``) remain present, and a
  ``tenant_id`` property is provided so existing ``getattr(user,
  "tenant_id", None)`` call sites now receive a **verified** value instead
  of always ``None``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

METHOD_DEVELOPMENT = "development"
METHOD_JWT = "jwt"
METHOD_OIDC = "oidc"
METHOD_DEMO = "demo"


@dataclass(frozen=True)
class TenantMembershipView:
    """A verified, read-only view of one enabled tenant membership."""

    tenant_id: str
    tenant_name: str
    role_name: str


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """The single authenticated-identity contract for the application.

    Every field except ``role`` may be empty for a minimally-identified
    principal, but the object as a whole is only ever constructed by the
    authentication layer after a credential has been verified — it is never
    built from client-supplied identity headers.
    """

    subject: str
    email: str
    role: str
    authentication_method: str
    user_id: int = 0
    username: str = ""
    tenant_memberships: tuple[TenantMembershipView, ...] = field(default_factory=tuple)
    active_tenant_id: str | None = None
    token_id: str | None = None
    issued_at: int | None = None
    expires_at: int | None = None

    # --- backward-compatible aliases (existing call sites read these) ---
    @property
    def id(self) -> int:  # noqa: A003 - matches the prior SimpleNamespace field
        return self.user_id

    @property
    def tenant_id(self) -> str | None:
        """Verified active tenant. Prior code read ``getattr(user,
        'tenant_id', None)`` and always got None (the field never existed);
        it now receives the membership-verified active tenant."""
        return self.active_tenant_id

    # --- helpers ---
    @property
    def is_development(self) -> bool:
        return self.authentication_method == METHOD_DEVELOPMENT

    @property
    def is_platform_admin(self) -> bool:
        return self.role == "admin"

    def verified_tenant_ids(self) -> frozenset[str]:
        return frozenset(m.tenant_id for m in self.tenant_memberships)

    def has_verified_membership(self, tenant_id: str) -> bool:
        return tenant_id in self.verified_tenant_ids()
