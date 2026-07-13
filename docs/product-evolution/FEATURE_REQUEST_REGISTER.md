# LumenAI — Feature Request Register

Every entry follows the required 18-field template from `docs/product-evolution/FEATURE_GOVERNANCE.md`. Every "Evidence Source" cites a specific, real document from this program — none are invented. Per the honesty constraint established throughout this document set, **no entry here claims "Pilot Hospital" or "Customer Feedback" as its evidence source**, since none exists yet; entries are instead grounded in usability studies, performance metrics, security reviews, and clinical validation reviews — all explicitly acceptable input sources.

---

### FR-001 — Reachable Supervisor Approve/Return Action

- **Description**: Add a working, reachable UI control that lets a supervisor approve or return an inspection finding, wired to the platform's existing disposition-recording backend.
- **Problem Statement**: No reachable approve/return action exists anywhere in the frontend today — the nav-reachable review queues are view-only, and the components whose names most plausibly match this function are orphaned from navigation and, per their own code comments, not the actual approval point.
- **Business Value**: Directly enables the core clinical workflow every pilot customer will expect; currently a blocking gap for any real pilot.
- **Clinical Value**: This is the UI-side completion of a patient-safety-critical control — the backend enforcement (mandatory override reason, `human_review_required`) is real and sound; only the frontend control is missing.
- **Evidence Source**: `docs/ux-review/USER_JOURNEYS.md` (Supervisor journey), reconfirmed in `docs/demo-program/ROLE_BASED_DEMOS.md`.
- **Supporting Metrics**: None yet measured (no pilot); qualitative finding confirmed via direct code inspection of every candidate screen.
- **Affected Users**: SPD Supervisor, SPD Manager.
- **Affected Modules**: Frontend — `FindingsQueuePage.tsx`, `InspectionWorkQueuePage.tsx`, or a new dedicated approval view.
- **Security Impact**: None — uses existing RBAC.
- **Clinical Impact**: High — closes the loop on the platform's human-review safety model.
- **Operational Impact**: High — removes a workflow blocker for supervisors.
- **Estimated Effort**: Medium.
- **Priority**: Critical.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Approved.
- **Target Version**: 1.1.

---

### FR-002 — Consolidate the Three Inspection-Creation Flows

- **Description**: Merge `New Inspection`, `Borescope Capture`, and `Upload Inspection Image` into one consistent flow, or clearly differentiate their purpose and remove the contradictory manual-entry rules between them.
- **Problem Statement**: Three sidebar destinations do the same core job with inconsistent rules about whether finding-category/risk-level is AI-derived or manually entered — confirmed independently by both this session's UX review and the internal dogfooding exercise's two-step upload friction finding.
- **Business Value**: Reduces training time and support burden; directly named as friction in both evidence sources.
- **Clinical Value**: Removes ambiguity about whether a technician is meant to manually classify findings the AI already determines, reducing risk of inconsistent data entry.
- **Evidence Source**: `docs/ux-review/USER_JOURNEYS.md`; `docs/pilot/pilot-lessons-learned.md` §2b (internal dogfooding, caveated per `CUSTOMER_FEEDBACK_REPORT.md`).
- **Supporting Metrics**: None yet from real usage; two independent qualitative findings converge on the same root cause.
- **Affected Users**: SPD Technician.
- **Affected Modules**: `NewInspectionPage.tsx`, `CapturePage.tsx`, `InspectionImageUploadPage.tsx`.
- **Security Impact**: None.
- **Clinical Impact**: Medium — reduces risk of inconsistent manual data entry contradicting AI-derived findings.
- **Operational Impact**: High.
- **Estimated Effort**: Medium-High.
- **Priority**: High.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Planned.
- **Target Version**: 1.1.

---

### FR-003 — Wire Orphaned Routes into Primary Navigation

- **Description**: Add sidebar entries for the 45 routes currently reachable only by direct URL, or deliberately retire genuinely superseded ones (e.g. reconcile the two competing "executive" dashboards).
- **Problem Statement**: Roughly half the application's built screens are undiscoverable through normal navigation.
- **Business Value**: Surfaces already-built capability (Vanguard's real executive/strategy tools, Veritas evidence review, Steward action tracking) without new engineering investment in those features themselves.
- **Clinical Value**: Low-direct, but includes clinically-relevant screens (Sentinel-X Patient Safety Alerts) currently undiscoverable.
- **Evidence Source**: `docs/ux-review/NAVIGATION_ARCHITECTURE.md`.
- **Supporting Metrics**: 45 of ~90 routes (50%) confirmed orphaned via direct route/nav diff.
- **Affected Users**: All roles.
- **Affected Modules**: `frontend/src/components/layout/AppShell.tsx`'s `NAV_GROUPS`.
- **Security Impact**: None — navigation only, backend authorization unchanged.
- **Clinical Impact**: Low-Medium.
- **Operational Impact**: High.
- **Estimated Effort**: Low.
- **Priority**: High.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Approved.
- **Target Version**: 1.1.

---

### FR-004 — Consolidate Duplicated Dashboard KPIs

- **Description**: Establish one canonical source per core KPI (Total Inspections, Critical Findings, Pass Rate, Risk Score, Network Participants) instead of independent per-dashboard recomputation.
- **Problem Statement**: The same metrics are recomputed across 3-8 different screens, sometimes from different backend fields, risking visible metric drift.
- **Business Value**: Reduces engineering maintenance burden and eliminates a credibility risk during customer demos.
- **Clinical Value**: None direct.
- **Evidence Source**: `docs/ux-review/DASHBOARD_STANDARDS.md`.
- **Supporting Metrics**: At least 5-8 core KPIs duplicated across 3-8 screens each, including one confirmed field-name mismatch (`network_participants` vs. `total_network_participants`).
- **Affected Users**: All dashboard-facing roles.
- **Affected Modules**: ~68 dashboard pages across `frontend/src/pages/`.
- **Security Impact**: None.
- **Clinical Impact**: None direct.
- **Operational Impact**: Medium.
- **Estimated Effort**: Medium.
- **Priority**: Medium.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Planned.
- **Target Version**: 1.1.

---

### FR-005 — Fix Atlas Enterprise Dashboard N+1 Query Pattern

- **Description**: Refactor `atlas_dashboard_service.py`'s per-facility loop to batch its underlying queries.
- **Problem Statement**: Loading the enterprise Atlas dashboard issues roughly 7 serialized queries per facility rather than a batched equivalent.
- **Business Value**: Reduces dashboard load time as facility count scales — directly relevant to the "Enterprise Scale" performance objective.
- **Clinical Value**: None direct.
- **Evidence Source**: `docs/release-management/PERFORMANCE_LOG.md`.
- **Supporting Metrics**: Confirmed via direct code trace, not yet measured under real load (no load-testing infrastructure exists, per Phase 1's Production Readiness Scorecard).
- **Affected Users**: Market Director, Enterprise Executive.
- **Affected Modules**: `backend/app/services/atlas_dashboard_service.py`.
- **Security Impact**: None.
- **Clinical Impact**: None.
- **Operational Impact**: Medium-High at enterprise scale.
- **Estimated Effort**: Low-Medium.
- **Priority**: Medium.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Approved.
- **Target Version**: 1.1.

---

### FR-006 — Consistent AI Inference Queuing

- **Description**: Move `app/routes/inspect.py`'s `stream_frame` inference call onto the RQ job queue, matching `stream.py`'s existing correct pattern.
- **Problem Statement**: The same job function (`run_inspection`) is queued asynchronously in one route and run synchronously in-request in another, creating an inconsistent, blocking inference-latency risk on one endpoint.
- **Business Value**: More predictable API response times under concurrent load.
- **Clinical Value**: None direct — does not change inference logic, only its execution context.
- **Evidence Source**: `docs/release-management/PERFORMANCE_LOG.md`.
- **Supporting Metrics**: Confirmed via direct code trace.
- **Affected Users**: SPD Technician (capture flow).
- **Affected Modules**: `backend/app/routes/inspect.py`.
- **Security Impact**: None.
- **Clinical Impact**: None.
- **Operational Impact**: Medium.
- **Estimated Effort**: Low.
- **Priority**: Medium.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Approved.
- **Target Version**: 1.1.

---

### FR-007 — Mount the Orphaned Veritas Evidence Panel; Wire GuardianX Explainability Tab

- **Description**: Mount `VeritasEvidencePanel.tsx` (built, correctly renders `limitations`, but never mounted anywhere) into the live inspection-results flow, and wire `AIAssuranceCenter.tsx`'s Explainability tab to actually fetch and render GuardianX's `alternative_explanations_json` rather than only printing API-call instructions.
- **Problem Statement**: "Limitations" and "alternative explanations" — two of the seven fields this program's own AI-explainability standard requires — are computed and stored server-side but have no live path to the screen.
- **Business Value**: Directly closes a named explainability gap ahead of any pilot or clinical-audience demo.
- **Clinical Value**: High — restores the "why" transparency this platform's own governance model requires.
- **Evidence Source**: `docs/ux-review/UX_GUIDELINES.md`.
- **Supporting Metrics**: Confirmed via direct component-mounting trace — 0 references to `VeritasEvidencePanel` outside its own file.
- **Affected Users**: SPD Supervisor, Quality Department.
- **Affected Modules**: `components/VeritasEvidencePanel.tsx`, `components/AIAssuranceCenter.tsx`.
- **Security Impact**: None.
- **Clinical Impact**: High.
- **Operational Impact**: Medium.
- **Estimated Effort**: Low-Medium (data and backend already exist).
- **Priority**: High.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Approved.
- **Target Version**: 1.1.

---

### FR-008 — Bind "Human Review Required" Disclaimer to the Real Per-Record Flag

- **Description**: Replace the static, fixed "AI outputs include human_review_required: true" boilerplate text with a dynamic binding to each record's actual `human_review_required` field.
- **Problem Statement**: The disclaimer currently reads identically regardless of the record's real value, risking a false sense of unconditional coverage.
- **Business Value**: Closes a real fidelity gap between platform claims and platform behavior.
- **Clinical Value**: High — this is a patient-safety-adjacent transparency fix.
- **Evidence Source**: `docs/ux-review/UX_GUIDELINES.md`.
- **Supporting Metrics**: Confirmed via direct code trace.
- **Affected Users**: All clinical-facing roles.
- **Affected Modules**: `NewInspectionPage.tsx`, `ClinicalDecisionPanel.tsx`.
- **Security Impact**: None.
- **Clinical Impact**: High.
- **Operational Impact**: Low.
- **Estimated Effort**: Low.
- **Priority**: High.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Approved.
- **Target Version**: 1.1.

---

### FR-009 — Add Missing `Inspection` Model Fields

- **Description**: Persist `facility_name`, `department`, `tray_id` (as a real dropdown-backed field, not free text), `instrument_barcode`, `instrument_udi`, `borescope_image_count`, and a formal `related_instrument_id` foreign key on the `Inspection` model.
- **Problem Statement**: These fields are captured on the form but not persisted, breaking tray-level and instrument-level reporting.
- **Business Value**: Unlocks several of the missing-report items below without further schema work.
- **Clinical Value**: Low-direct; improves traceability.
- **Evidence Source**: `docs/pilot/pilot-lessons-learned.md` §4 (internal dogfooding, caveated).
- **Supporting Metrics**: 7 named missing fields, confirmed against the current `Inspection` model schema.
- **Affected Users**: SPD Technician, Quality Department (reporting).
- **Affected Modules**: `backend/app/models/inspection.py` (or equivalent), Alembic migration.
- **Security Impact**: None.
- **Clinical Impact**: Low.
- **Operational Impact**: Medium.
- **Estimated Effort**: Medium (requires a real Alembic migration — note the existing 4-migrations-for-417-tables gap from Phase 1's Production Readiness review; this is an opportunity to add real migration discipline alongside the schema change).
- **Priority**: Medium.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Planned.
- **Target Version**: 1.1.

---

### FR-010 — Add Missing Aggregate Reports

- **Description**: Add tray-level contamination summary, instrument cycle-count trend, baseline-coverage %, review-turnaround-time, upload-failure log, week-over-week finding trend, and instrument×finding risk heat map reports.
- **Problem Statement**: None of these views exist today despite the underlying data being available (once FR-009's field gaps are closed).
- **Business Value**: Directly requested/observed friction during internal dogfooding; likely to be among the first real requests once a pilot begins.
- **Clinical Value**: Medium — trend/heat-map views support proactive quality review.
- **Evidence Source**: `docs/pilot/pilot-lessons-learned.md` §5 (internal dogfooding, caveated).
- **Supporting Metrics**: 7 named missing report types.
- **Affected Users**: Quality Department, SPD Manager.
- **Affected Modules**: Analytics/reporting services and dashboards (`quality_dashboard_service.py`, `pilot_analytics.py`).
- **Security Impact**: None.
- **Clinical Impact**: Medium.
- **Operational Impact**: Medium.
- **Estimated Effort**: Medium-High (7 distinct views).
- **Priority**: Low-Medium.
- **Product Owner**: TBD.
- **Approval Status**: Recommended for Research (scope and prioritize the 7 sub-items individually before committing to all 7 in one release).
- **Target Version**: 1.1 or later, pending sub-item scoping.
