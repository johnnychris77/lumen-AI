from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


SAFE_ERROR_MESSAGES = {
    400: ("BAD_REQUEST", "The request could not be processed."),
    401: ("AUTHENTICATION_REQUIRED", "Authentication is required to access this resource."),
    403: ("ACCESS_DENIED", "You do not have permission to access this resource."),
    404: ("NOT_FOUND", "The requested resource was not found."),
    409: ("CONFLICT", "The request conflicts with the current resource state."),
    422: ("VALIDATION_ERROR", "The request could not be processed. Please check the submitted fields."),
    429: ("RATE_LIMITED", "Too many requests. Please try again later."),
    500: ("INTERNAL_ERROR", "An unexpected error occurred. Please try again later."),
    503: ("SERVICE_UNAVAILABLE", "This service is temporarily unavailable."),
}


def get_request_id(request: Request | None = None) -> str:
    if request is not None:
        incoming = request.headers.get("X-Request-ID")
        if incoming:
            return incoming
    return f"req_{uuid4().hex}"


def safe_error_payload(
    status_code: int,
    request_id: str,
    code: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    default_code, default_message = SAFE_ERROR_MESSAGES.get(
        status_code,
        ("INTERNAL_ERROR", "An unexpected error occurred. Please try again later."),
    )

    return {
        "error": {
            "code": code or default_code,
            "message": message or default_message,
            "request_id": request_id,
            "status_code": status_code,
        }
    }


def safe_error_response(
    status_code: int,
    request: Request | None = None,
    code: str | None = None,
    message: str | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=safe_error_payload(
            status_code=status_code,
            request_id=request_id,
            code=code,
            message=message,
        ),
    )
