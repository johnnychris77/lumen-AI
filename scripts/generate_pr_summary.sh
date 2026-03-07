#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/generate_pr_summary.sh path/to/task.md"
  exit 1
fi

TASK_FILE="$1"

if [ ! -f "$TASK_FILE" ]; then
  echo "Task file not found: $TASK_FILE"
  exit 1
fi

mkdir -p .ai/pr

TITLE="$(awk -F': ' '/^# Task:/{print $2}' "$TASK_FILE" | head -n 1)"
OWNING_AGENT="$(awk '/## Owning Agent/{getline; print $0}' "$TASK_FILE" | tr -d '\r')"
RELEASE_IMPACT="$(awk '/## Release Impact/{getline; print $0}' "$TASK_FILE" | tr -d '\r')"

CHANGED_FILES="$(git diff --name-only HEAD~1..HEAD 2>/dev/null || true)"
if [ -z "$CHANGED_FILES" ]; then
  CHANGED_FILES="No changed files detected from HEAD~1..HEAD"
fi

PR_FILE=".ai/pr/$(date +%Y%m%d_%H%M%S)_${TITLE// /-}.md"

cat > "$PR_FILE" <<PR
# Pull Request Draft

## Title
${TITLE}

## Summary
Implemented task ${TITLE} using the ${OWNING_AGENT} agent workflow.

## Why This Change
This PR advances the task defined in:
${TASK_FILE}

## Scope
- task-driven implementation
- agent-aligned change set
- validation-ready PR packaging

## Files Touched
$(printf '%s\n' "$CHANGED_FILES" | sed 's/^/- /')

## Validation
- review the linked task validation plan
- attach actual commands and results before merge

## Risks
- validation evidence may still need to be added manually
- reviewer must confirm changed file scope matches task

## Release Impact
${RELEASE_IMPACT:-none}

## Rollback Plan
Revert this PR commit and rebuild the stack.

## Linked Task
${TASK_FILE}
PR

echo "Generated PR draft: $PR_FILE"
