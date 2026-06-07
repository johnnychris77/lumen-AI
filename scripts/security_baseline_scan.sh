#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== LumenAI Security Baseline Scan ==="

echo ""
echo "=== Backend: activate environment ==="
cd "$ROOT_DIR/backend"

if [ -f "/home/ohna/lumen-ai/lumen-AI/.venv-backend/bin/activate" ]; then
  source /home/ohna/lumen-ai/lumen-AI/.venv-backend/bin/activate
fi

export DATABASE_URL="${DATABASE_URL:-sqlite:///./lumenai.db}"
export PYTHONPATH="${PYTHONPATH:-.}"

echo ""
echo "=== Backend: install scan tools if missing ==="
python -m pip install --upgrade pip >/dev/null
python -m pip install ruff bandit pip-audit >/dev/null

echo ""
echo "=== Backend: syntax compile ==="
python -m compileall app

echo ""
echo "=== Backend: ruff lint baseline ==="
ruff check app tests || true

echo ""
echo "=== Backend: bandit security baseline ==="
bandit -r app -ll || true

echo ""
echo "=== Backend: pip-audit dependency baseline ==="
pip-audit || true

echo ""
echo "=== Frontend: build and npm audit ==="
cd "$ROOT_DIR/frontend"

if [ -f package.json ]; then
  npm install
  npm run build
  npm audit --audit-level=high || true
else
  echo "No frontend package.json found."
fi

echo ""
echo "=== Git status ==="
cd "$ROOT_DIR"
git status --short

echo ""
echo "=== Security baseline scan complete ==="
