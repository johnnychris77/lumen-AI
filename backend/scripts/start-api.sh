#!/bin/sh
set -eu

echo "=== LumenAI RESET API startup ==="
echo "BUILD_MAIN_SHA=${BUILD_MAIN_SHA:-unknown}"
echo "PWD=$(pwd)"
echo "Python=$(python --version 2>&1)"

echo "Waiting for database..."
python - <<'PY'
import os, time
import psycopg2

dsn = os.environ["DATABASE_URL"].replace("+psycopg2", "")
for i in range(60):
    try:
        conn = psycopg2.connect(dsn)
        conn.close()
        print(f"Database ready on attempt {i+1}")
        break
    except Exception as e:
        print(f"DB not ready yet ({i+1}/60): {e}")
        time.sleep(2)
else:
    raise SystemExit("Database never became ready")
PY

echo "Fingerprinting app files..."
sha256sum /app/app/main.py || true
grep -n "portfolio_brief" /app/app/main.py || true

echo "OpenAPI route probe..."
python - <<'PY'
from app.main import app
paths = sorted(app.openapi()["paths"].keys())
print("portfolio routes:", [p for p in paths if "portfolio-briefings" in p])
PY

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
