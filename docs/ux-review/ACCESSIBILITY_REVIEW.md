# LumenAI — Accessibility Review

Objective 9 review. States real gaps plainly rather than claiming a compliance level that hasn't been verified, consistent with this repository's established review discipline. All figures below are from a direct audit of `frontend/src/` (~204 TS/TSX files, ~49.5k lines in pages+components); contrast ratios were not computed (that requires rendering, which this review could not do) — token hex values are reported so a contrast check can be run separately.

## ARIA usage — sparse, concentrated in 15 files

`aria-label`/`aria-describedby`/`aria-hidden`/`aria-invalid`/`role=` together total **26 occurrences across 15 files**, out of ~200 component/page files. `aria-describedby` and `aria-invalid` are used **zero times anywhere in the codebase**.

Good examples exist and should be the pattern to replicate:
- `ui/input.tsx` deliberately derives an `aria-label` from the placeholder when no label/id/`aria-labelledby` is present — a genuine "accessibility floor" built into a shared primitive.
- `layout/AppShell.tsx` labels its icon-only sidebar toggle, breadcrumb nav, notification bell, and user-menu buttons.
- `ui/spinner.tsx` correctly marks itself `aria-hidden="true"` (decorative).
- `ui/StatusBanner.tsx`/`ui/alert.tsx` use `role="alert"` on their dismiss controls.

Gaps: of **368 raw `<button>` elements** in the codebase (vs. only 24 uses of the styled `Button` component), the large majority — including toggle-style buttons in `SupervisorNotes.tsx` — carry no `aria-pressed`/`aria-expanded` even where they function as toggles. No custom dropdown/combobox anywhere uses ARIA combobox patterns (native `<select>` is used instead, which is the correct fallback, but only because nothing more complex was attempted).

## Keyboard navigation — a confirmed real gap

`tabIndex` is used **zero times** in the entire codebase. `onKeyDown` appears 11 times, all as `Enter`-to-submit convenience handlers on native search/chat inputs (a bonus, not a required fix, since native elements already have keyboard support). The `<div onClick>` anti-pattern — a clickable element with no `tabIndex`, `role="button"`, or `onKeyDown` fallback — was confirmed in **3 files**:
- `ui/NotificationPanel.tsx` — the entire notification row is click-to-mark-read with no keyboard path; a keyboard/screen-reader user can only reach the nested dismiss button.
- `components/DigitalTwinDashboard.tsx` — a scenario-selection row, same gap.
- `components/RegulatoryComplianceDashboard.tsx` — an expandable finding-detail card, same gap (only `cursor:"pointer"` signals interactivity).

No evidence anywhere of focus-trap or Escape-to-close behavior on any modal/dialog implementation — dialogs are plain conditionally-rendered `<div>`s (see [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)).

## Focus indicators — present in shared primitives, absent almost everywhere else

`frontend/src/index.css` has **zero** global `focus`/`focus-visible` rules — no fallback exists at the CSS layer. Tailwind `focus:`/`focus-visible:` utilities appear in only 10 files: `ui/button.tsx` (token-based ring color, but only for 2 of 6 variants — `outline`/`secondary`/`ghost`/`success`/`warning` fall back to Tailwind's default ring, not the design tokens), `ui/input.tsx`/`select.tsx`/`textarea.tsx` (hardcoded `focus:ring-blue-500`, inconsistent with the `--color-primary` indigo token), plus one hit apiece on 6 page files. **The 368 raw `<button>` elements outside the shared `Button` component have no verified custom focus-visible styling anywhere** — they rely entirely on whatever the browser's default outline provides, which some inline `style={{}}` objects may inadvertently suppress (not individually verified per button).

## Alt text — present but weak on clinical images

Only 6 raw `<img>` elements exist in the whole frontend, and **all 6 have `alt=`** — no missing-alt gap. However, on the two components that display actual uploaded clinical inspection images (`NewInspectionPage.tsx`, `InspectionImageUploadPage.tsx`), alt text is just the raw filename (e.g. `"IMG_2481.jpg"`), not a description of the clinical content — technically compliant, but not useful to a screen-reader user trying to distinguish between uploaded images.

## Color and color-as-only-signal

The design-token palette (`index.css`): primary `#4f46e5`, success `#059669`, warning `#d97706`, danger `#dc2626`, info `#0284c7`, each with `-hover`/`-subtle` variants; body text `#0f172a` on `#f8fafc`. No dark-mode variant tokens exist. Contrast ratios were not computed by this review and should be verified with a contrast-checking tool before any WCAG AA claim is made, especially for subtle-background/text-color pairs.

`CustomerSuccessDashboard.tsx`'s `HealthBadge` correctly pairs a colored dot with its text label ("Green — 85%") — color is not the sole signal there. By contrast, several **pure decorative color dots with no adjacent text or `aria-label`** were found (`CustomerOnboardingPage.tsx`), and several progress-bar-style colored fills (`InspectionReadinessPage.tsx`, `ExecutiveAdoptionPage.tsx`, `NetworkDashboardPage.tsx`, `GoLiveCenterPage.tsx`, `DeploymentReadinessPage.tsx`, `BaselineReadinessPage.tsx`) rely on a numeric score displayed elsewhere on the page — the bar's own color-band meaning is not independently exposed to assistive tech (no `role="progressbar"`/`aria-valuenow` on any of them).

## Screen reader compatibility / semantic HTML

`layout/AppShell.tsx` is a genuinely strong example — `<aside>`, `<nav>` (used twice, including a properly labeled `<nav aria-label="Breadcrumb">`), `<header>`, `<main>`, and native `<button>` elements throughout, with only 15 bare `<div>`s in the whole 423-line file. This is the pattern to replicate.

The opposite extreme, also confirmed: `NewInspectionPage.tsx` — 75 `<div>` elements vs. only 4 `<button>`s, **zero** `<main>`/`<section>`/`<header>` landmark elements. A large, complex clinical-inspection form built almost entirely from unstructured `<div>`s. Two smaller sampled pages (`FindingsQueuePage.tsx`, `OperationsDashboard.tsx`) land in between, with a reasonable `<div>`-to-`<section>` ratio but zero `<button>` elements (likely relying on `<Link>`/inline handlers).

## Error messaging — visually associated, not programmatically associated

`ui/RequiredField.tsx`'s `FieldError` renders `<p role="alert">{message}</p>` under the field (used in 17 places), and `LoginPage.tsx` uses the same `role="alert"` pattern for its login-failure banner. This means the error **is** announced once via the live region when it appears. However, since `aria-describedby` and `aria-invalid` are both used zero times codebase-wide, **the error text is never programmatically linked to its input** — a screen-reader user tabbing back into the invalid field afterward gets no "invalid"/"describes error X" indication from the field itself. This is an announced-once pattern, not a fully wired ARIA error association.

## Summary of concrete gaps (priority order)

1. `aria-describedby`/`aria-invalid` are used nowhere — form errors are announced once but never linked to their input.
2. 3 files use the `<div onClick>` anti-pattern with no keyboard fallback — small in count but a real keyboard-trap risk for those specific interactions.
3. No global focus-visible CSS exists; the 368 raw buttons outside the shared `Button` primitive have no verified custom focus styling.
4. ARIA labeling is concentrated in `AppShell.tsx` and the shared `ui/` primitives — essentially absent from the ~180 page-level dashboard components.
5. Clinical-image alt text is present but not clinically descriptive (raw filenames).
6. `NewInspectionPage.tsx` (the primary technician-facing form) is the codebase's clearest div-soup example, with zero semantic landmark elements, in direct contrast to `AppShell.tsx`'s strong semantic structure.

None of these require new AI capability to fix — they are markup/attribute-level changes to existing components, consistent with this program's "no new AI capabilities" scope.
