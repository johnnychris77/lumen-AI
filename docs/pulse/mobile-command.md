# Project Pulse — Mobile Command Center

LumenAI OS v4.2 — Section 13

## A responsive layout of the same real data, not a separate app

Confirmed before writing any frontend code: no responsive/mobile-
detection framework exists anywhere in `frontend/src` (only incidental
uses of the word "mobile" in unrelated filenames), and the only
mobile-specific backend model (`app/models/mobile.py`) covers offline
inspection sessions and barcode scan results — unrelated to a command
center. Building a genuinely separate mobile application (a second
frontend, a native app, or a device-detection routing layer) would be a
large, disproportionate undertaking for what Section 13 actually asks
for: "responsive command center" support for Director/Manager/
Supervisor/Executive roles with real-time notifications.

`PulseCommandCenterDashboard.tsx` is therefore built responsively from
the start — every widget grid uses Tailwind's responsive classes
(`grid-cols-1 sm:grid-cols-2 md:grid-cols-4`, etc.), so the same
component and the same API endpoints serve both desktop and mobile
viewports without a second implementation to maintain.

## Per-device layout personalization

`PulseDashboardLayout.is_mobile_layout` (Section 12's widget
personalization, extended) lets a user save a different widget
arrangement for their mobile viewport than their desktop one —
`GET /api/pulse/dashboard-layout?is_mobile=true` / `POST
/api/pulse/dashboard-layout` with `{"is_mobile": true, "layout": [...]}`.

## Real-time notifications

Mobile users receive the same unified notification feed every other
Pulse surface uses (`GET /api/pulse/notifications`,
`platform_notification_service.unified_notifications` under the hood)
— no separate mobile push-notification infrastructure was built, since
none exists in this codebase to extend and building one (APNs/FCM
integration) is outside this sprint's real scope. The existing
`MobileNotification` model (`app/models/mobile.py`) remains available
for a future native-push integration; this sprint composes it into the
same unified feed rather than adding a parallel mobile-only channel.
