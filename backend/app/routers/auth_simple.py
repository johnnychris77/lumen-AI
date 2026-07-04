from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import time
import threading
import jwt
from fastapi import APIRouter, Form, HTTPException, Request, status
from pydantic import BaseModel
from passlib.hash import bcrypt
from sqlalchemy import create_engine, text

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
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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
    # Case-insensitive match — an email typed with different capitalization
    # than it was stored with must still authenticate.
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT username, password_hash FROM users WHERE LOWER(username)=LOWER(:u)"),
            {"u": u.strip()},
        ).fetchone()
        if not row:
            return None
        if not bcrypt.verify(password, row.password_hash):
            return None
        return row.username


def _user_role(username: str) -> str:
    """Return the stored role for a user so the frontend gets the real role,
    not a hard-coded 'viewer' default.

    Resolution order: admin-managed role assignment table → users.role column →
    'viewer'. The assignment table is the source of truth for roles granted via
    the User Management UI / bootstrap.
    """
    normalized = username.strip()
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT role FROM user_role_assignments WHERE LOWER(username)=LOWER(:u)"),
                {"u": normalized},
            ).fetchone()
            if row and row.role:
                return row.role
    except Exception:
        pass
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT role FROM users WHERE LOWER(username)=LOWER(:u)"), {"u": normalized}
            ).fetchone()
            if row and row.role:
                return row.role
    except Exception:
        pass
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
