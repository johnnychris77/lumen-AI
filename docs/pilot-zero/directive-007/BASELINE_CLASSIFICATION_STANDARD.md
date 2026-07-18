# LPZ-DIR-007 — Baseline Classification Standard

**Purpose:** define the categories of baseline reference LumenAI recognizes, so
every baseline has a declared purpose, approval authority, permitted uses, and
lifecycle. A baseline is a **trusted reference representation** of a
known-good (or known-reference) instrument image used for comparison in future
computer-vision workflows.

Guardrail: categories describe **provenance and trust level**, not clinical
performance. No category implies regulatory clearance.

## Categories

### Manufacturer Reference
* **Purpose:** vendor-supplied or manufacturer-derived reference of a new/ideal
  instrument.
* **Approval authority:** Engineering Reviewer + Baseline Approver; provenance
  from the manufacturer must be documented.
* **Permitted uses:** reference for structural/appearance comparison; seed for a
  Digital Twin.
* **Restrictions:** must not be presented as a site-validated standard; usage
  rights/provenance must be recorded.
* **Lifecycle:** Draft → Approved → Published → Superseded/Retired.
* **System:** `BaselineLibraryEntry.baseline_type = "manufacturer"`.

### Pilot Zero Candidate Baseline
* **Purpose:** a baseline proposed from Pilot Zero lab acquisition, pending
  approval.
* **Approval authority:** none yet — it is a candidate.
* **Permitted uses:** internal review only; **not** for comparison until approved.
* **Restrictions:** cannot be published or used as a reference while a candidate.
* **Lifecycle:** Draft/Candidate → Under Review → Approved (or Rejected).

### Approved Development Baseline
* **Purpose:** a reviewed, approved baseline for development/comparison use.
* **Approval authority:** Baseline Approver (with engineering, and clinical where
  applicable).
* **Permitted uses:** comparison reference; Digital Twin association; dataset
  provenance.
* **Restrictions:** development context; not a site production standard unless
  also Site Approved.
* **Lifecycle:** Approved → Published → Superseded/Retired.

### Engineering Baseline
* **Purpose:** engineering/optical reference (e.g., calibration-context or
  structural reference) for technical comparison.
* **Approval authority:** Engineering Reviewer.
* **Permitted uses:** engineering comparison, coverage/structure checks.
* **Restrictions:** not a clinical or acceptance standard.
* **Lifecycle:** Draft → Approved → Superseded/Retired.

### Research Baseline
* **Purpose:** exploratory reference for research questions.
* **Approval authority:** AI Researcher + Baseline Approver; flagged research-only.
* **Permitted uses:** research analysis; never a production comparison standard.
* **Restrictions:** must be labeled research-only; excluded from any production
  path.
* **Lifecycle:** Draft → Approved (research) → Retired.

### Site Approved Baseline
* **Purpose:** a baseline a site has reviewed and accepted for its own governed
  use.
* **Approval authority:** site Baseline Approver under customer governance;
  tenant-scoped.
* **Permitted uses:** comparison within that site/tenant.
* **Restrictions:** tenant isolation — not shared across tenants without a
  governed sharing action.
* **Lifecycle:** Approved → Published (site) → Superseded/Retired.

### Retired Baseline
* **Purpose:** a baseline withdrawn from active use.
* **Approval authority:** Baseline Approver records retirement + reason.
* **Permitted uses:** **none for new comparisons**; retained for audit/history.
* **Restrictions:** cannot be selected for new inspections.
* **Lifecycle:** Retired → Archived (immutable history).

### Historical Baseline
* **Purpose:** a superseded prior version kept for traceability.
* **Approval authority:** n/a (system-preserved).
* **Permitted uses:** audit, lineage, reproducing a past comparison.
* **Restrictions:** not used as a current reference.
* **Lifecycle:** Superseded → Archived (retrievable, never overwritten).

## Cross-category rules

* **Approval before use.** Only Approved/Published categories may serve as a
  live comparison reference; candidates and research baselines never enter the
  production comparison path.
* **Tenant isolation.** Site Approved baselines are tenant-scoped; cross-tenant
  use requires an explicit, audited sharing action.
* **Provenance required.** Every baseline records its source and usage rights.
* **No overwrite.** Category or version changes create new versions; historical
  versions are retained (`BASELINE_VERSIONING_STANDARD.md`).

## Governance note (existing system)

`BaselineLibraryEntry.baseline_type` currently enumerates
`manufacturer / vendor / network_contributed`, and `approval_status` is
`pending / approved / deprecated`. The richer category set above is a governance
overlay; a future authorized change may extend the `baseline_type` vocabulary and
map `deprecated → Retired/Historical`. No code is changed under this directive.
