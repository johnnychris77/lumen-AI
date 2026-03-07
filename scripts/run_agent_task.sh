#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/run_agent_task.sh path/to/task.md"
  exit 1
fi

TASK_FILE="$1"

if [ ! -f "$TASK_FILE" ]; then
  echo "Task file not found: $TASK_FILE"
  exit 1
fi

OWNING_AGENT="$(awk '/## Owning Agent/{getline; print $0}' "$TASK_FILE" | tr -d '\r')"

echo "======================================"
echo "LumenAI Agent Orchestrator"
echo "Task: $TASK_FILE"
echo "Owning Agent: $OWNING_AGENT"
echo "======================================"
echo

case "$OWNING_AGENT" in
  architect)
    AGENT_FILE=".ai/agents/architect.md"
    ;;
  backend)
    AGENT_FILE=".ai/agents/backend.md"
    ;;
  frontend)
    AGENT_FILE=".ai/agents/frontend.md"
    ;;
  ml)
    AGENT_FILE=".ai/agents/ml.md"
    ;;
  devops)
    AGENT_FILE=".ai/agents/devops.md"
    ;;
  qa-release)
    AGENT_FILE=".ai/agents/qa-release.md"
    ;;
  *)
    echo "Unknown agent: $OWNING_AGENT"
    exit 1
    ;;
esac

echo "Use this agent file:"
echo "  $AGENT_FILE"
echo
echo "Task content:"
echo "--------------------------------------"
cat "$TASK_FILE"
echo "--------------------------------------"
echo
echo "Required shared context:"
echo "  .ai/system/contract.md"
echo "  .ai/architecture.md"
echo "  .ai/orchestrator/output-contract.md"
echo
echo "Suggested next step:"
echo "  Feed the task + agent file + shared context into your coding agent."
