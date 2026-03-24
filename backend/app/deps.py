from __future__ import annotations

import os
from types import SimpleNamespace

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db import models

DEV_TOKEN = os.getenv("LUMENAI_DEV_TOKEN", "dev-token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = authorization.split(" ", 1)[1].strip()

    # Simple dev token role mapping for now
    dev_role_map = {
        "dev-token": "admin",
        "spd-manager-token": "spd_manager",
        "vendor-token": "vendor_user",
        "viewer-token": "viewer",
    }

    if token in dev_role_map:
        return SimpleNamespace(
            id=0,
            email=f"{dev_role_map[token]}@local",
            role=dev_role_map[token],
        )

    # Optional DB-backed lookup by email token convention
    # Example token format: user:<email>
    if token.startswith("user:"):
        email = token.split("user:", 1)[1].strip().lower()
        user = (
            db.query(models.User)
            .filter(models.User.email == email)
            .first()
        )
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )
