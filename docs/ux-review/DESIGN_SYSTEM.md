# LumenAI — Design System

Objective 12 review. Inventories `frontend/src/components/ui/` (15 files) and checks how consistently the rest of the ~200-file frontend actually uses it.

## `ui/` component inventory

| Component | Variants | Design tokens? | Notes |
|---|---|---|---|
| `button.tsx` | default, destructive, outline, secondary, ghost, success, warning; sizes default/sm/lg/icon | **Yes** — `bg-primary`, `bg-danger`, `bg-success`, `bg-warning` + hover tokens | Most recently touched, part of the prior UI-unification pass |
| `badge.tsx` | default, success, warning, destructive, secondary, outline | **Yes** for 4 of 6 variants; `secondary`/`outline` fall back to hardcoded `slate-*` | |
| `alert.tsx` | default, success, warning, destructive, info | **Yes**, full token set | Imported in only 7 files codebase-wide |
| `card.tsx` | single style | No — hardcoded `border-slate-200`, `text-slate-900/500` | Predates the token pass |
| `input.tsx` | none | No — hardcoded `focus:ring-blue-500`, not `ring-primary` | Has a genuinely good built-in accessibility fallback: derives an `aria-label` from the placeholder when none is set |
| `label.tsx` | none | No — `text-slate-700` | |
| `select.tsx` | none | No — same hardcoded `blue-500` focus ring as `input.tsx` | |
| `textarea.tsx` | none | No — same hardcoded `blue-500` focus ring | |
| `spinner.tsx` | none | Token-agnostic (`text-current`) | Correctly marked `aria-hidden="true"` |
| `FormSection.tsx` | none | No — uses `gray-*` scale, not the `slate-*` scale everything else uses | Used only by `NewInspectionPage.tsx` — a single-consumer component placed in the shared folder |
| `RequiredField.tsx` | none | No — hardcoded `red-500/600`, not the `danger` token | Same single-consumer pattern |
| `StatusBanner.tsx` | success/error/warning/info | No — hand-rolled color map duplicating what `alert.tsx` already does with tokens | Used in exactly 1 file (`NewInspectionPage.tsx`) — a second, competing "alert" component |
| `NotificationPanel.tsx` | severity-driven | No — hardcoded `red-500`/`amber-500`/`blue-500` | |
| `barcode-scanner.tsx` | none | No — fully hardcoded amber/black/white | Implements its own modal overlay, independent of any shared dialog pattern |
| `baseline-image-upload.tsx` | none | No — `bg-emerald-600`, `text-blue-500` | |

**The folder contains two eras of code**: `button.tsx`/`badge.tsx`/`alert.tsx` are fully token-based (the newest, most recently touched files); everything else — including `card.tsx`, all form primitives, and the pre-existing alert/notification components — still hardcodes Tailwind palette colors. **Two competing "alert" components coexist** (`alert.tsx`, token-based, 7 consumers vs. `StatusBanner.tsx`, hardcoded, 1 consumer).

## Token adoption across the app — the migration reached ~9 files out of ~200

Only 9 files use the new token classes (`bg-primary`, `text-danger`, etc.): `CouncilWorkspace.tsx`, `StewardWorkspace.tsx`, `OracleWorkspace.tsx`, `Dashboard.tsx`, `AppShell.tsx`, `ui/alert.tsx`, `ui/badge.tsx`, `ui/button.tsx`, plus `index.css` itself. By contrast, the hardcoded Tailwind palette classes the tokens were meant to replace (`bg-indigo-600`, `bg-blue-600`, `text-emerald-600`, `bg-emerald-600`) still appear in **71 files, 157 occurrences** — e.g. `KnowledgeMemoryCenter.tsx` (8), `CatalystCopilotWorkspace.tsx` (6), `SupervisorNotes.tsx` (6), `CustomerSuccessDashboard.tsx` (5), `PilotAnalyticsDashboard.tsx` (5). **The token system, as it stands, covers a handful of the newest flagship-workspace files and the 3 shared primitives it touched — the large majority of the app, including most tables/forms/dashboards, still hardcodes colors.**

## No shared Table, Dialog, or Skeleton component exists

- **Loading states** — three co-existing, hand-written patterns: plain "Loading…" text (`GlobalInfrastructureConsole.tsx`, `QualityIntelligencePage.tsx`), an `animate-pulse` text block with a bespoke message per page (`InspectionReadinessPage.tsx`, `ImageQualityPage.tsx`, `ExecutiveAdoptionPage.tsx`, and 5 more), and inline-style loading text that bypasses tokens entirely (`FindingsQueuePage.tsx`, `OperationsDashboard.tsx`, both using `style={{ color: "#94a3b8" }}`). The `Spinner` primitive is reused in ~8 files but is optional per-author choice, not a convention. **Only one true skeleton block exists in the whole codebase** (`PilotDashboardCards.tsx`), and it's not reused anywhere else.
- **Empty states** — every page writes its own copy and wrapper markup ("No data yet.", "No X found.", "No results", longer instructional variants); styling is inconsistent between Tailwind classes (`text-slate-400`) and inline hex colors (`style={{ color: "#6b7280" }}`) across different files. **No shared `EmptyState` component exists.**
- **Error states** — the token-based `Alert` is imported in only 7 files; meanwhile hardcoded red-color error rendering (bypassing the `danger` token) appears in **51 separate page files, 162 occurrences**. `GlobalRegistryPage.tsx` has no error-handling markup at all.
- **Tables** — no shared `<Table>` component exists; roughly 80 hand-rolled `<table>` elements exist in two competing styling conventions (Tailwind-class style in ~45 places vs. an older inline-`style` convention in components like `EnterpriseCapaPanel.tsx`, `DigitalTwinDashboard.tsx`, `VendorIntelligenceDashboard.tsx`).
- **Forms** — the shared `Input`/`Select`/`Textarea` primitives exist but are bypassed almost everywhere: only 5 page files import `ui/input.tsx`, while raw `<input>` elements appear in 22 page files (66 occurrences) and 33 component files (87 occurrences) — e.g. `NewInspectionPage.tsx` alone has 20 raw `<input>`s.
- **Dialogs/modals** — no `Dialog`/`Modal` component exists in `ui/` at all. `UpgradeModal.tsx` is fully inline-styled with its own overlay/dismiss logic; `barcode-scanner.tsx` implements a second, differently-styled modal overlay independently. Every modal-like UI in the app reinvents overlay, sizing, and dismiss behavior from scratch.

## Icons — the one genuinely consistent convention

`lucide-react` is used in 48+ files and is the dominant, consistent icon convention. Raw inline `<svg>` appears only for legitimate custom graphics (a node-graph connector line, chart elements) — not as a competing icon system.

## Spacing/typography

Tailwind's standard spacing/type scale is followed wherever utility classes are used (only 1 occurrence of arbitrary-bracket-value syntax exists project-wide). However, **776 inline `style={{...}}` objects across 51 files** — concentrated in the pre-unification "Enterprise*/Vendor*/Capa*" components — use arbitrary pixel values (`padding: 32`, `fontSize: 11`) with no relationship to any spacing/type scale, sitting alongside newer files that consistently use Tailwind's scale.

## Recommendation

The design-token migration (`bg-primary`/`text-danger`/etc.) is real and correctly designed where it's been applied, but it has covered roughly 4% of the codebase (9 of ~200 files). The highest-leverage next step is not creating new tokens but **extending the existing ones into `card.tsx`, `input.tsx`, `select.tsx`, `textarea.tsx`, and `StatusBanner.tsx`** (retiring `StatusBanner.tsx` in favor of the already-token-based `alert.tsx`), plus building the three genuinely missing shared components (`Table`, `Dialog`, a loading/empty/error `EmptyState`-style set) that every one of the ~68 dashboards in [DASHBOARD_STANDARDS.md](./DASHBOARD_STANDARDS.md) currently reinvents independently.
