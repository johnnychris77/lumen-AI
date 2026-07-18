# LPZ-DIR-010 — GO / NO-GO Decision Framework

**Purpose:** define the formal criteria, required evidence, approvals, and sign-off
for the Pilot Alpha entry decision. The decision is based **solely on documented
evidence**. This framework authorizes **no** clinical deployment, **no** production
AI, and **no** regulatory-approval claim.

## Decision options

### GO
* **Meaning:** proceed to Pilot Alpha execution (data-acquiring) without conditions.
* **Required evidence:** all ten scorecard categories ≥ 85; the full Acceptance Test
  Plan passing; `LAB_READINESS_CHECKLIST.md` signed; a readiness-certified dataset
  and a governed experiment record exist.
* **Approvals:** CEO, CTO, CQO, CISO, Chief AI Officer, PMO Lead (unanimous).
* **Outstanding actions:** none.
* **Acceptance criteria:** no open High risk; no FAIL category.

### GO WITH CONDITIONS
* **Meaning:** proceed to a **controlled Pilot Alpha stand-up** (planning +
  laboratory build + enforcement), with data-acquiring execution gated on named
  conditions closing.
* **Required evidence:** overall CONDITIONAL (65–84); no Security or safety FAIL; all
  conditions have owners, acceptance criteria, and target dates.
* **Approvals:** CTO, CQO, CISO, Chief AI Officer, PMO Lead (PMO tracks conditions;
  CEO informed).
* **Outstanding actions:** the condition list below.
* **Acceptance criteria:** each condition is independently verifiable and closes
  before the corresponding execution step.

### NO-GO
* **Meaning:** do not proceed; remediate first.
* **Triggers:** Security category FAIL; any unmitigated safety-critical defect; a
  false-PASS/contamination-safety regression; or ≥ 3 categories FAIL with no
  credible remediation path.
* **Approvals:** any one of CISO / CQO / CEO may issue NO-GO.
* **Outstanding actions:** remediation plan required before re-review.

## This review's decision

**GO WITH CONDITIONS.** Overall readiness **75/100 (CONDITIONAL)**; Security PASS;
governance/architecture PASS; no safety-critical defect. Two categories FAIL
(Laboratory 45, Dataset Quality 55) because physical execution has not begun — these
become the primary conditions.

## Conditions (must close before the gated step)

| # | Condition | Gates | Owner | Acceptance |
|---|---|---|---|---|
| C-1 | Build + qualify the physical lab (IQ/OQ/PQ); sign `LAB_READINESS_CHECKLIST.md` | Any data acquisition | Lab Lead / PMO | Signed READY; Laboratory ≥ 80 |
| C-2 | Acquire governed images; build + readiness-certify one dataset end-to-end | Dataset/experiment work | CQO | AT-01/02 pass; Dataset Quality ≥ 80 |
| C-3 | Enforce High-priority governance gates in code (006–009: GT-gating, SoD, dataset immutability, first-class experiment) | AT-04/06/07/08 | CTO | Gates enforced; tests pass |
| C-4 | Activate CI (backend suite + ruff + build) on every PR | Merge gating | CTO | CI green on PRs |
| C-5 | Consolidate Directive 005 deliverables on `main` | Documentation completeness | PMO | 005 doc set present |
| C-6 | Merge Directive 009 documentation (PR #106) | AI-governance baseline | PMO | 009 on `main` |
| C-7 | Train operators per SOPs; record training | Lab operation | Lab Lead | Training records archived |

## Executive sign-off requirements

Pilot Alpha stand-up under GO WITH CONDITIONS requires recorded sign-off from the
**CTO, CQO, CISO, Chief AI Officer, and PMO Lead**, with the **CEO** informed and the
condition register (C-1…C-7) owned by the PMO. Transition from stand-up to
**data-acquiring** Pilot Alpha requires C-1, C-2, and C-3 closed and re-scored to
overall ≥ 80. No sign-off in this framework authorizes clinical use or production
deployment.
