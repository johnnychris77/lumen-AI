#!/usr/bin/env bash
# CI-faithful reproduction of the "Backend tests (PostgreSQL 16)" job of
# .github/workflows/pilot-zero-gate.yml: Alembic upgrade/downgrade -1/upgrade on the
# SAME fresh database, then the full suite on that database. Isolated worktree.
# usage: ci_pg_repro.sh <worktree> <dbname> <outdir>
set -u
WT=$1; DB=$2; OUT=$3
mkdir -p "$OUT"
export PGPASSWORD=p47203
psql -h localhost -U postgres -qc "DROP DATABASE IF EXISTS $DB" -c "CREATE DATABASE $DB"
export DATABASE_URL=postgresql://postgres:p47203@localhost:5432/$DB
cd "$WT/backend"
{
  echo "sha=$(git rev-parse HEAD)"; echo "db=$DB"; date -u +start=%FT%TZ
  psql -h localhost -U postgres -tAc "select version()"
  python --version; pip freeze 2>/dev/null | grep -iE '^(sqlalchemy|psycopg|pytest|fastapi|alembic)'
} > "$OUT/env.txt" 2>&1
( alembic upgrade head && alembic downgrade -1 && alembic upgrade head ) > "$OUT/alembic.log" 2>&1
echo "alembic_exit=$?" >> "$OUT/env.txt"
python -m pytest tests -q -p no:cacheprovider -rfEsxX --junitxml="$OUT/junit.xml" > "$OUT/pytest.log" 2>&1
echo "pytest_exit=$?" >> "$OUT/env.txt"
date -u +end=%FT%TZ >> "$OUT/env.txt"
