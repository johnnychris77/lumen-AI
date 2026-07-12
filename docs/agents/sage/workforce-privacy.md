# Project Sage — Workforce Privacy and Fairness

LumenAI AI Specialist, Section 16.

## What Sage must never do

`sage_workforce_privacy_service.PROHIBITED_ACTIONS` documents the six
safeguards the brief names: no public employee ranking, no disciplinary
action, no protected-characteristic inference, no unvalidated-AI-finding
performance action, no unauthorized individual exposure, no employment
decisions. Nothing in Sage's route layer or service layer performs any of
these — every table's status fields are advisory/educational only.

## Access control

`can_view_individual_competency(role, viewer_identity, subject_identity)` --
true only if the viewer IS the subject (self-view, Section 11) or the
viewer holds an authorized leadership role (`admin`/`spd_manager`). Every
individual-level Sage route (`/gaps`, `/learning-plans`, `/assessments`,
`/executive-summary`) is leadership-only at the route layer
(`require_tenant_roles`); `/my-learning` resolves the learner from the
authenticated identity, never a client-supplied parameter, so a technician
can never request a peer's data through it.

## Access logging

`log_individual_access` routes through the platform's existing hash-chained,
tamper-evident audit trail (`enterprise_audit_service.
record_enterprise_audit_event`) rather than a new, weaker log table --
every individual-level gap-detection call is recorded there.

## Executive aggregates only

`sage_executive_intelligence_service.executive_workforce_intelligence`
returns counts and rates grouped by domain/instrument-family/anatomy-zone
only — no technician name ever appears in that summary.
