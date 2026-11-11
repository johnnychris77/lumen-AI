import os

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.authz import require_roles

router = APIRouter(tags=["system"])


def _deployed_commit() -> str:
    """The git commit this process is running, for deployment verification.
    Render sets RENDER_GIT_COMMIT automatically; GIT_COMMIT/SOURCE_COMMIT/
    BUILD_MAIN_SHA are honored as fallbacks. 'unknown' when none is set."""
    return (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("GIT_COMMIT")
        or os.getenv("SOURCE_COMMIT")
        or os.getenv("BUILD_MAIN_SHA")
        or "unknown"
    )


@router.get("/health")
async def health(request: Request):
    """Healthcheck for edge / k8s / docker — and the Render deploy health gate
    (``render.yaml`` healthCheckPath = /api/health).

    - ``git_commit`` lets an operator confirm which commit production is actually
      running (e.g. that a merge reached the backend) without dashboard access.
    - ``schema_ok`` reports the startup schema-bootstrap outcome TRUTHFULLY: when
      a required table/column for the baseline-image comparison is missing (a
      failed or partial bootstrap), ``status`` is ``"degraded"``, never ``"ok"``
      — so this check can never certify readiness while the app would silently
      serve "no comparison performed". HTTP stays 200 so the deploy is still
      observable (crashing startup instead black-holes the deploy and keeps the
      stale build live). Only sanitized issue labels are exposed; full
      exceptions stay in the logs.
    """
    schema_ok = bool(getattr(request.app.state, "schema_ok", True))
    body = {
        "status": "ok" if schema_ok else "degraded",
        "git_commit": _deployed_commit(),
        "schema_ok": schema_ok,
    }
    if not schema_ok:
        body["schema_issues"] = list(getattr(request.app.state, "schema_issues", []))
    return body


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


@router.get("/v1/system/inference-status")
async def inference_status(current_user=Depends(require_roles("admin"))):
    """Live status of the inspection-scoring inference pipeline.

    Admin-only: this reports whether the deployment is currently running a
    trained CV model or the deterministic placeholder (see
    app.ai.inference.PRODUCTION_INFERENCE_MODE and
    app.services.baseline_comparison_scoring_service.PRODUCTION_INFERENCE_MODE),
    which is operationally sensitive information.

    Note: this system's RBAC has no distinct "superuser" role -- "admin" is
    its highest-privilege role, so that's what gates this endpoint.
    """
    from app.ai.inference_status import get_inference_status
    return get_inference_status()
