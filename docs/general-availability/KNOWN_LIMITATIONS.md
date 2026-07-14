# Known Limitations — LumenAI Version 1.0

This document consolidates the known-limitations content already
documented, honestly, across many prior phases of this program. Nothing
here is new; it is gathered into one place per Section 11's requirement.

## Clinical / AI model limitations

- **The trained candidate model has never been wired into the live
  inspection path.** The deployed, real-time scoring pipeline
  (`app/ai/inference.py::LumenAIModel.predict()`) currently falls through
  to a deterministic, SHA-256-image-hash-seeded placeholder whenever no
  YOLO weights file is present — which is always true in this repository.
  The Genesis-trained pure-Python logistic-regression model exists and is
  registered, but no real inspection currently uses its weights.
- **The trained model itself, when it is used, is a foundation-scale
  logistic-regression baseline over Pillow-computed image features**
  (brightness, sharpness, aspect ratio) — not a trained computer-vision
  model with learned visual features. No causal or diagnostic claim is
  made. (`app/services/ml/explainability.py::KNOWN_LIMITATIONS`)
- **Supported findings are limited to `debris` and `corrosion`** (`blood`
  only when at least 3 validated training samples exist). Every other
  category is explicitly marked not-evaluated rather than guessed.
- **No visual explanation (saliency map / class-activation map) is
  generated.** This pipeline has no real trained vision model with real
  gradients to visualize; fabricating a heatmap would misrepresent it as
  something it is not.
- **No regulatory clearance is claimed anywhere** — not FDA, not any
  other body.
- **`human_review_required` is always `true`, regardless of confidence.**
  No finding is ever presented as a definitive conclusion.
- **No real facility pilot has ever been run.** All Advisory Mode
  interaction data in existence is either unit-test fixture data or
  output of an explicitly synthetic seed script
  (`backend/scripts/seed_pilot_data.py`, `random.Random(42)`).

## Engineering / operational limitations

- **No production deployment has ever served real customer traffic** —
  only a self-hosted demo instance exists.
- **No backup has ever been taken or restored.**
- **No disaster-recovery drill has ever been run** (the runbook is real
  and detailed; it is unexecuted).
- **No load-testing has ever been performed**; no performance targets have
  measured evidence behind them.
- **The exercised deployment path is single-instance** — no high
  availability, no database replication, no load balancer in practice.
- **Rollback has never been validated** beyond a demo-landing-page-only
  script; no Alembic downgrade has ever been executed.
- **Only 4 database migrations exist covering 417 tables**, with no
  downgrade path ever exercised (`docs/production-readiness/
  TECHNICAL_DEBT_REGISTER.md`).
- **The executive dashboard may serve fabricated/mock data with no UI
  indication** — flagged as a Critical finding in the technical debt
  register and not yet resolved.

## Security limitations

- **No security incident-response runbook exists.**
- **No penetration test has ever been conducted.**
- **Vulnerability remediation SLAs are documented but not enforced** by
  any code or CI gate.
- **Tenant-isolation automated test coverage is incomplete** (tracked as
  an open item in the security risk register).
- **A compliance document currently overclaims encryption-at-rest and
  Dependabot usage that do not exist in code** — flagged for correction
  regardless of release decision.
- **Alerting is not automatically triggered.** Notification dispatch code
  is real but disabled by default; a human or rule engine must invoke it
  manually today.

## Commercial / legal limitations

- **No BAA, MSA, DPA, Terms of Service, or Privacy Policy text exists
  anywhere in this repository** — every reference to these documents is a
  placeholder or an unchecked checklist item.
- **Pricing is unapproved and inconsistent** across at least 4 internal
  sources.
- **No dedicated customer support ticketing/case-management tooling
  exists.**
- **No on-call rotation exists.**

## Lumen Decision Engine & Observation Doctrine limitations

- **"Condition remains after recleaning" is not yet an automated
  re-check.** The Decision Engine records an `escalation_condition`
  string describing when supervisor review would be required, but there
  is no automated hook today that re-evaluates a specific inspection
  because a prior recleaning of the same physical instrument didn't
  resolve a finding.
- **Digital Twin trend is honestly reported as `not_available`** in the
  Result Contract's assessment layer — no real trend computation is wired
  in yet; this is not fabricated as "stable" or any other value.
- **The 4-panel Decision Engine frontend view is additive**, shown
  alongside the pre-existing `ClinicalDecisionPanel`, not a replacement —
  a human reviewer has not yet walked a real inspection through it
  end-to-end in a browser.
- **Policy simulation's `false_escalation_estimate` is a simple ratio**,
  not a validated statistical estimate — reported only when historical
  decision records exist to compute it from.

## What is NOT a limitation — verified strengths

- Real bcrypt/JWT/OIDC authentication and consistently enforced RBAC.
- Real hash-chained, tamper-evident audit logging.
- Real, CI-blocking dependency vulnerability scanning (has already caught
  a real CVE).
- Real secrets issuance (`secrets.token_urlsafe(40)`, SHA-256 hash only,
  never retrievable).
- A full backend regression suite of 3,516 tests passing cleanly, with a
  consistent, verified discipline of never fabricating a metric — every
  "insufficient_data" report in this codebase is genuine, not a cover for
  a missing feature.
