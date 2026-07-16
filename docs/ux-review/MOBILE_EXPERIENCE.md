# LumenAI — Mobile Experience

Objective 8 review. Covers tablet/workstation/large-display support, touch interaction, responsive layout, barcode scanners, and camera integration, grounded in what the frontend actually implements today.

## Responsive breakpoint usage — real but shallow and inconsistent

Tailwind responsive prefixes (`sm:`/`md:`/`lg:`/`xl:`) appear in **88 of 197 `.tsx` files (~45%)**, concentrated in a handful of files (`OracleWorkspace.tsx` 12 hits, `NewInspectionPage.tsx` 10, `GlobalInfrastructureConsole.tsx` 9, `PulseCommandCenterDashboard.tsx` 8). More than half the files use zero responsive prefixes. Where breakpoints are used, they're usually a single `grid-cols-N md:grid-cols-M` collapse rather than a systematic mobile-first design.

- `Dashboard.tsx` — grids collapse at breakpoints (`grid-cols-2 lg:grid-cols-4`), but the base case is already 2-up, not 1-up, so a phone-width viewport still renders 2 columns for several sections. Its results table falls back to `overflow-x-auto` (horizontal scroll) rather than a redesigned mobile layout.
- `NewInspectionPage.tsx` — the most responsive-aware page sampled: grids consistently use `grid-cols-1 sm:grid-cols-2/3/4`, i.e. genuinely stack to a single column below `sm`.
- `OracleWorkspace.tsx` — also single-column-first, expanding at `md`.

**Overall**: adaptivity exists but is inconsistent and shallow. No container queries, no evidence of a mobile-first design system, and most of the "Console"/"Center" dashboard pages (the majority not in the breakpoint-using set) are effectively fixed desktop-grid layouts with no small-screen consideration.

## The "Pulse mobile view" is not a distinct mobile UI

There is no dedicated mobile page or component. `components/PulseCommandCenterDashboard.tsx`'s own header comment states this plainly: *"Responsive grid classes (`grid-cols-1 md:grid-cols-*`) throughout serve as the Pulse Mobile View (Section 13) — no separate mobile app or framework exists in this codebase to extend, so a responsive layout of the same real data is the mobile experience."* It is the same nine-tab desktop command center with a handful of `md:` breakpoints — no touch-optimized layout, no simplified widget set, no separate mobile route or bundle.

## A real backend mobile API has zero frontend consumer

`backend/app/routes/mobile.py` (792 lines), `backend/app/services/mobile_service.py`, and `backend/app/models/mobile.py` implement a substantial, separate mobile API surface: offline inspection sessions, session sync, scan-decode, image upload, and a mobile dashboard endpoint. **A repo-wide search for `/api/mobile` in `frontend/src` returns zero matches.** This is a real, citable gap — a fairly complete offline/mobile backend exists today with no UI built against it at all.

## Camera integration — two real, distinct mechanisms

1. **Live in-browser video stream** via `getUserMedia`: `ui/barcode-scanner.tsx` (opens a rear-facing camera stream, and if the browser's native `BarcodeDetector` API is available, polls it for decode results — Chromium-only, no polyfill for Firefox/Safari, falling back to manual text entry), and `pages/CapturePage.tsx`/`pages/StationPage.tsx` (same pattern for live borescope/USB video feeds with a device selector).
2. **Native OS file-picker**: `InspectionImageUploadPage.tsx`/`BaselineImageUploadPage.tsx` use a plain `<input type="file" accept="image/*" multiple>` with **no `capture=` attribute** — so on mobile this opens the OS's standard chooser (camera or library), not a forced straight-to-camera flow. Both upload pages offer a `"mobile_camera"` dropdown option as a metadata/provenance tag only — it does not change how the picker behaves.

## Barcode/QR scanning — real, but narrow

`ui/barcode-scanner.tsx` is a genuine modal scanning component supporting `qr_code`/`code_128`/`code_39`/`ean_13`/`ean_8`/`data_matrix`/`pdf417` via the browser's native `BarcodeDetector` API — used in exactly one place, `VendorIntake.tsx`, whose own UI copy warns: *"Requires Chrome 83+ or Edge."* No fallback decoder exists for Safari/Firefox. Separately, the backend ships a real `pyzbar`-based decode capability (`mobile.py`'s `mobile.scan.decode`) with **no frontend caller** — consistent with the broader "mobile API has no consumer" finding above.

`barcode_qr_keydot` in `Dashboard.tsx`'s `CATEGORY_LABELS` is confirmed to be an unrelated concept — a detected CV finding-category label, not an input/scanning mechanism. Both the real scanner component and this label legitimately coexist in the codebase without being the same thing.

## Touch-specific interaction — absent

A repo-wide search for `onTouchStart`/`onTouchEnd`/`onTouchMove`/`touch-` returns **zero matches**, and no swipe/gesture library appears in `frontend/package.json`. There is no touch-gesture handling anywhere in the frontend — all interaction is mouse/click-based, relying on the browser's default touch-to-click translation. Button/tap-target sizing (`text-xs`, `px-3 py-1.5`) is identical regardless of viewport — no evidence of touch-target enlargement for smaller/touch devices.

## Recommendation

1. **Either build a frontend for the existing mobile API, or explicitly scope it out** — a substantial offline/sync backend with zero UI consumer is either wasted investment or a near-term roadmap item; this review can't tell which was intended, but the gap should be a deliberate decision, not an oversight.
2. **Extend the `capture=` attribute** on the two image-upload inputs so mobile users get a direct camera shortcut rather than the generic OS picker, matching the "reduce clicks" spirit of Objective 2.
3. **No touch-gesture work is urgent** — this app's interaction model (forms, tables, buttons) does not obviously need swipe gestures; native tap-to-click is a reasonable baseline. The barcode scanner's Chromium-only limitation is the one real cross-browser gap worth prioritizing, since `VendorIntake.tsx` explicitly tells non-Chromium users the feature won't work.
