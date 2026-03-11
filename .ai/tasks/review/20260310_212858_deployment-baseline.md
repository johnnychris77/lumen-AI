# Task: deployment-baseline

## Owning Agent
devops

## Problem
LumenAI runs locally in Docker, but it does not yet have a deployment-ready baseline for staging or investor demos.

## Goal
Prepare a deployment baseline with environment configuration, container workflow expectations, and a path to staging deployment.

## Scope
- environment variable review
- container readiness review
- deployment doc/runbook
- staging assumptions
- image/run command consistency

## Out of Scope
- full cloud provisioning
- production HA architecture
- enterprise security hardening

## Acceptance Criteria
- [ ] deployment assumptions are documented
- [ ] required env vars are clear
- [ ] Docker runtime is consistent for staging use
- [ ] health verification steps are documented
- [ ] repo has a clear deploy baseline

## Validation Plan
- rebuild stack
- validate health scripts
- verify required env vars
- verify operator runbook

## Release Impact
minor
