from fastapi import APIRouter, Form, HTTPException, Request, status
from pydantic import BaseModel

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "viewer"


@router.post("/api/auth/login", response_model=Token)
async def login(
    request: Request,
    username: str = Form(default=None),
    password: str = Form(default=None),
    grant_type: str = Form(default="password"),
):
    """Delegates to the real auth router (/auth/login) which validates credentials."""
    user = username
    pwd = password

    if not (user and pwd):
        try:
            data = await request.json()
            user = data.get("username") or data.get("email")
            pwd = data.get("password")
        except Exception:
            pass

    if not user or not pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required",
        )

    # Delegate to auth_simple's verification logic
    try:
        from app.routers.auth_simple import _verify_user, _make_token, _user_role
        valid = _verify_user(user, pwd)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        return Token(access_token=_make_token(valid), role=_user_role(valid))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
