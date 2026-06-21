# Notification Framework — P18

## Notification Types and Priority Matrix

| Type                  | Default Priority | Action Required | Delivery Channel |
|-----------------------|------------------|-----------------|------------------|
| `capa_assignment`     | high             | Yes             | in_app + push    |
| `recall_alert`        | critical         | Yes             | all              |
| `quality_alert`       | high             | No              | in_app + push    |
| `safety_alert`        | critical         | Yes             | all              |
| `inspection_failure`  | high             | Yes             | in_app + push    |
| `executive`           | normal           | No              | in_app           |

---

## Delivery Channels

### in_app
- Notification stored in `mobile_notifications` DB table.
- Client polls `GET /api/mobile/notifications` every 30 seconds.
- Or receives via Server-Sent Events at `GET /api/mobile/notifications/stream` (future).
- Badge count shown on mobile nav icon.

### push (Web Push API)
- Requires VAPID key pair (server-generated, stored as env vars `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`).
- Client subscribes:
```javascript
const subscription = await swReg.pushManager.subscribe({
  userVisibleOnly: true,
  applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
});
await fetch('/api/mobile/device-sessions/push-subscribe', {
  method: 'POST', body: JSON.stringify({ subscription })
});
```
- Service worker receives push event:
```javascript
self.addEventListener('push', event => {
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/badge-72.png',
      data: { action_url: data.action_url }
    })
  );
});
```
- Notification click routes to `action_url`.

### email
- Future delivery channel. Would use SendGrid or SES via background worker.

---

## In-App Polling

Default polling interval: 30 seconds.

```javascript
const POLL_INTERVAL = 30_000;
async function pollNotifications() {
  const res = await fetch('/api/mobile/notifications?read_status=unread', {
    headers: { Authorization: `Bearer ${getToken()}` }
  });
  const { notifications, total } = await res.json();
  updateBadge(total);
  renderNotifications(notifications);
}
setInterval(pollNotifications, POLL_INTERVAL);
```

## Server-Sent Events (Future)

```
GET /api/mobile/notifications/stream
Accept: text/event-stream
```

Each event:
```
event: notification
data: {"notification_id": "...", "title": "...", "priority": "high"}
```

---

## VAPID Key Setup

```bash
# Generate VAPID keys (one-time, store in secrets manager)
npx web-push generate-vapid-keys

# Set env vars
VAPID_PUBLIC_KEY=BM...
VAPID_PRIVATE_KEY=abc...
VAPID_SUBJECT=mailto:platform@lumenai.com
```
