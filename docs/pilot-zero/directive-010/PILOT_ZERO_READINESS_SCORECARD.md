# LPZ-DIR-010 — Pilot Zero Readiness Scorecard

**Purpose:** quantitative, evidence-based readiness by category (0–100). Scores
reflect the review; they are honest assessments, not targets.

## Scoring bands

* **PASS:** ≥ 85
* **CONDITIONAL:** 65–84
* **FAIL:** < 65

A category < 65 that is **safety- or execution-critical** (Laboratory, Dataset
Quality, AI Governance, Security) forces at most **GO WITH CONDITIONS** and, if
Security or a safety gate fails, **NO-GO**.

## Scores

| # | Category | Score | Band | Basis |
|---|---|---|---|---|
| 1 | Architecture | 90 | PASS | Frozen, inventoried, ADR-backed, API-cataloged |
| 2 | Engineering | 78 | CONDITIONAL | Strong security/tests/recovery; CI disabled (ERR-1), gates not in code (ERR-2) |
| 3 | Security | 86 | PASS | Directive 002 passed; secured writes; tenant isolation; audit; secrets hygiene |
| 4 | Laboratory | 45 | FAIL | Framework complete; **physical lab not built / not qualified** (LRR-1) |
| 5 | Documentation | 80 | CONDITIONAL | Extensive; 005 not consolidated (SRR-1), 009 unmerged (SRR-2) |
| 6 | Governance | 88 | PASS | 006/007/008 frameworks complete + audit, largely in code |
| 7 | Dataset Quality | 55 | FAIL | Governance defined; **no acquired images / no certified dataset yet** (DGR-3) |
| 8 | AI Governance | 80 | CONDITIONAL | 009 framework strong; enforcement + first experiment pending (AGR-2/3) |
| 9 | Operations | 72 | CONDITIONAL | Backup/DR/monitoring executed; operator training/lab ops pending |
| 10 | Risk | 75 | CONDITIONAL | Register current; open highs are execution prerequisites |

## Weighted overall

Equal-weight mean of the ten categories: **(90+78+86+45+80+88+55+80+72+75)/10 =
74.9 → 75/100**.

**Overall band: CONDITIONAL (65–84).**

## Interpretation

* **Framework, governance, security, and architecture are PASS-level and mature.**
* **Two categories FAIL (Laboratory 45, Dataset Quality 55)** — both because the
  program has not yet moved from *specification* to *physical execution* (no lab, no
  acquired data). These are the decisive constraints.
* No safety-critical **defect** exists; the low scores are *absence of executed
  physical work*, which is appropriate at the end of a documentation-and-governance
  program and is precisely what Pilot Alpha stand-up is meant to deliver.

**Scorecard conclusion:** overall **75/100 (CONDITIONAL)** → **GO WITH CONDITIONS**
(see `GO_NO_GO_DECISION_FRAMEWORK.md`). The conditions target Laboratory and Dataset
Quality (raise each to ≥ 80 by executing lab stand-up + acquisition) and the
Engineering/Documentation/AI-Governance enforcement and consolidation items.
