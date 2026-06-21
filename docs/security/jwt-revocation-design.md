# JWT Revocation Design

**Status:** Recommended — not yet implemented  
**Scope:** LumenAI backend (`app/auth/`, `app/enterprise_auth.py`)  
**Date:** 2026-06-20

---

## Problem

JWTs are stateless by design. Once issued, a valid token cannot be invalidated before its
expiry without additional infrastructure. This creates risk in several scenarios:

- User logs out but the token remains valid for up to the `exp` window
- Admin disables a compromised account mid-session
- Stolen token discovered after issuance
- Role change needs to take effect immediately

---

## Recommended Approach

### 1. Short-Lived Access Tokens

Set `exp` to **15 minutes** in the OIDC provider. This bounds the exposure window without
requiring server-side state for routine use.

```
OIDC provider config:
  access_token_lifetime: 900   # 15 minutes
  refresh_token_lifetime: 86400  # 24 hours (rotating)
```

### 2. Refresh Token Rotation

Pair short-lived access tokens with rotating refresh tokens. Each refresh issues a new
access token and a new refresh token; the old refresh token is invalidated. This limits
replay attacks even if a refresh token is leaked.

Implemented at the OIDC provider (Auth0, Keycloak, etc.) — no backend changes required.

### 3. Redis-Backed Deny-List (Emergency Revocation)

For immediate revocation (logout, account disable, breach response), maintain a Redis
set of revoked JTI (JWT ID) values.

**Schema:**
```
Key:   jti_denylist:{jti}
Value: "1"
TTL:   equal to token's remaining lifetime (exp - now)
```

**Validation hook in `validate_jwt_signature_with_jwks`:**
```python
jti = claims.get("jti")
if jti and redis_client.exists(f"jti_denylist:{jti}"):
    raise JWKSSignatureValidationError("Token has been revoked.")
```

**Revocation write (logout endpoint):**
```python
remaining_ttl = max(0, int(claims["exp"] - time.time()))
redis_client.setex(f"jti_denylist:{jti}", remaining_ttl, "1")
```

**Requirements:**
- OIDC provider must include `jti` claim in access tokens (most do by default)
- Redis instance available to the backend (already present in the deployment stack)
- `REDIS_URL` env var already in use for the job queue

**Operational notes:**
- Deny-list entries self-expire via Redis TTL — no cleanup job needed
- Redis unavailability should **fail open** with a log warning (don't block all auth on
  Redis downtime); or **fail closed** for high-security deployments (configurable)
- Deny-list only needs to cover the access token lifetime window (≤ 15 min per above)

### 4. Logout Behavior

```
POST /auth/logout
  - Validate bearer token (must be a valid, non-expired token)
  - Extract jti from verified claims
  - Write jti to deny-list with TTL = remaining lifetime
  - Return 204 No Content
```

Frontend responsibility: clear the access and refresh tokens from storage on 204.

### 5. Admin Disable-User Behavior

When an admin disables a user account:
1. Mark `user.is_active = False` in the database (already prevents new logins)
2. Query active sessions for the user (if session tracking exists) or:
3. Revoke by `sub` claim: maintain a separate `sub_denylist:{sub}` key with TTL equal to
   the maximum token lifetime — less precise but simpler than per-JTI tracking

For the `sub`-based approach:
```python
# On disable
redis_client.setex(f"sub_denylist:{user.sub}", 900, "1")  # 15-min TTL

# In validate_jwt_signature_with_jwks (after signature check)
sub = claims.get("sub", "")
if sub and redis_client.exists(f"sub_denylist:{sub}"):
    raise JWKSSignatureValidationError("User account has been disabled.")
```

---

## Implementation Checklist

- [ ] Add `jti` claim requirement to `validate_jwt_signature_with_jwks` options
- [ ] Implement `POST /auth/logout` endpoint with deny-list write
- [ ] Add deny-list check in `validate_jwt_signature_with_jwks` (after signature verification)
- [ ] Add `REDIS_DENYLIST_ENABLED` env flag (default `false`) for gradual rollout
- [ ] Write unit tests for: revoked JTI rejected, expired deny-list entry ignored, Redis-down fail-open behavior
- [ ] Configure OIDC provider: 15-min access token, rotating refresh token, `jti` included

---

## Risks and Assumptions

| Risk | Mitigation |
|------|-----------|
| Redis unavailability blocks all authentication | Fail-open mode (log + allow) is default; configurable |
| Deny-list grows unbounded | Redis TTL auto-expires entries; no separate sweep needed |
| OIDC provider omits `jti` | Validate at startup; raise config error if `jti` absent and deny-list is enabled |
| Short token lifetime degrades UX | Transparent refresh via frontend SDK (standard pattern) |
