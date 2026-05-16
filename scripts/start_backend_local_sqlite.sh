#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

source .venv/bin/activate

export DATABASE_URL="sqlite:///./lumenai.db"
export PUBLIC_BASE_URL="http://127.0.0.1:18011"
export ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:9092,http://127.0.0.1:9092,http://localhost:18011,http://127.0.0.1:18011,https://lumen-ai-53u4.onrender.com"

python -m uvicorn app.main:app --host 0.0.0.0 --port 18011
