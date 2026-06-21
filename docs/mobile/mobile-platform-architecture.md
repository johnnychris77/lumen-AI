# Mobile Platform Architecture — P18

## Strategy: PWA-First, React Native as Phase 2

### Recommendation: Progressive Web App (PWA)

LumenAI adopts PWA as the primary mobile strategy for the following reasons:

- **No separate codebase**: PWA runs on the existing React frontend. No fork, no duplication.
- **Home screen installable**: iOS (Safari 16.4+) and Android support `Add to Home Screen` via the Web App Manifest.
- **Offline capability**: Service workers cache assets and queue mutations for background sync.
- **Camera & barcode APIs**: `MediaDevices.getUserMedia()` and `@zxing/browser` work in modern mobile browsers without app store approval.
- **Instant updates**: Deploying a new service worker version updates all installed clients on next visit — no App Store review cycle.
- **React Native path**: If Phase 2 requires native device APIs (USB, Bluetooth, background BLE scanning), a React Native wrapper can share business logic via a shared API layer.

---

## PWA Architecture

### manifest.json
```json
{
  "name": "LumenAI Inspection",
  "short_name": "LumenAI",
  "start_url": "/mobile",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1a1a2e",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### Service Worker
- **Registration**: `navigator.serviceWorker.register('/sw.js')`
- **Lifecycle**: Install → Activate → Fetch intercept
- **Cache name versioned**: `lumenai-v1` — bump version to force update

### Offline Cache Strategy

| Resource type        | Strategy              | Notes                                    |
|----------------------|-----------------------|------------------------------------------|
| Static assets (JS/CSS/fonts) | Cache-First  | Precached at install time                |
| API GET calls        | Network-First with fallback | Fallback to cached response if offline |
| API POST/PATCH/DELETE | Offline Queue        | Queued in IndexedDB, replayed on reconnect |
| Images (baseline)    | Cache-First with TTL  | 7-day max-age                            |

---

## Sync Model

1. **Optimistic local write**: Inspection data is written to IndexedDB immediately. UI shows the result without waiting for network.
2. **Background sync queue**: Mutations are added to a `sync_queue` store in IndexedDB. The Background Sync API (`SyncManager.register('inspection-sync')`) triggers `sync` events when connectivity is restored.
3. **Server reconciliation**: `POST /api/mobile/sessions/{id}/sync` merges offline findings into the main inspection record.
4. **Conflict resolution**:
   - AI findings (server-generated): **server wins** — never overwritten by client data.
   - Human annotations/notes: **last-write-wins** by `updated_at` timestamp comparison.
   - Images: client images are appended, never replaced.

---

## Offline Storage

| Storage              | Use case                                      | Limit          |
|----------------------|-----------------------------------------------|----------------|
| IndexedDB            | Inspection sessions, findings, sync queue     | Browser quota (~1GB typical) |
| IndexedDB (blobs)    | Captured images as base64 blobs               | 50MB cap enforced client-side |
| SQLite via OPFS      | Structured relational data (future)           | OPFS storage quota           |
| localStorage (encrypted) | Auth tokens, user preferences             | 5MB            |

Image blobs are stored as base64 in IndexedDB with a running size counter. When 50MB is reached, the UI prompts the user to sync before capturing more.

Auto-expiry: inspection sessions older than 7 days are purged from IndexedDB by the service worker's periodic sync handler.

---

## Authentication

- **Primary**: JWT stored in `HttpOnly` cookie (SSR path) or `localStorage` (SPA path, matching existing pattern).
- **Biometric**: WebAuthn API — `navigator.credentials.create({ publicKey: { authenticatorSelection: { authenticatorAttachment: "platform" } } })`. Stores credential ID in localStorage; private key never leaves the device secure enclave.
- **PIN fallback**: Delegates to device screen lock (no app-level PIN storage). Session requires re-auth after 8h.
- **Token lifetimes**: Access token = 8h, Refresh token = 30d.
- **Remote logout**: `POST /api/mobile/device-sessions/{id}/logout` sets `remote_logout_requested=True`; client checks this flag on next sync and clears local session.

---

## Security

- **Token expiration**: 8h access / 30d refresh.
- **Token revocation**: Server maintains a revocation list (Redis in production, DB table in dev). `GET /api/mobile/auth/check` validates against the revocation list.
- **Encrypted localStorage**: Sensitive values encrypted with SubtleCrypto AES-GCM. Key derived from device fingerprint + server-issued salt.
- **HTTPS only**: Service worker only registers on secure origins. HSTS enforced in production.
- **Permissions-Policy**: `camera=(), microphone=()` relaxed per-page for capture screens only.

---

## Camera Integration

```javascript
const stream = await navigator.mediaDevices.getUserMedia({
  video: {
    facingMode: "environment",  // rear camera preferred
    width: { ideal: 1920 },
    height: { ideal: 1080 }
  }
});
```

- Falls back to front camera if rear unavailable.
- Frame captured via `canvas.drawImage(video, ...)` then `canvas.toBlob(cb, 'image/jpeg', 0.85)` for compression.

---

## Barcode / QR / UDI Scanning

- **Client-side**: `@zxing/browser` `BrowserMultiFormatReader` decodes from video frame in real time.
- **Server fallback**: `POST /api/mobile/scan/decode` with `image_base64` for cases where client decode fails (low-end devices, complex UDI).
- **UDI parsing**: GS1 Application Identifiers — AI 01 = GTIN-14, AI 21 = serial number.

---

## KeyDot

KeyDot images are captured via camera and POSTed to `POST /api/mobile/scan/decode` with `scan_type=keydot`. Decode is server-side only (proprietary pattern matching). Response includes `decoded_value` and `confidence_score`.

---

## React Native Phase 2

If Phase 2 requires:
- USB borescope enumeration (WebUSB not universally supported)
- Background BLE scanning
- Native push notifications (APNs/FCM direct)

...then a React Native shell can be introduced. The PWA API layer (`/api/mobile/*`) is already the contract. The React Native app calls the same endpoints. Shared business logic lives in the API, not the client.
