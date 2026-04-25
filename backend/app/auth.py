from __future__ import annotations

from fastapi import Header, HTTPException


def get_current_user(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if token == "dev-token":
        return {
            "user_email": "admin@local",
            "role_name": "platform_admin",
        }

    raise HTTPException(status_code=401, detail="Unauthorized")
