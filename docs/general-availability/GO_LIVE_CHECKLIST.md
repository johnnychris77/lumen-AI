# Go-Live Checklist — LumenAI Version 1.0

**Release decision:** CONDITIONAL GO (narrow, disclosed pilot only) / NO GO
(unconditional GA). See `GENERAL_AVAILABILITY_REPORT.md` for full
evidence. This checklist is the itemized remediation plan Section 10 of
the GA program requires.

## Blocking issues (must close before ANY real customer engagement, including a disclosed pilot)

| # | Blocking issue | Owner | Risk if unaddressed | Remediation plan | Target |
|---|---|---|---|---|---|
| 1 | No BAA/MSA/DPA/ToS/Privacy Policy text exists anywhere | Legal / Product | Cannot lawfully process a real customer's data; every pilot doc assumes these exist | Draft real agreements starting from `docs/data-governance/pilot-data-governance.md`'s real retention/PHI/breach-notification content; legal counsel review | Before pilot signature |
| 2 | Live inference path never calls the Genesis-trained model | Engineering / ML | Governance ladder validates a model nobody's inspection actually uses; pilot would silently run the deterministic placeholder | Wire a promoted (`candidate_stage="Pilot"`) model's weights into `app/ai/inference.py`'s prediction path, behind the existing `deployment_gates` capability check | Before pilot start |
| 3 | No real facility has ever run the Advisory pilot | Clinical / Customer Success | Every "pilot evidence" claim is currently either a unit-test fixture or a synthetic seed script | Select one pilot site under condition #1's agreements; run Advisory Mode for the duration in `PilotStatus.pilot_duration_days`; do not claim pilot completion until real `SupervisorReview`/`AdvisoryRecommendationInteraction` rows exist | Pilot window |
| 4 | No backup has ever been taken or restored | Engineering / Ops | Total data loss on any DB failure with no recovery path | Implement and execute the procedure in `docs/deployment/backup-restore-guide.md`; run one full restore-to-scratch drill and record results | Before pilot start |
| 5 | No security incident-response runbook exists | Security | No defined process if a real incident occurs during a pilot handling real facility data | Author a runbook (severity classification, notification timeline, containment steps); this is explicitly listed as open in the project's own compliance control matrix | Before pilot start |
| 6 | Encryption-at-rest is claimed in `docs/global/global-security-readiness.md` with no corresponding code | Security / Legal | A customer-facing security claim would be false | Correct the document immediately regardless of release decision; implement real field-level encryption before any claim is restated, or remove the claim | Immediate (document correction), before pilot (implementation) |
| 7 | Pricing is unapproved and contradicts itself across 4 sources | Commercial / Product | Cannot issue a real quote or contract | Reconcile `docs/commercial/pricing-strategy.md`, `docs/global/global-commercialization-plan.md`, `backend/app/routes/commercial.py`, and the frontend subscription page into one approved source of truth | Before pilot signature |
| 8 | No alerting is automatically triggered — a human must check a dashboard or a Forge rule must fire | Engineering / Ops | A real safety event or system failure during a pilot could go unnoticed | Configure `LUMENAI_ALERTS_ENABLED` and the relevant channel env vars for the pilot tenant; wire `pulse_alert_service`'s trend alerts to `notifier.dispatch_alert`; define an on-call rotation, even an informal one, for the pilot's duration | Before pilot start |

## Should-close before a SECOND pilot or broader rollout (not blocking for the first narrow pilot)

| # | Issue | Owner | Remediation | Target |
|---|---|---|---|---|
| 9 | No load-testing has ever been performed | Engineering | Run a load test against realistic pilot-scale traffic before accepting a second, larger site | Before pilot #2 |
| 10 | High availability is design-only (single instance in the exercised deployment path) | Engineering | Acceptable for one small pilot; required before any multi-site commitment | Before broader rollout |
| 11 | Rollback has never been validated | Engineering | Execute one real rollback drill (app + one Alembic downgrade) in a non-production environment | Before pilot #2 |
| 12 | Tenant-isolation automated test coverage is incomplete (SEC-002, open) | Security | Close the specific gap the risk register already tracks | Before onboarding a second tenant |
| 13 | Customer Health Score formula and onboarding timeline disagree across docs | Customer Success | Pick one canonical version, update all references | Before customer-facing distribution |
| 14 | No Dependabot config despite one doc claiming otherwise | Engineering | Either add `dependabot.yml` or correct the doc | Low urgency, correct either way |

## Verified GREEN items (real evidence, no action needed)

- ✓ Authentication (bcrypt + JWT + OIDC), RBAC enforcement, secrets issuance/hashing, hash-chained audit logging
- ✓ CI-blocking dependency vulnerability scanning (has already caught a real CVE)
- ✓ Pilot-to-production KPI conversion logic (`pilot_service.py`)
- ✓ Full backend regression suite: 3516 passed, 2 skipped, 0 failed
- ✓ Frontend build clean; `ruff check` clean
- ✓ Human-oversight invariant (`human_review_required: true`, no auto-approval anywhere) verified structurally throughout Genesis/Shadow/Advisor
- ✓ Known limitations already honestly documented in multiple places (consolidated in `KNOWN_LIMITATIONS.md`)

## What a passing checklist looks like

Every row in the "Blocking issues" table above must move to a dated,
evidenced "closed" state — with a link to the real artifact (signed
agreement, drill report, dashboard screenshot showing an alert firing) —
before the release decision can be revised from CONDITIONAL GO to GO.
