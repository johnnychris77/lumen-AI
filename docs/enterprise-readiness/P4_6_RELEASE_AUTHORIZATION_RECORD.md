# P4.6 — Synthetic Pilot Release Authorization Record (unsigned)

**For:** LumenAI's designated **Release Authority**.
**Status:** **UNSIGNED — no authorization issued.** This record is completed **only** by the Release
Authority, and **only after** the prerequisite decisions below are authentically recorded. "No
preference" / silence is **not** an authorization and never starts the pilot. The AI workflow does
not and cannot sign this record or mark it approved.

**Scope of this authorization (maximum):** an **internal, LumenAI-owned, synthetic-data-only**
research pilot, **research-only, not clinically validated**. This record **cannot** authorize real
patient data, institution-controlled data, hospital research, production use, or any clinical claim —
those require the separate institution-sponsored prerequisites (`P4_6_GOVERNANCE_APPLICABILITY_MATRIX.md`).

**Reviewed content:** combined code `7c0f679` (via #178 `8574a2a`, 7 CI jobs green incl. PG16);
#176 `fdaee8e`; #177 `b35e552`; `main` `0f2ec588` (unchanged). No code changed by P4.6.

---

## 1. Prerequisite decisions (must all be recorded before authorization)

| # | Prerequisite | Record / authority | Required for | Status |
|---|--------------|--------------------|--------------|--------|
| P-1 | RGI-01 (synthetic) LumenAI data authorization | `P4_6_SYNTHETIC_GOVERNANCE_DECISIONS.md` §C / Synthetic Data-Governance Owner | Any synthetic dataset use | **OPEN** |
| P-2 | RGI-02 internal reviewer framework | same doc §C / Release Authority | Any reported synthetic metric | **OPEN** |
| P-3 | RGI-10 scientific-methodology decision | `P4_6_RGI10_METHODOLOGY_DECISION_RECORD.md` §4 / Methodology Reviewer | Any reported pixel metric | **OPEN** |
| P-4 | SEC-174-02 disposition | `P4_6_INDEPENDENT_SECURITY_REVIEW_REQUEST.md` / **non-author** reviewer | Security axis | **OPEN** |
| P-5 | SEC-175-01 independent review | same doc + `P3_SECURITY_REVIEW_HANDOFF.md` / **non-author** reviewer | Security axis | **OPEN** |
| P-6 | Readiness checklist fully PASS | `P4_6_SYNTHETIC_PILOT_READINESS_CHECKLIST.md` / pilot operator | Operational readiness | **OPEN** |
| P-7 | Dataset manifest `Verified-Permitted` for each dataset | `P4_6_SYNTHETIC_DATASET_MANIFEST.md` / Data-Governance Owner | Data admission | **OPEN** |
| P-8 | RK-04 artifact-inventory condition satisfied | risk register / Release Authority | Artifact safety | **OPEN** |

**Decision rule:** authorize **only if** P-1, P-2 (if metrics reported), P-3 (if pixel metrics
reported), **P-4 and P-5 (always, non-author)**, P-6, P-7, and P-8 are recorded and acceptable. P-4
and P-5 **cannot** be satisfied by the author, CI, Codex, or an internal LumenAI reviewer who fails
the non-author test. Any unmet always-required prerequisite ⇒ **HOLD**.

## 2. Release Authority decision (DO NOT prepopulate)
| Field | Value |
|---|---|
| Release Authority (name / role) | |
| Authority authenticated (how) | |
| Confirms P-1…P-8 recorded & acceptable (list refs) | |
| Independent security disposition reviewed (SEC-174-02 / SEC-175-01 refs) | |
| Scope authorized | **Internal synthetic-only research pilot (research-only)** — nothing beyond |
| Explicitly NOT authorized | Real/institutional data; hospital research; production; clinical/FDA claims |
| Conditions / monitoring | |
| Stop-condition acknowledgement (CHARTER §4) | |
| Decision (AUTHORIZE synthetic pilot / HOLD / REJECT) | |
| Effective / review date | |
| Date | |
| Signature or authenticated approval reference | |

## 3. Current consolidated status
- Prerequisites recorded: **none** (P-1…P-8 OPEN).
- Security independence: **unmet** (no non-author disposition recorded).
- **Determination: HOLD — the synthetic pilot is NOT authorized.** This holds until the Release
  Authority completes §2 on the basis of authentically recorded prerequisites.

*Engineering completion is not governance authorization. No authorization, waiver, or SEC closure is
issued by this record or by the AI workflow. The final pilot-readiness re-assessment is performed
only after these decisions are recorded — not before.*
