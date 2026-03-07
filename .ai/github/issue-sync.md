# GitHub Issue to Task Sync

## Purpose
Convert GitHub issues into repo-native orchestrator task files under `.ai/tasks/open/`.

## Why
This creates a consistent bridge between GitHub planning and LumenAI agent execution.

## Rules
- Every synced issue becomes one markdown task file.
- Filename format:
  `YYYYMMDD_HHMMSS_issue-<number>-<slug>.md`
- Issue title and body are preserved as the source planning context.
- Owning agent is inferred from labels when possible.

## Agent Mapping Heuristics
- label `backend` -> backend
- label `frontend` -> frontend
- label `ml` -> ml
- label `infra` or `devops` -> devops
- label `qa` or `release` -> qa-release
- otherwise -> architect

## Output
A task file in `.ai/tasks/open/` with:
- GitHub issue reference
- owning agent
- title
- problem
- goal
- scope
- acceptance criteria placeholder
- release impact placeholder
