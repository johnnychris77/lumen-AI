import os
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.services.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

_APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
_IS_PRODUCTION = _APP_ENV in {"production", "prod"}


def _get_seed_password() -> str:
    """
    Return the admin seed password from env, or generate a random one for
    non-production use. Fails closed in production if the env var is absent.
    """
    password = os.getenv("ADMIN_SEED_PASSWORD", "").strip()
    if password:
        return password
    if _IS_PRODUCTION:
        raise RuntimeError(
            "ADMIN_SEED_PASSWORD environment variable must be set in production. "
            "Refusing to seed admin with a default or random password."
        )
    # Development / staging: generate a one-time random password and log it once.
    generated = secrets.token_urlsafe(24)
    print(f"[WARN] ADMIN_SEED_PASSWORD not set. Generated one-time admin password: {generated}")  # noqa: T201
    return generated


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/seed_admin")
def seed_admin(db: Session = Depends(get_db)):
    if not db.query(User).filter(User.username == "admin").first():
        password = _get_seed_password()
        db.add(User(username="admin", password_hash=hash_password(password), is_admin=True))
        db.commit()
    return {"ok": True}
