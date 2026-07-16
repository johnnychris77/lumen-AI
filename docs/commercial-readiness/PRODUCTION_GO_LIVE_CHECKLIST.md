# LumenAI — Production Go-Live Checklist

The Validation section's 9 checkmarks, made literal and tied to specific, verified findings from this document set and from Phases 1/3/4/5 — not a generic go-live template.

## ✓ Production environment deploys successfully

- [ ] Confirm Render deployment (the only real, operational path — see `docs/commercial-readiness/DEPLOYMENT_GUIDE.md`) is current; do not assume Kubernetes/Helm are viable alternates, since neither has ever been applied to a real cluster.
- [ ] Fix the root `Dockerfile`'s missing `$PORT` default and the `docker/Dockerfile.worker` placeholder stub before relying on the GHCR tag-triggered release pipeline.
- [ ] Confirm `docker-compose.prod.yml`'s full stack boots cleanly — this is the one path already exercised in CI (`enterprise-quality-gate.yml`), so re-run it immediately before go-live rather than assuming last week's green run still holds.

## ✓ Backup and recovery procedures tested

- [ ] **This checkbox cannot honestly be checked yet.** No backup or restore script exists anywhere in this repository, and no restore drill has ever been executed, per `DEPLOYMENT_GUIDE.md`. Write and run one real backup/restore cycle before checking this box for a real customer's data.

## ✓ Monitoring operational

- [ ] Point the deployment's health check at `/ready` (real DB-connectivity check), not `/api/health`/`/health` (unconditional 200-OK stubs) — the current Render config uses the latter.
- [ ] Note honestly that `/metrics` is minimal (request count + uptime only) and that the Prometheus/Grafana config files in `observability/` are not wired into any running service — do not present full observability as operational until this gap is closed.

## ✓ Support documentation complete

- [ ] Confirm `docs/commercial-readiness/SUPPORT_OPERATIONS_MANUAL.md`'s severity/SLA table is distributed to the actual support team, and that the security-incident-response gap (no runbook exists, per `LEGAL_GOVERNANCE_PACKAGE.md`) is explicitly acknowledged as out of scope for Level 1-3 product support, not silently assumed to be covered.

## ✓ Onboarding workflow validated

- [ ] Walk a test tenant through `docs/commercial-readiness/CUSTOMER_ONBOARDING_GUIDE.md`'s full sequence end to end, including SSO setup, before the first real customer does.
- [ ] Confirm the BAA/MSA/DPA checklist items in the onboarding sequence are flagged as **not yet real documents** (per `LEGAL_GOVERNANCE_PACKAGE.md`) so onboarding doesn't stall on a signature step for a document that doesn't exist to sign.

## ✓ Pilot environment operational

- [ ] Re-run `backend/scripts/seed_pilot_data.py` immediately before the pilot begins (deterministic seed, per `docs/demo-program/SYNTHETIC_DATA_GUIDE.md`).
- [ ] Confirm `PilotSiteConfig`/`PilotStatus` are correctly provisioned for the specific pilot tenant per `docs/commercial-readiness/PILOT_IMPLEMENTATION_PLAN.md`.

## ✓ Customer documentation complete

- [ ] Confirm the Administrator/Technician/Supervisor/Director guides (split across `docs/demo-program/CUSTOMER_SUCCESS_PLAYBOOK.md` and `docs/demo-program/TRAINING_GUIDE.md` from Phase 5) are current against the live product, especially the honest caveat that a working supervisor approve/return UI action was not located during the UX review — do not distribute a Supervisor Guide that assumes this control exists without first verifying it's been built.

## ✓ Commercial materials approved

- [ ] **This checkbox cannot honestly be checked yet.** Per `docs/commercial-readiness/PRICING_MODEL.md`, at least three internal pricing documents disagree on tier names and dollar figures, and `docs/commercial/launch-readiness-checklist.md` itself states pricing approval is still "In Progress." Do not present pricing as final to a real prospect until this reconciliation is complete and formally signed off.

## ✓ Go-live checklist completed

- [ ] This document itself, run in full, immediately before the specific go-live date — not as a one-time exercise weeks in advance.

## Overall status

Of these 9 validation items, **2 cannot honestly be marked complete today** (backup/recovery testing, commercial materials approval) and at least 3 more require a specific fix or reconciliation before they can be checked (monitoring health-check target, onboarding's BAA/MSA/DPA gap, customer documentation's supervisor-approval caveat). See `docs/commercial-readiness/FINAL_READINESS_REPORT.md` for the consolidated Go/Conditional-Go/No-Go verdict across this and the three prior phase scorecards.
