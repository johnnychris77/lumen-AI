from __future__ import annotations

from typing import Any

from fastapi import Request

from app.auth.context import AuthContext
from app.auth.request_context import build_request_audit_details


def build_auth_audit_details(
    auth_context: AuthContext,
    *,
    extra_details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> dict[str, Any]:
    details = auth_context.to_audit_details()
    details.update(build_request_audit_details(request))

    if extra_details:
        details.update(extra_details)

    return details


def merge_auth_context_into_details(
    details: dict[str, Any] | None,
    auth_context: AuthContext | None,
    request: Request | None = None,
) -> dict[str, Any]:
    merged = dict(details or {})

    for key, value in build_request_audit_details(request).items():
        merged.setdefault(key, value)

    if auth_context is None:
        return merged

    for key, value in auth_context.to_audit_details().items():
        merged.setdefault(key, value)

    return merged
