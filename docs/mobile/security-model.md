# Mobile Security Model — P18

## Authentication

### Biometric (WebAuthn)
```javascript
// Registration
const credential = await navigator.credentials.create({
  publicKey: {
    challenge: serverChallenge,
    rp: { name: "LumenAI", id: window.location.hostname },
    user: { id: userId, name: userEmail, displayName: userName },
    pubKeyCredParams: [{ type: "public-key", alg: -7 }],  // ES256
    authenticatorSelection: {
      authenticatorAttachment: "platform",  // device biometric (Face ID, Touch ID, Windows Hello)
      requireResidentKey: false,
      userVerification: "required"
    },
    timeout: 60000
  }
});
// Store credential.id in localStorage; private key never leaves device secure enclave
```

```javascript
// Authentication
const assertion = await navigator.credentials.get({
  publicKey: {
    challenge: serverChallenge,
    allowCredentials: [{ type: "public-key", id: storedCredentialId }],
    userVerification: "required"
  }
});
// Send assertion to POST /api/mobile/auth/webauthn/verify
```

### PIN Fallback
- No app-level PIN storage. Delegates to device screen lock.
- If device has screen lock enabled, iOS/Android enforce PIN/biometric before unlocking.
- Session re-auth required after 8h regardless of device lock state.

---

## Token Lifecycle

| Token type    | Expiry | Storage                   | Renewal                              |
|---------------|--------|---------------------------|--------------------------------------|
| Access token  | 8h     | localStorage (encrypted)  | POST /api/mobile/auth/token-refresh  |
| Refresh token | 30d    | HttpOnly cookie           | Rotate on use                        |

### Token Refresh Flow
1. Client detects access token expiry (checks `exp` claim before each request).
2. `POST /api/mobile/auth/token-refresh` with refresh token in cookie.
3. Server validates refresh token against revocation list.
4. Returns new access token (8h) and rotated refresh token (30d).

---

## Encrypted Local Storage

Sensitive values (tokens, cached PII) encrypted with AES-GCM via SubtleCrypto:

```javascript
async function encryptValue(plaintext, keyMaterial) {
  const key = await crypto.subtle.importKey(
    'raw', keyMaterial, { name: 'AES-GCM' }, false, ['encrypt']
  );
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(plaintext));
  return { iv: Array.from(iv), data: Array.from(new Uint8Array(encrypted)) };
}
```

Key derivation: PBKDF2 from device fingerprint (navigator.userAgent + screen dimensions + timezone) + server-issued salt. Salt rotates every 30 days.

---

## Remote Logout

1. Admin calls `POST /api/mobile/device-sessions/{device_session_id}/logout`.
2. Server sets `remote_logout_requested=True`, `is_active=False`.
3. Server adds access token to revocation list (Redis key with TTL matching token expiry).
4. On next API call, `GET /api/mobile/auth/check` returns 401.
5. Client detects 401, clears local session, redirects to login.

---

## Remote Wipe

1. Admin calls `POST /api/mobile/device-sessions/{device_session_id}/wipe`.
2. Server sets `remote_wipe_requested=True`.
3. On next sync, client checks `remote_wipe_requested` flag.
4. Client clears all IndexedDB stores (`inspection_sessions`, `sync_queue`, `image_blobs`, `notifications_cache`).
5. Client clears encrypted localStorage.
6. Client signs out and redirects to login.

```javascript
// Client-side wipe check on sync response
if (syncResponse.remote_wipe_requested) {
  await clearAllLocalData();
  await signOut();
}
```

---

## Offline Data Expiry

Cached inspection data auto-expires after 7 days in IndexedDB:

```javascript
// Service worker periodic sync (requires PeriodicSync API)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'expire-offline-data') {
    event.waitUntil(purgeExpiredData());
  }
});

async function purgeExpiredData() {
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const db = await openDB();
  const sessions = await db.getAll('inspection_sessions');
  for (const s of sessions) {
    if (new Date(s.created_at).getTime() < cutoff && s.sync_status === 'SYNCED') {
      await db.delete('inspection_sessions', s.session_id);
    }
  }
}
```

---

## Security Controls Summary

| Control                | Implementation                                    |
|------------------------|---------------------------------------------------|
| Authentication         | JWT + WebAuthn biometric + device PIN fallback    |
| Token storage          | Encrypted localStorage (AES-GCM SubtleCrypto)    |
| Token expiry           | Access: 8h / Refresh: 30d                        |
| Token revocation       | Server-side revocation list (Redis/DB)           |
| Transport security     | HTTPS + HSTS (max-age=63072000)                  |
| Remote logout          | Server flag + revocation list                    |
| Remote wipe            | Client clears all local data on next sync         |
| Offline data lifetime  | 7 days, auto-purged by periodic sync              |
| Tenant isolation       | All queries filtered by tenant_id from JWT        |
| Audit trail            | Every action logged to audit_events table         |
