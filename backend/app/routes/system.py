from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    """
    Simple healthcheck for edge / k8s / docker.
    """
    return {"status": "ok"}


@router.post("/auth/login")
async def login(request: Request):
    """
    Real login: validate credentials, return a signed JWT and the user's role.

    Replaces a previous stub that handed out a hardcoded "dev-token" with no
    role — which left every user stuck as "viewer" and the token unable to
    authenticate role-gated endpoints. Accepts JSON {username|email, password}
    or form-encoded credentials.
    """
    username = None
    password = None

    # JSON body (what the frontend sends)
    try:
        data = await request.json()
        if isinstance(data, dict):
            username = data.get("username") or data.get("email")
            password = data.get("password")
    except Exception:
        pass

    # Form-encoded fallback (OAuth2-style clients)
    if not (username and password):
        try:
            form = await request.form()
            username = username or form.get("username")
            password = password or form.get("password")
        except Exception:
            pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required",
        )

    from app.routers.auth_simple import _verify_user, _make_token, _user_role

    # Emails/usernames are matched case-insensitively — "Jane@Hospital.org" at
    # bootstrap time must still work when typed "jane@hospital.org" at login.
    username_normalized = username.strip().lower()

    # 1) Validate against the self-managed admin credential table (founder bootstrap).
    try:
        from passlib.hash import bcrypt
        from sqlalchemy import func
        from app.db.session import SessionLocal
        from app.models.admin_credential import AdminCredential

        db = SessionLocal()
        try:
            # Prefer an exact-case match first — if a case-only duplicate row
            # ever exists (e.g. from data predating this case-insensitive
            # lookup), a case-folded `.first()` could pick either row
            # nondeterministically and check the wrong password hash.
            candidates = (
                db.query(AdminCredential)
                .filter(func.lower(AdminCredential.username) == username_normalized)
                .order_by(AdminCredential.id.asc())
                .all()
            )
            cred = next((c for c in candidates if c.username == username), None) or (
                candidates[0] if candidates else None
            )
            if cred and bcrypt.verify(password, cred.password_hash):
                return {
                    "access_token": _make_token(cred.username),
                    "token_type": "bearer",
                    "role": _user_role(cred.username),
                }
        finally:
            db.close()
    except Exception:
        # Credential table unavailable — fall through to legacy validation.
        pass

    # 2) Legacy users-table validation (defensive — schema may be absent).
    try:
        valid = _verify_user(username, password)
    except Exception:
        valid = None

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return {
        "access_token": _make_token(valid),
        "token_type": "bearer",
        "role": _user_role(valid),
    }


@router.get("/reviews/queue")
async def reviews_queue():
    """
    Stubbed queue endpoint for pending inspections.

    Later we can wire this into the inspections table (or a dedicated
    review queue table). For now it just returns an empty list.
    """
    return {"items": []}
