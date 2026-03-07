#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/create_task.sh task-name owning-agent"
  exit 1
fi

TASK_NAME="$1"
OWNING_AGENT="${2:-architect}"
DATE_STR="$(date +%Y%m%d_%H%M%S)"
TASK_PATH=".ai/tasks/open/${DATE_STR}_${TASK_NAME}.md"

cat > "$TASK_PATH" <<TASK
# Task: ${TASK_NAME}

## Owning Agent
${OWNING_AGENT}

## Problem

## Goal

## Scope

## Out of Scope

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

echo "Created task: $TASK_PATH"
