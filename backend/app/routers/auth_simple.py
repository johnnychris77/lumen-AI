from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import time
import threading
import logging
import jwt
from fastapi import APIRouter, Form, HTTPException, Request, status
from pydantic import BaseModel
from passlib.hash import bcrypt
from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)

_rate_lock = threading.Lock()
_rate_buckets: dict[str, tuple[int, float]] = {}  # ip → (count, window_start)
_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "10"))
_RATE_WINDOW = 60.0  # seconds


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        count, window_start = _rate_buckets.get(ip, (0, now))
        if now - window_start >= _RATE_WINDOW:
            count, window_start = 0, now
        count += 1
        _rate_buckets[ip] = (count, window_start)
    if count > _RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

SECRET_KEY = os.getenv("SECRET_KEY") or ""
if not SECRET_KEY:
    _env = os.getenv("APP_ENV", "development").strip().lower()
    if _env in {"production", "prod"}:
        raise RuntimeError("SECRET_KEY environment variable must be set in production.")
    SECRET_KEY = "dev-only-secret-not-for-production"
ALGORITHM = "HS256"
# Default shortened from 480 (8h) to 60: there is no refresh/revocation flow,
# so a leaked token stays valid for its full lifetime. Override per-deploy via
# ACCESS_TOKEN_EXPIRE_MINUTES if a longer session is explicitly needed.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
router = APIRouter(prefix="/auth", tags=["auth"])

class LoginJSON(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

def _make_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "iat": int(now.timestamp()),
               "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _verify_user(u: str, password: str) -> Optional[str]:
    """Legacy users-table password login — DISABLED (P472-03 B5.5).

    This used to query ``users.username`` / ``users.password_hash``. The
    canonical ``users`` table (ORM ``app.models.user.User``; Alembic baseline
    ``4b336d3ed612``) has ``email`` / ``hashed_password``, so the query raised on
    every call and the caller turned that into 401: this path has never
    authenticated anyone against the canonical schema, and no mounted code
    creates ``users`` rows. Making it work would add an unreviewed credential
    source, so it stays closed — explicitly and visibly — until the
    authentication owner decides otherwise (decision AUTH-1). Login through
    ``admin_credentials`` (``/api/auth/login``) is unaffected.
    """
    logger.warning(
        "legacy users-table password login is disabled (AUTH-1 pending); refused login for an account "
        "not found in admin_credentials",
    )
    return None


def _role_from(conn, sql: str, identity: str) -> Optional[str]:
    """One role source; exact-case match wins, disagreeing case variants are ambiguous."""
    rows = conn.execute(text(sql), {"u": identity}).fetchall()
    if not rows:
        return None
    exact = [r.role for r in rows if r.ident == identity and r.role]
    if exact:
        return exact[0]
    roles = {r.role for r in rows if r.role}
    if len(roles) == 1:
        return roles.pop()
    if roles:
        logger.warning("role lookup is ambiguous for a principal (case-variant rows with different roles); "
                       "failing closed to viewer")
        raise _AmbiguousRole()
    return None


class _AmbiguousRole(Exception):
    pass


_ROLE_SOURCES = (
    # Admin-managed assignments (User Management UI / bootstrap) — the source of truth.
    ("user_role_assignments",
     "SELECT username AS ident, role FROM user_role_assignments WHERE LOWER(username) = LOWER(:u)"),
    # Canonical users table: the principal's identity is its email (B5.5; was users.username).
    ("users", "SELECT email AS ident, role FROM users WHERE LOWER(email) = LOWER(:u)"),
)


def _user_role(username: str) -> str:
    """Stored role of an AUTHENTICATED principal (the validated JWT ``sub`` /
    the username just verified at login — never a client-supplied identity).

    Resolution order: role assignment table → ``users.role`` (by email) →
    ``viewer``. Fail closed to ``viewer`` (least privilege) on an ambiguous
    identity or any database error — and LOG the error, so a broken lookup is
    no longer indistinguishable from "no role" (P472-03 B5.5).
    """
    identity = (username or "").strip()
    if not identity:
        return "viewer"
    for source, sql in _ROLE_SOURCES:
        try:
            with engine.begin() as conn:
                role = _role_from(conn, sql, identity)
        except _AmbiguousRole:
            return "viewer"
        except Exception:
            logger.warning("role lookup in %s failed; failing closed to viewer", source, exc_info=True)
            return "viewer"
        if role:
            return role
    return "viewer"

@router.post("/login")
async def login(request: Request, username: Optional[str] = Form(None), password: Optional[str] = Form(None)):
    _check_rate_limit(request.client.host if request.client else "unknown")
    user = username
    pwd = password
    if not (user and pwd):
        # try JSON body too
        try:
            data = await request.json()
            lj = LoginJSON(**data)
            user = lj.username or lj.email
            pwd = lj.password
        except Exception:
            pass

    if not user or not pwd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")

    valid = _verify_user(user, pwd)
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = _make_token(valid)
    return {"access_token": token, "token_type": "bearer", "role": _user_role(valid)}
