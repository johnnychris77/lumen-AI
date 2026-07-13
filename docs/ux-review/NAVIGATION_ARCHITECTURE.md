# LumenAI — Navigation Architecture

Objective 3 review. This document describes the real navigation structure implemented in `frontend/src/components/layout/AppShell.tsx` (423 lines) and `frontend/src/main.tsx` (556 lines, the actual router — there is no separate `App.tsx`).

## Nav data model

```ts
type NavLeaf = { to: string; label: string; icon: React.ElementType; roles?: string[] };
type NavGroup = { label: string; roles?: string[]; items: NavLeaf[] };
```
Navigation is a static array of 10 groups (`NAV_GROUPS`). Role-gating is optional on both the group and each individual leaf; an omitted `roles` array means the item is visible to every authenticated user. Two gating constants are used:
```ts
const ELEVATED_ROLES = ["admin", "spd_manager", "site_admin", "tenant_admin"];
const EXECUTIVE_ROLES = [...ELEVATED_ROLES, "executive"];
```
`site_admin`, `tenant_admin`, and `executive` are **not part of the core dev-auth role set** (see [USER_PERSONAS.md](./USER_PERSONAS.md)), so for a normal `admin`/`spd_manager`/`operator`/`viewer`/`vendor_user` account, these gates effectively only ever match `admin` or `spd_manager`.

The code's own comment is explicit that this is UX decluttering, not a security boundary: *"hiding a link is never the security boundary"* — every API call is independently re-checked server-side.

## The 10 nav groups (label → routes, role restriction noted)

| Group | Role gate | Items |
|---|---|---|
| Executive | `EXECUTIVE_ROLES` | Dashboard, Command Center, Surgical Readiness, Global Registry |
| Inspection Intelligence | none | Dashboard, New Inspection, Borescope Capture, Inspection History, Review Queue, Inspection Analytics, Smart Work Queue |
| Baselines | none (Baseline Reviews item gated `ELEVATED_ROLES`) | Manufacturer Baselines, Vendor Baselines, Baseline Library, Baseline Reviews |
| Instruments | none | Instrument Registry, Instrument Passport, Instrument Library, Anatomy Library, Inspection Zones, Coverage Dashboard, Barcode/QR/KeyDot, Image Library, Upload Baseline Image, Upload Inspection Image |
| Quality & Compliance | none (Audit Evidence/Enterprise Quality/Supervisor Coaching items gated) | Findings, CAPA, Audit Evidence, Enterprise Quality, SPD Education Library, Supervisor Coaching, Pre-Sterilization Command Center, Knowledge Graph, Knowledge Center, Agent Trace, Clinical Intelligence OS |
| Analytics | `EXECUTIVE_ROLES + operator` (some items further gated `admin`/`spd_manager` only) | Executive Dashboard, Benchmarking, Risk Signals, Quality Dashboard, Clinical Service Readiness, Operational Analytics, Operations Board, Pilot Data Collection, Pilot Validation |
| Enterprise | `ELEVATED_ROLES` | Network Dashboard, Image Quality |
| Go-Live | `ELEVATED_ROLES` | Go-Live Center, Implementation Tracker, Training Compliance, Baseline Readiness, Inspection Readiness, Executive Adoption, Value Realization |
| Customer Success | `ELEVATED_ROLES` | Onboarding Center, Customer Health, Deployment Readiness, Training Center, ROI Center, Subscription |
| Administration | `ELEVATED_ROLES` | User Roles, Users, Roles, Settings |

Active-route highlighting uses react-router's `NavLink` `isActive`; the Dashboard entry uses `end={to === "/"}` so it is only "active" on an exact match, not as a path prefix.

## Breadcrumbs

`AppShell.tsx`'s `Header` renders a `Breadcrumb` built from `location.pathname`, resolving a human-readable label by scanning `NAV_GROUPS` for the **first** item whose `to` matches the current path (the code's own comment notes: *"breadcrumb uses first match, not last"*), falling back to a slugified path segment when no nav entry matches — which happens for every one of the 45 orphaned routes below.

**At least 6 page files additionally hand-roll their own breadcrumb bar inside the page body** (`VendorIntake.tsx`, `BaselineReviewPage.tsx`, `VendorBaselinePortalPage.tsx`, `UserManagementPage.tsx`, `ManufacturerBaselinesPage.tsx`, `IntakeHistoryPage.tsx`), producing two differently-styled breadcrumb trails stacked on the same screen — a direct, citable "duplicate navigation" finding.

## Search and quick actions — absent

There is **no global search box** and **no quick-action affordance** (e.g. a persistent "+ New Inspection" button) anywhere in `AppShell.tsx`'s header. The header contains only: breadcrumb, a role badge, a notification bell, and a user-menu dropdown. There is no command palette, no fuzzy search, and no favorites/pinning mechanism — reaching any feature requires either the sidebar or a direct URL.

## The central finding: 45 routes exist with zero sidebar entry

Diffing every `path="..."` in `main.tsx` against every `to:` in `NAV_GROUPS` surfaces **45 routes reachable only by typing the URL directly** (or via a link buried inside another page), out of roughly 90 total authenticated routes — this is nearly half the application:

```
/accreditation  /agents  /ai-assurance  /atlas  /autonomous-operations
/case-intelligence  /collaboration  /collaboration-governance  /commercial
/copilot-workspace  /council  /developers  /digital-twin  /executive
/forecast  /global-intelligence  /global-standards  /governance  /growth
/instrument-forensics  /integrations  /intelligence-cloud  /knowledge-memory
/launcher  /legacy  /maestro  /marketplace  /my-learning  /network
/network-intelligence  /oracle  /phoenix  /platform-admin  /platform-health
/pulse  /quality  /quality-command-center  /research  /risk  /sage
/scenario-analysis  /sentinel  /strategy  /vendor-intelligence  /veritas
/workflow-builder
```

This cuts in the opposite direction from the brief's "reduce navigation complexity" framing — the risk here is not clutter, it's **undiscoverability**. Notably, this list includes exactly the screens this review needed to trace for the Supervisor journey (`/steward` is also orphaned, though not listed above as it wasn't in the diffed set — confirmed separately in [USER_JOURNEYS.md](./USER_JOURNEYS.md)), the Director/Executive journey (`/executive`, `/strategy`), and the Biomedical Engineering persona (`/instrument-forensics`). See [USER_PERSONAS.md](./USER_PERSONAS.md) for the persona-level impact and [USER_JOURNEYS.md](./USER_JOURNEYS.md) for the workflow-level impact.

## Client-side role restriction on routes (not the real security boundary)

`main.tsx` wraps a small number of routes in an inline `RequireRole` component:
- `/operations-board`, `/users`, `/roles`, `/user-management`, `/settings`, `/coaching-dashboard` → `ELEVATED_ROLES`
- `/pilot-data-collection` → `["admin","spd_manager"]`

Every other route inside the authenticated section is reachable by any logged-in user at the React-Router level regardless of role — the backend independently re-enforces per-endpoint authorization on the actual API calls those pages make, per the code's own comment (*"client-side declutter... not the security boundary"*), consistent with the Phase 1 architecture review's finding that tenant/role isolation is enforced server-side.

## Recommendation

The highest-value navigation fix identified by this review is not simplification but **completion**: add sidebar entries for the 45 orphaned routes (or intentionally retire the ones that are genuinely dead/superseded, such as the `/executive` vs. `/executive-command-center` duplication — see [USER_PERSONAS.md](./USER_PERSONAS.md)), and de-duplicate the 6 pages with double breadcrumb rendering. Neither fix requires new AI capability or architecture change.
