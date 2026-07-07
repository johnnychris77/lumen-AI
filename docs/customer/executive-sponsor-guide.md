# Executive Sponsor Guide

## Who this is for

The hospital or health-system executive (VP of Perioperative Services,
CNO, Director of Quality, or equivalent) who sponsors the LumenAI
implementation and is accountable for its success internally.

## What the Executive Sponsor needs to know

You do not need to understand the AI architecture in detail. You need to
be able to answer, for your own leadership:

1. **What is LumenAI?** An AI-assisted pre-sterilization clinical
   inspection platform — it helps SPD staff catch contamination, damage,
   and quality issues before instruments proceed to packaging and
   sterilization. It is not a sterilization monitoring system (see
   `docs/architecture/pre-sterilization-boundary.md`).
2. **What does it require of my staff?** Technicians capture images as
   part of their normal inspection workflow; supervisors review AI
   recommendations and either confirm or correct them. No AI
   recommendation is final without a supervisor's sign-off.
3. **What value should I expect, and by when?** See the 30/60/90-day
   plans (`docs/customer/30-day-go-live-plan.md` and following) — Day 30
   is operational go-live, Day 90 is the first quantified value review
   using your own site's data (`docs/customer/90-day-value-realization-plan.md`).
4. **How is patient safety protected?** Every recommendation is
   advisory and explainable (`docs/knowledge-graph/reasoning-engine.md`);
   a human supervisor is the final authority on every disposition
   (`docs/architecture/design-principles.md`, Principle 4).
5. **How is my data protected?** Tenant-isolated, RBAC-gated, fully
   audit-logged (`docs/security/security-compliance-center.md`).

## Your role during implementation

- Name an SPD Champion (`docs/customer/spd-champion-guide.md`) as the
  day-to-day operational owner — the Executive Sponsor is the escalation
  path and business-value owner, not the daily operator.
- Attend the Day 30, Day 60, and Day 90 checkpoint reviews.
- Clear organizational blockers (staffing, training time, department
  buy-in) that are outside the SPD Champion's authority to resolve.
- Review the value realization package at Day 90 and decide on expansion
  (additional sites, instrument families, or edition upgrade — see
  `docs/enterprise/commercial-packaging.md`).

## Reporting you'll receive

- Weekly status during Days 1–30 from the LumenAI implementation team.
- The Executive Command Center dashboard (frontend) and
  `/api/cios/dashboard` for a live, self-service view of system health,
  readiness, and risk indicators at any time.
- A formal value realization package at Day 90
  (`docs/customer/90-day-value-realization-plan.md`), and quarterly
  thereafter.

## Escalation

Any blocker risking the go-live timeline, or any critical safety-queue
item unresolved beyond 48 hours, should reach you within one business
day — confirm this escalation path is set up correctly with your LumenAI
implementation lead during kickoff.
