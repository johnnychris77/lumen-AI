# LumenAI — User Personas

**User Experience Program · Phase 4: Harmony · User Experience, Human Factors & Workflow Optimization**

Objective 1 review. This document maps the brief's 12 named clinical/operational personas onto what LumenAI's real, enforced role system and real pages actually support — grounded in code, not the idealized job description. Where a persona has no distinct enforced role or no dedicated screen, that gap is stated plainly rather than assumed away, consistent with this repository's established review discipline (see `docs/clinical-validation/HUMAN_OVERSIGHT_MODEL.md` for the same pattern applied to clinical approval tiers).

## The role-system reality behind every persona below

There is **no single canonical role enum** in this codebase. At least four independent, only-partially-overlapping role vocabularies are simultaneously enforced:
1. **The core 5-role set** (`backend/app/deps.py`'s `_DEV_ROLE_MAP`, `backend/app/services/platform_identity_service.py`'s `_DEV_AUTHZ_ROLES`): `admin`, `spd_manager`, `operator`, `viewer`, `vendor_user`.
2. `backend/app/routes/admin_users.py`'s `ASSIGNABLE_ROLES`, which adds a sixth value, `supervisor`, not present in the core set above.
3. `backend/app/enterprise_access_control.py`'s `ROLE_ORDER`: `viewer`/`auditor`/`operator`/`executive`/`admin` — introduces `auditor` and `executive`, genuinely enforced on `p20_network_intelligence.py` routes but never issued by dev-auth.
4. `backend/app/routes/mobile.py`'s `_VALID_ROLES`: `technician`/`supervisor`/`manager`/`quality_director`/`infection_prevention`/`executive` — a third, disjoint vocabulary for the mobile role-update endpoint.

A code comment in `backend/app/models/council_leadership.py` states LumenAI's RBAC has "four roles (admin/spd_manager/operator/viewer)" — omitting `vendor_user` — showing even internal documentation disagrees with the dev-auth map by one role. **Any UX documentation describing "who can do what" must specify which of these four vocabularies applies to which screen** — no unified role glossary exists today.

## Personas

### SPD Technician
- **Goals**: Process instrument trays quickly and correctly; get a clear AI read on contamination/damage before sign-off.
- **Responsibilities**: Capture inspection images, tag anatomy zones, submit inspections.
- **Information needed**: Instrument identity, capture guidance, AI finding/confidence output, whether supervisor review is required.
- **Typical workflow**: Login → Dashboard → New Inspection form (single scrolling page, not a wizard) → inline AI Prediction Panel.
- **Real role mapping**: `operator` (or `viewer` if read-only). No distinct "technician" role exists in the core RBAC; `mobile.py`'s separate vocabulary does use `technician` literally, but only for its own mobile-role-update endpoint.
- **Pain points (verified)**: **Three separate, non-integrated inspection-creation screens** are all reachable from the sidebar and do overlapping jobs — `New Inspection` (`/inspection/new`), `Borescope Capture` (`/inspection/capture`), and `Upload Inspection Image` (`/inspection-image-upload`) — each re-declaring its own instrument-identity fields with no shared state. Worse, `New Inspection`'s own on-page copy states finding-category and risk-level are AI-determined and "technicians do not enter them," while `Upload Inspection Image` requires the technician to manually pick a `finding_category` and `risk_level` from a dropdown — a technician who uses the "wrong" nav entry is asked to do work the other flow says is not theirs. See [USER_JOURNEYS.md](./USER_JOURNEYS.md) and [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md).
- **Required permissions**: Create inspections, upload images; no admin-tier access needed.

### SPD Lead Technician
- **Goals**: Same as Technician plus light peer quality-checking.
- **Real role mapping**: **No distinct enforced role exists anywhere in the codebase for this title** — a Lead Technician would be provisioned as `operator` (identical permissions to a line Technician) or, informally, given `spd_manager` (which over-grants manager-tier access). This is a real gap, not an oversight to smooth over.
- **Pain points**: Same three-flow ambiguity as Technician; no intermediate permission tier to reflect the "lead" responsibility.

### SPD Supervisor
- **Goals**: Review AI-flagged findings, approve or return instruments, oversee technician quality.
- **Responsibilities**: Approve/reject dispositions, review baselines, handle escalations.
- **Real role mapping**: **No distinct enforced role.** `admin_users.py`'s `ASSIGNABLE_ROLES` does include the literal string `supervisor`, but it does not appear in the core dev-auth role set or in `ROLE_AUTHORITY_TIER`-style authority checks documented in the clinical review's `HUMAN_OVERSIGHT_MODEL.md` — in practice, `spd_manager` covers this scope.
- **Pain points (verified — the most significant finding of this review)**: The nav-reachable "Review Queue" (`/findings`) is a relay that links every row to the same generic `/inspection-work-queue` page rather than the specific inspection. That destination page (`InspectionWorkQueuePage.tsx`, 166 lines, read in full) renders 7 sectioned tables with **zero `onClick`, button, or link on any row** — a supervisor cannot open an individual inspection or take a disposition action from either nav-reachable screen. The nav-reachable `/baseline-review` page's own on-page copy instructs supervisors to "review and approve" baselines, but the component it renders has **no approve/reject button in its entire 539-line file** — it is read-only. The components whose names most closely match "evidence review" (`Veritas Workspace`, `/veritas`) and disposition action-tracking (`Steward Workspace`, `/steward`) are both **absent from the sidebar nav entirely** (orphaned routes), and each explicitly documents in its own header comment that it is *not* the clinical approve/deny action point. **A real, reachable "approve this finding / return to technician" button could not be located anywhere in this codebase.** See [USER_JOURNEYS.md](./USER_JOURNEYS.md) §Supervisor journey for full detail.
- **Required permissions**: `spd_manager` in practice.

### SPD Manager
- **Goals**: Run the department — staffing, throughput, quality metrics, escalation resolution.
- **Real role mapping**: `spd_manager` — one of only two personas in this list (with Technician) that maps to a genuinely distinct, real, enforced role.
- **Pain points**: Inherits the Supervisor-tier action gaps above, since `spd_manager` is the role that actually satisfies supervisor-tier checks; also faces the dashboard redundancy documented in [DASHBOARD_STANDARDS.md](./DASHBOARD_STANDARDS.md) (the same KPIs like "Total Inspections" and "Critical Findings" recomputed independently across 6-8 different screens).
- **Required permissions**: `spd_manager`.

### Market Director
- **Goals**: Oversee multiple facilities/departments within a market/region.
- **Real role mapping**: **No enforced role exists for a multi-facility "Market Director" tier.** The closest real concept is `executive` (enforced on `p20_network_intelligence.py` routes and in `enterprise_access_control.py`'s `ROLE_ORDER`), but it is never issued by the dev-auth token map, meaning no demo/dev account can actually authenticate as this role today.
- **Pain points**: The real multi-facility leadership screens (Vanguard's `/executive` Executive Intelligence Center and `/strategy` Strategic Planning) are **both orphaned from the sidebar nav** — see [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md). A Market Director using only the sidebar would never discover the one screen (`/strategy`) that has a genuine leadership action (approving/archiving a strategic initiative via status dropdown).
- **Required permissions**: `executive` conceptually; not provisionable via the dev-auth map.

### OR Leadership
- **Goals**: Confirm instrument/tray readiness ahead of scheduled cases; understand delay risk.
- **Real role mapping**: No distinct role. Closest fit is `viewer` (read-only) or `spd_manager` if the person also has SPD authority.
- **Real dashboard**: `SurgicalReadinessDashboard.tsx` (`/surgical-readiness`, nav-visible under "Executive") — Cases Today, Readiness %, Delayed Cases, Case Detail, Surgical Timeline. This is a real, reachable, purpose-built screen for this persona.
- **Pain points**: No loading/error/empty-state markers were found in this page during recon — an OR leader hitting a slow API call gets no feedback that data is still loading.

### Infection Prevention
- **Goals**: Monitor contamination trends, patient-safety signals, and audit trails relevant to infection control.
- **Real role mapping**: `infection_prevention` is a literal, real string in `backend/app/routes/mobile.py`'s `_VALID_ROLES` — but it exists **only** in that one mobile role-update endpoint's vocabulary, not in the core RBAC, `enterprise_access_control.py`, or any web-app route gate found in this review. There is no web dashboard scoped specifically to this persona; the closest fit is Sentinel-X's Patient Safety Alerts tab (`/risk`, itself an orphaned route — see below) or the contamination-trend widgets scattered across `QualityDashboardPage`/`CIOSDashboard`.
- **Pain points**: No dedicated persona-facing screen exists; the patient-safety-relevant data this persona needs is split across at least 3 different dashboards (Sentinel-X risk, Quality Dashboard, CIOS), none built specifically for this role.

### Quality Department
- **Goals**: Track pass/reclean/reprocess rates, CAPA status, root-cause trends, audit readiness.
- **Real role mapping**: `object_authorization.py`'s `QUALITY_ROLES` set includes a literal `quality_manager` string, enforced on some object-authorization checks — but this is a fourth, separate role vocabulary from the core dev-auth set, so a "quality_manager" cannot be issued as a dev/demo login.
- **Real dashboards**: `QualityDashboardPage.tsx` (`/quality-dashboard`, ~20 widgets — one of the densest screens in the app), `QualityManagementCenterPage.tsx` (`/quality`, orphaned from nav), `QualityCommandCenterPage.tsx` (`/quality-command-center`, orphaned from nav). Three separately-named "quality" destinations, two of which are undiscoverable via the sidebar.
- **Pain points**: Widget density and cross-dashboard KPI duplication — see [DASHBOARD_STANDARDS.md](./DASHBOARD_STANDARDS.md).

### Biomedical Engineering
- **Goals**: Track instrument reliability/repair history, decide repair-vs-replace.
- **Real role mapping**: No distinct role; would likely be provisioned as `operator` or `spd_manager`.
- **Real dashboard**: `InstrumentForensicsWorkspace.tsx` (`/instrument-forensics`, orphaned from nav) — the one screen built for this persona, but per the inspection/twin UI recon, its condition-progression data (`insufficient_history`/`rapidly_worsening`/etc.) is rendered as **raw, unstyled JSON** (`&lt;pre&gt;{JSON.stringify(...)}&lt;/pre&gt;`), not a chart or trend visualization — see [DASHBOARD_STANDARDS.md](./DASHBOARD_STANDARDS.md) and the digital-twin section of [UX_GUIDELINES.md](./UX_GUIDELINES.md).
- **Pain points**: Orphaned route (not in sidebar) plus a raw-JSON presentation that undermines the "make progression easy to understand" objective this program was asked to satisfy.

### Manufacturer Representative
- **Goals**: Submit/maintain baseline images and IFU references; review governance-approved feedback.
- **Real role mapping**: `vendor_user` — a genuinely distinct, real, enforced role (one of the 5 core roles).
- **Real dashboards**: `VendorBaselinePortalPage.tsx`, `VendorIntake.tsx`, `ManufacturerBaselinesPage.tsx`, `IntakeHistoryPage.tsx` — all nav-reachable under "Baselines"/"Instruments."
- **Pain points**: `BaselineReviewQueue.tsx` (the screen a manufacturer's submission ultimately depends on) is read-only with no visible approve/reject control, per the Supervisor persona's pain point above — a manufacturer has no way to see, from the product, whether/why their baseline was actually rejected beyond an audit-trail reference.

### Executive Leadership
- **Goals**: Enterprise-wide quality/risk posture, financial impact, strategic decisions.
- **Real role mapping**: `admin` in practice (the dev-auth map's highest tier); `executive` exists as a distinct string in `enterprise_access_control.py`/`p20_network_intelligence.py` route gates but is not dev-auth-issuable.
- **Pain points (verified — a major, quotable finding)**: **Two differently-named, near-duplicate "executive" dashboards coexist**, and the codebase's own comment acknowledges the split: `components/ExecutiveIntelligenceCenter.tsx`'s header states *"Frontend route `/executive`, API prefix `/api/vanguard` — deliberately distinct from the pre-existing `/api/executive` mock-KPI endpoint."* The nav-visible one (`/executive-command-center`) is a KPI-card-only dashboard; the orphaned one (`/executive`, Vanguard's real Executive Intelligence Center, with actual scorecards/financial/governance/strategy data and formatted-as-raw-JSON content) is not reachable from the sidebar at all. An executive using only in-app navigation would never find the "real" one.
- **Required permissions**: `admin`, conceptually `executive`.

### System Administrator
- **Goals**: Manage users/roles, platform configuration, integrations, audit log oversight.
- **Real role mapping**: `admin` — a genuinely distinct, real, enforced role.
- **Real dashboards**: `PlatformAdminPage.tsx` (`/platform-admin`, orphaned from nav), `UserManagementPage.tsx` (`/user-management`, nav-visible under "Administration"), `PlatformHealthPage.tsx` (`/platform-health`, orphaned from nav).
- **Pain points**: Two of the three admin-relevant screens are orphaned from the sidebar despite `admin` being the role most likely to need exactly this kind of platform-operations visibility.

## Cross-persona finding: 45 routes are unreachable from any sidebar nav item

Across every persona above, a recurring pain point is the same underlying defect: **45 of the app's ~90 routes have zero corresponding entry in `AppShell.tsx`'s `NAV_GROUPS`**, including exactly the screens most relevant to Supervisor (`/veritas`, `/steward`), Market Director/Executive (`/executive`, `/strategy`), and Biomedical Engineering (`/instrument-forensics`) personas. See [NAVIGATION_ARCHITECTURE.md](./NAVIGATION_ARCHITECTURE.md) for the full list and root cause.
