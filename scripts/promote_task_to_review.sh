#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/promote_task_to_review.sh path/to/task.md"
  exit 1
fi

TASK_FILE="$1"

if [ ! -f "$TASK_FILE" ]; then
  echo "Task file not found: $TASK_FILE"
  exit 1
fi

mkdir -p .ai/tasks/review
mkdir -p .ai/pr

BASENAME="$(basename "$TASK_FILE")"
DEST=".ai/tasks/review/${BASENAME}"

mv "$TASK_FILE" "$DEST"
echo "Moved task to review: $DEST"

if [ -x scripts/generate_pr_summary.sh ]; then
  echo "Generating PR draft..."
  ./scripts/generate_pr_summary.sh "$DEST"
else
  echo "PR generator script not found or not executable: scripts/generate_pr_summary.sh"
fi
