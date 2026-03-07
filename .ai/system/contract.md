# LumenAI Autonomous Engineering System Contract

## Mission
Turn the LumenAI repository into a repo-native, agent-assisted engineering system that can plan, build, review, test, and release with minimal manual relay.

## Source of Truth
GitHub is the only source of truth.
No code may exist only inside containers or local scratch paths.

## Core Principles
- One active backend architecture
- One explicit runtime path
- One shared DB contract
- No silent sqlite fallback in shared runtime
- No duplicate active code trees
- Every issue must have acceptance criteria
- Every PR must include validation notes
- No direct feature commits to main

## Required Runtime Rules
- API and worker must share the same DATABASE_URL and REDIS_URL
- Missing required env vars must fail loudly
- CI must be green before release
- Every release must map to a tag and published image

## Agent Roles
- Architect Agent
- Backend Agent
- Frontend Agent
- ML Agent
- DevOps Agent
- QA Release Agent

## Execution Policy
1. Architect shapes the task
2. Specialist agent builds
3. Reviewer checks
4. QA validates
5. Release agent summarizes impact

## Done Means
- code in repo
- tests or validation evidence
- Docker/runtime compatibility preserved
- docs updated if needed
- issue acceptance criteria satisfied
