# Offline Sync Design — P18

## IndexedDB Schema

### Object Store: `inspection_sessions`
```
keyPath: session_id (string UUID)
indexes: [tenant_id, sync_status, started_at_device]
fields: session_id, tenant_id, facility_id, technician_id, device_id,
        instrument_id, tray_id, inspection_type, started_at_device,
        completed_at_device, sync_status, offline_findings (array),
        offline_capa_notes, image_count, created_at, updated_at
```

### Object Store: `sync_queue`
```
keyPath: queue_id (string UUID, auto-generated)
indexes: [tenant_id, status, payload_type]
fields: queue_id, tenant_id, session_id, device_id, payload_type,
        payload_json, status (pending/processing/completed/failed),
        retry_count, next_retry_at, queued_at, processed_at
```

### Object Store: `image_blobs`
```
keyPath: image_id (string UUID)
indexes: [capture_session_id]
fields: image_id, capture_session_id, image_base64, size_bytes,
        sha256, image_type, annotation, captured_at, expires_at
```

### Object Store: `notifications_cache`
```
keyPath: notification_id
indexes: [tenant_id, read_status]
fields: notification_id, title, body, priority, read_status, created_at, expires_at
```

---

## Service Worker Caching Strategy

### Cache-First (static assets)
Assets precached at service worker install time:
```javascript
const PRECACHE = [
  '/', '/index.html', '/mobile', '/static/js/main.js', '/static/css/main.css',
  '/manifest.json', '/icons/icon-192.png', '/icons/icon-512.png'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open('lumenai-v1').then(c => c.addAll(PRECACHE)));
});
```

### Network-First (API GETs)
```javascript
self.addEventListener('fetch', event => {
  if (event.request.url.includes('/api/') && event.request.method === 'GET') {
    event.respondWith(
      fetch(event.request)
        .then(res => { cache.put(event.request, res.clone()); return res; })
        .catch(() => caches.match(event.request))
    );
  }
});
```

### Offline Queue (mutations)
All POST/PATCH/DELETE requests when offline are intercepted:
```javascript
if (!navigator.onLine && ['POST','PATCH','DELETE'].includes(event.request.method)) {
  await addToSyncQueue(event.request);
  return new Response(JSON.stringify({ queued: true }), { status: 202 });
}
```

---

## Sync Conflict Resolution Rules

| Data type              | Rule                     | Rationale                                           |
|------------------------|--------------------------|-----------------------------------------------------|
| AI inspection findings | Server wins              | AI results are authoritative; client cannot override|
| Human annotations      | Last-write-wins          | Compare `updated_at`; higher timestamp wins         |
| CAPA notes             | Last-write-wins          | Same as annotations                                 |
| Images                 | Append (no conflict)     | Images are additive; never deleted on merge         |
| Sync status            | Server is authoritative  | Client reflects server state after sync             |

---

## Background Sync API

```javascript
// Register sync tag when connectivity returns
navigator.serviceWorker.ready.then(sw => {
  sw.sync.register('inspection-sync');
});

// Service worker handles the sync event
self.addEventListener('sync', event => {
  if (event.tag === 'inspection-sync') {
    event.waitUntil(processSyncQueue());
  }
});

async function processSyncQueue() {
  const items = await db.getAll('sync_queue', IDBKeyRange.only('pending'));
  for (const item of items) {
    try {
      await fetch(item.url, { method: item.method, body: item.payload_json, headers: item.headers });
      await db.put('sync_queue', { ...item, status: 'completed' });
    } catch {
      await scheduleRetry(item);
    }
  }
}
```

---

## Queue Retry with Exponential Backoff

Retry delays: 2s → 4s → 8s → 16s → 32s (max 5 retries)

```javascript
async function scheduleRetry(item) {
  const delays = [2000, 4000, 8000, 16000, 32000];
  const delay = delays[Math.min(item.retry_count, delays.length - 1)];
  if (item.retry_count >= 5) {
    await db.put('sync_queue', { ...item, status: 'failed' });
    return;
  }
  await db.put('sync_queue', {
    ...item,
    retry_count: item.retry_count + 1,
    next_retry_at: Date.now() + delay,
    status: 'pending'
  });
}
```

---

## Image Compression Before Upload

Images are compressed before being stored or uploaded using the Canvas API:

```javascript
async function compressImage(file, targetQuality = 0.85) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      canvas.getContext('2d').drawImage(img, 0, 0);
      canvas.toBlob(blob => {
        URL.revokeObjectURL(url);
        resolve(blob);
      }, 'image/jpeg', targetQuality);
    };
    img.src = url;
  });
}
```

Target: < 2MB per image at quality=0.85. If still > 2MB, scale resolution down 50% and retry.
