# P4.6 — Reviewer Assignment Matrix

**Purpose:** map each synthetic-pilot governance gate to the **required authority**, eligibility
rules, and the (blank) assignment. **No assignment or decision is prefilled.** The Release Authority
records assignments; decisions are recorded in the respective decision documents. Identity must be
authenticated and roles kept distinct for separation of duties.

---

## 1. Assignment matrix (DO NOT prepopulate decisions)

| Gate | Decision record | Required authority | Eligibility rule | Assigned reviewer (name/role) | Identity verified (how) | Status |
|---|---|---|---|---|---|---|
| RGI-01 (synthetic) data authorization | `P4_6_SYNTHETIC_GOVERNANCE_DECISIONS.md` §C | Synthetic Data-Governance Owner | Not the dataset's generator/author; authenticated | | | OPEN |
| RGI-02 reviewer framework | same §C | Release Authority | Authenticated; distinct from reviewers confirmed | | | OPEN |
| RGI-10 metric convention | `P4_6_RGI10_METHODOLOGY_DECISION_RECORD.md` §4 | Scientific-Methodology Reviewer | Qualified in segmentation/anomaly metrics; not the metric-code implementer | | | OPEN |
| **SEC-174-02 disposition** | `P4_6_INDEPENDENT_SECURITY_REVIEW_REQUEST.md` | **Independent NON-AUTHOR security reviewer** | **Did NOT author #171–#178 or prior reviews**; declares independence | | | OPEN |
| **SEC-175-01 independent review** | same + `P3_SECURITY_REVIEW_HANDOFF.md` | **Independent NON-AUTHOR security reviewer** | same as above | | | OPEN |
| Readiness checklist | `P4_6_SYNTHETIC_PILOT_READINESS_CHECKLIST.md` | Pilot operator + Release Authority | Operator authenticated | | | OPEN |
| Dataset manifest verification | `P4_6_SYNTHETIC_DATASET_MANIFEST.md` | Synthetic Data-Governance Owner | Not the generator | | | OPEN |
| Final release authorization | `P4_6_RELEASE_AUTHORIZATION_RECORD.md` §2 | Release Authority | Authenticated; confirms the above | | | OPEN |

## 2. Eligibility notes (carried from P4.5, unchanged)

- **John asaah** (`johnnychris77`) was designated reviewer in P4.5. His eligibility is **role-
  dependent**:
  - Enterprise **Release Authority** (synthetic pilot scope): **Yes**.
  - Institutional data-rights (synthetic form): **Conditionally** — valid for synthetic-only scope;
    real-data use still needs genuine institutional/IRB authority he alone cannot supply.
  - Scientific-methodology (RGI-10): **only if qualified**, and he must attest the qualification.
  - **Independent non-author security reviewer (SEC-174-02 / SEC-175-01): NO** — he sponsored/
    directed P4.1–P4.6 and fails the non-author independence test.
- **The AI workflow (author of #176/#177/#178 and all assurance docs): NOT eligible** for the
  independent security role, and cannot self-approve any gate.
- **Separation of duties:** one person holding several of these roles is a recorded governance
  weakness for the Release Authority to weigh, not a silent default.

## 3. Independent-security-reviewer options (neither chosen here)
Per `P4_5_DECISION_TRACKING_REGISTER.md` §3, two legitimate paths exist and **neither is selected**
(selecting one is an affirmative act for the Release Authority, not a default):
- **(a)** Engage a genuine independent **non-author** reviewer — the only path that **closes**
  SEC-175-01.
- **(b)** The Release Authority records an explicit, **signed risk-acceptance waiver** for the
  synthetic-only pilot — logged as a **risk acceptance**, explicitly **NOT** an independent security
  approval and **NOT** SEC-175-01 closure. It must be authored/signed by the authority themselves;
  the AI workflow will not create it.

Until (a) or (b) is authentically recorded, **SEC-175-01 remains OPEN** and the security axis is
**not** approved.

*No reviewer is assigned and no decision is recorded by this matrix. Assignments and decisions are
authored by the named authorities.*
