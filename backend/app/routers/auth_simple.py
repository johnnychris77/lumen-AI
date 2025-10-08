from datetime import datetime, timedelta, timezone
from typing import Optional
import os, jwt
from fastapi import APIRouter, Form, HTTPException, Request, status
from pydantic import BaseModel
from passlib.hash import bcrypt
from sqlalchemy import create_engine, text

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")  # set a strong value in .env.prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
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
    with engine.begin() as conn:
        row = conn.execute(text("SELECT username, password_hash FROM users WHERE username=:u"), {"u": u}).fetchone()
        if not row:
            return None
        if not bcrypt.verify(password, row.password_hash):
            return None
        return row.username

@router.post("/login")
async def login(request: Request, username: Optional[str] = Form(None), password: Optional[str] = Form(None)):
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
    return {"access_token": token, "token_type": "bearer"}
