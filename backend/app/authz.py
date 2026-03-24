from __future__ import annotations

from typing import Iterable

from fastapi import Depends, HTTPException, status

from app.deps import get_current_user


def require_roles(*allowed_roles: str):
    allowed = set(allowed_roles)

    def checker(current_user = Depends(get_current_user)):
        user_role = getattr(current_user, "role", "viewer")
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' is not permitted for this resource.",
            )
        return current_user

    return checker
