# LumenAI JWT Authentication Engineering Design v1

## Status

Ready for implementation.

## Purpose

This document defines the engineering design for adding JWT authentication support to the LumenAI backend.

## Proposed Backend Files

Recommended files:

- `backend/app/core/auth_config.py`
- `backend/app/core/jwt_auth.py`
- `backend/app/core/principal.py`
- `backend/tests/test_jwt_auth_baseline.py`

## Environment Variables

Recommended variables:

- `AUTH_MODE`
- `ENABLE_DEV_AUTH`
- `JWT_ISSUER`
- `JWT_AUDIENCE`
- `JWT_ALGORITHM`
- `JWT_SECRET`
- `JWT_PUBLIC_KEY`

## Principal Shape

Recommended authenticated principal:

```python
{
    "user_id": "user_123",
    "email": "user@example.com",
    "tenant_id": "tenant_123",
    "roles": ["customer_admin"],
    "auth_mode": "jwt"
}
