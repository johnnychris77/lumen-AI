#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/sync_github_issue_to_task.sh ISSUE_NUMBER"
  exit 1
fi

ISSUE_NUMBER="$1"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is not installed."
  exit 1
fi

mkdir -p .ai/tasks/open

TITLE="$(gh issue view "$ISSUE_NUMBER" --json title -q .title)"
BODY="$(gh issue view "$ISSUE_NUMBER" --json body -q .body)"
LABELS_RAW="$(gh issue view "$ISSUE_NUMBER" --json labels -q '.labels[].name' 2>/dev/null || true)"

SLUG="$(printf '%s' "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//;s/-$//')"
STAMP="$(date +%Y%m%d_%H%M%S)"

OWNING_AGENT="architect"

if printf '%s\n' "$LABELS_RAW" | grep -qi '^backend$'; then
  OWNING_AGENT="backend"
elif printf '%s\n' "$LABELS_RAW" | grep -qi '^frontend$'; then
  OWNING_AGENT="frontend"
elif printf '%s\n' "$LABELS_RAW" | grep -qi '^ml$'; then
  OWNING_AGENT="ml"
elif printf '%s\n' "$LABELS_RAW" | grep -Eqi '^(infra|devops)$'; then
  OWNING_AGENT="devops"
elif printf '%s\n' "$LABELS_RAW" | grep -Eqi '^(qa|release)$'; then
  OWNING_AGENT="qa-release"
fi

TASK_FILE=".ai/tasks/open/${STAMP}_issue-${ISSUE_NUMBER}-${SLUG}.md"

cat > "$TASK_FILE" <<TASK
# Task: ${SLUG}

## GitHub Issue
#${ISSUE_NUMBER}

## Source Title
${TITLE}

## Owning Agent
${OWNING_AGENT}

## Problem
${BODY}

## Goal
Translate GitHub issue #${ISSUE_NUMBER} into an executable LumenAI orchestrator task.

## Scope
- implement issue-defined change
- preserve repo architecture
- route execution to ${OWNING_AGENT}

## Out of Scope
- unspecified feature expansion
- unrelated refactors unless required for correctness

## Acceptance Criteria
- [ ]
- [ ]
- [ ]

## Validation Plan
- command
- command

## Release Impact
none
TASK

echo "Created task: $TASK_FILE"
echo "Owning agent: $OWNING_AGENT"
