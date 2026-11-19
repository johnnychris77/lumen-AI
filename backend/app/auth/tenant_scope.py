"""Tenant scope for routes whose request can name a tenant (P472-03).

The tenant a request acts in is ALWAYS the tenant of its verified auth context
(``require_enterprise_auth(request, db=db)``): for a signed user token that is a
tenant the user is an enabled member of — the explicit ``X-Tenant-Id`` header
when one is sent and membership verifies, otherwise the user's sole membership.

A ``tenant_id`` that arrives in a query string or request body is never a
selector. It is only a claim, and a claim that names any other tenant is
refused. It is never rewritten to the caller's own tenant: a request that names
a tenant it may not use fails, it is not silently served from somewhere else.

A user who belongs to several tenants selects one with ``X-Tenant-Id`` (verified
against membership by the auth layer); a ``tenant_id`` claim must then agree.

Usage, inline in a handler so the endpoint-governance scanner sees the auth call::

    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db), tenant_id)

Routes that authenticate with ``get_current_user`` / ``require_roles`` /
``require_tenant_roles`` instead of an ``AuthContext`` use ``principal_tenant``
(or ``verified_request_tenant`` when the handler holds no principal). The rule is
the same: the tenant comes from verified membership, and a tenant named in a
header is a claim that must be one of the caller's memberships.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request

from app.auth.context import AuthContext
from app.security.principal import AuthenticatedPrincipal

# Structured security log for privileged cross-tenant access (P472-03 PA-1). The
# resolver is a pure function with no database handle, so it cannot write a
# tamper-evident audit row here; a standard security log at least makes the
# access detectable. A durable, hash-chained sink is part of the governance-owned
# closure of PA-1, not of this change.
_security_log = logging.getLogger("lumenai.security.tenant")

# One message for every refusal, so a response does not reveal whether the named
# tenant exists.
TENANT_DENIED_DETAIL = "Access to the requested tenant is not permitted."


def authorized_tenant(ctx: AuthContext, *claimed_tenant_ids: str | None) -> str:
    """Return the verified tenant of ``ctx``; refuse any claim of another tenant.

    ``claimed_tenant_ids`` are the tenant identifiers the CLIENT sent (query
    parameter, body field). Empty or absent claims are ignored — the request then
    simply acts in the verified tenant. Fails closed with HTTP 403.
    """
    tenant = (getattr(ctx, "tenant_id", "") or "").strip()
    if not tenant:
        raise HTTPException(status_code=403, detail="No verified tenant for this request.")
    for claimed in claimed_tenant_ids:
        if claimed is None:
            continue
        if not isinstance(claimed, str):
            raise HTTPException(status_code=403, detail=TENANT_DENIED_DETAIL)
        if claimed.strip() and claimed.strip() != tenant:
            raise HTTPException(status_code=403, detail=TENANT_DENIED_DETAIL)
    return tenant


# ── principals (get_current_user / require_roles / require_tenant_roles) ─────

# The two request headers a client can name a tenant in. Different parts of the
# application historically read different ones, which is how a membership check
# on one header came to guard data selected by the other (P472-03 AW-02).
TENANT_HEADERS = ("x-lumenai-tenant-id", "x-tenant-id")
NO_VERIFIED_TENANT_DETAIL = "No verified tenant membership for this request."
LEGACY_DEFAULT_TENANT = "default-tenant"


def named_tenant(request: Request) -> str | None:
    """The single tenant the request names in its headers, or ``None``.

    Two tenant headers that disagree are refused for every caller: no later code
    can then verify one and act on the other.
    """
    named = {(request.headers.get(header) or "").strip() for header in TENANT_HEADERS}
    named.discard("")
    if len(named) > 1:
        raise HTTPException(status_code=403, detail=TENANT_DENIED_DETAIL)
    return next(iter(named), None)


def request_tenant(ctx: AuthContext, request: Request) -> str:
    """The tenant a ``require_enterprise_auth`` handler acts in (P472-03 AW-03/AW-06M).

    Always the tenant of the VERIFIED auth context. A tenant named in a request
    header is only a claim: one naming any other tenant is refused (403), and two
    headers that disagree are refused. Handlers previously discarded the context
    and re-read ``X-LumenAI-Tenant-Id`` themselves (``get_request_tenant_id``),
    which the auth layer had not verified and which fell back to a shared
    ``default-tenant`` when absent. Usage, inline so the auth call stays visible::

        tenant_id = request_tenant(require_enterprise_auth(request, db=db), request)
    """
    return authorized_tenant(ctx, named_tenant(request))


def principal_tenant(principal: Any, request: Request) -> str:
    """The tenant an authenticated principal acts in for this request. Fails closed.

    For a signed user token (the only kind accepted in production):

    * a tenant named in a header is honoured only when the user is an enabled
      member of it; any other named tenant is refused (403), never replaced by
      the user's own tenant;
    * with no tenant named, the user acts in their sole membership;
    * a user with no membership, or with several and none selected, is refused.
      Nothing is served from a header alone or from a shared default tenant.

    Two caller classes keep the behaviour they had before P472-03 batch 2, which
    is ``own sole membership, else the named header, else default-tenant``:

    * the development tokens (``authentication_method == "development"``), which
      the authentication layer accepts only outside production;
    * the platform administrator (global role ``admin``), whose cross-tenant
      access is an existing, documented rule (``app/security/tenant_context.py``).
      It is unchanged here and is recorded as an open governance item: it has no
      stated purpose and leaves no access log.
    """
    requested = named_tenant(request)
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(status_code=403, detail=NO_VERIFIED_TENANT_DETAIL)

    own = principal.tenant_id
    if principal.is_development or principal.is_platform_admin:
        resolved = own or requested or LEGACY_DEFAULT_TENANT
        # P472-03 PA-1: the platform-administrator / development cross-tenant rule
        # is UNCHANGED here (an open governance item, pinned by the batch 2 tests).
        # Previously this privileged path left no access record at all. Emit a
        # structured security log whenever such a principal is resolved to a tenant
        # it is not a verified member of, so cross-tenant privileged access is at
        # least detectable. This does not alter the access decision; whether this
        # access should exist, and a tamper-evident audit sink for it, are reserved
        # for governance review and are not closed by this log.
        if resolved not in principal.verified_tenant_ids():
            _security_log.warning(
                "P472-03 PA-1 privileged cross-tenant access: principal=%s method=%s "
                "role=%s resolved_tenant=%s source=%s (access decision unchanged; "
                "governance review pending)",
                getattr(principal, "subject", None) or getattr(principal, "email", None),
                getattr(principal, "authentication_method", None),
                getattr(principal, "role", None),
                resolved,
                "named-header" if requested else ("own-tenant" if own else "legacy-default"),
            )
        return resolved

    verified = principal.verified_tenant_ids()
    if requested:
        if requested not in verified:
            raise HTTPException(status_code=403, detail=TENANT_DENIED_DETAIL)
        return requested
    if own and own in verified:
        return own
    raise HTTPException(status_code=403, detail=NO_VERIFIED_TENANT_DETAIL)


def verified_request_tenant(request: Request, db: Any) -> str:
    """``principal_tenant`` for a handler that holds no principal object.

    Authenticates the bearer token exactly as ``get_current_user`` does (401 when
    it is missing or invalid) and resolves the tenant from that identity.
    """
    from app.deps import get_current_user

    principal = get_current_user(authorization=request.headers.get("authorization"), db=db)
    return principal_tenant(principal, request)
