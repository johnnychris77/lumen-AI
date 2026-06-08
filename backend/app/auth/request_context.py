from __future__ import annotations

from uuid import uuid4

from fastapi import Request


def get_request_id(request: Request | None = None) -> str:
    if request is None:
        return f"req-{uuid4()}"

    return (
        request.headers.get("x-request-id")
        or request.headers.get("x-lumenai-request-id")
        or f"req-{uuid4()}"
    )


def get_correlation_id(request: Request | None = None) -> str:
    if request is None:
        return f"corr-{uuid4()}"

    return (
        request.headers.get("x-correlation-id")
        or request.headers.get("x-lumenai-correlation-id")
        or request.headers.get("x-request-id")
        or request.headers.get("x-lumenai-request-id")
        or f"corr-{uuid4()}"
    )


def build_request_audit_details(request: Request | None = None) -> dict[str, str]:
    return {
        "request_id": get_request_id(request),
        "correlation_id": get_correlation_id(request),
    }
