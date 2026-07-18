# LPZ-DIR-010 — Program Risk Register

**Purpose:** consolidated Pilot Zero risk register. Probability (P) and Impact (I)
are Low/Med/High. Status reflects the review.

| ID | Category | Risk | P | I | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| R-01 | Laboratory | Physical lab not built; no qualified hardware | High | High | Stand up lab; IQ/OQ/PQ; sign readiness checklist (LRR-1) | PMO / Lab Lead | Open |
| R-02 | Data | No governed images/datasets acquired yet | High | High | Execute acquisition post-lab; validate one end-to-end dataset | CQO | Open |
| R-03 | Technical | Governance gates documented, not enforced in code | Med | High | Implement 006–009 High-priority enforcement | CTO | Open |
| R-04 | Operational | CI/CD disabled; no automated merge gating | Med | Med | Activate CI (suite + ruff + build) | CTO | Open |
| R-05 | Documentation | Directive 005 doc set not consolidated on main | Med | Med | Locate/restate Directive 005 deliverables | PMO | Open |
| R-06 | Documentation | Directive 009 docs on open PR, not merged | Low | Med | Merge PR #106 | PMO | Open |
| R-07 | AI | Candidate model quality/bias unknown (none trained) | Med | High | Governed experiment + stratified eval before any pilot use | Chief AI | Open (expected) |
| R-08 | Security | Regression on secured writes / tenant isolation | Low | High | Governance regression tests; keep Security Gate green | CISO | Mitigated |
| R-09 | Compliance | Misread of governance as regulatory/clinical approval | Low | High | Explicit no-claim guardrails in every doc | CQO / Legal | Mitigated |
| R-10 | AI safety | AI output treated as autonomous clinical decision | Low | High | Decision-support-only, fail-closed, human review mandated | Chief AI | Mitigated |
| R-11 | Data integrity | Evidence drift vs. manifest/checksum | Low | Med | `image_sha256` + manifest verification (008) | CQO | Mitigated |
| R-12 | Operational | Operators untrained for acquisition/review | Med | Med | Training per SOPs before acquisition | Lab Lead | Open |
| R-13 | Project | Scope creep beyond frozen v1.0 architecture | Low | Med | Freeze restated each directive; doc-only directives | PMO | Mitigated |
| R-14 | Data | PHI ingress into images/metadata | Low | High | Instrument-only lab; no-PHI guardrail every spec | CISO / CQO | Mitigated |
| R-15 | Operational | Backup/DR unproven at pilot scale | Low | Med | Executed restore + DR drill with measured RTO/RPO (foundation) | CTO | Mitigated |

## Summary

* **Open, high-impact:** R-01 (lab), R-02 (no data), R-03 (enforcement), R-07 (model
  quality) — these define the conditions for a data-acquiring Pilot Alpha.
* **Mitigated:** security/tenant isolation, compliance-claim, AI-autonomy, PHI,
  data-integrity, DR — the safety and governance guardrails are in force.
* **No unmitigated safety-critical risk** is present in the documentation/framework
  posture; the open highs are execution prerequisites, not defects.
