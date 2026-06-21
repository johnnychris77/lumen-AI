# LumenAI Database Runbook

## Overview

LumenAI uses PostgreSQL in production (managed: RDS, Cloud SQL, or Azure Database) and SQLite for local development and CI. Database schema is managed via Alembic migrations.

---

## Migration Workflow

### Prerequisites
```bash
cd backend
export DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/lumenai
pip install alembic psycopg2-binary
```

### Run all pending migrations (standard deploy step)
```bash
alembic upgrade head
```

### Check current migration state
```bash
alembic current
```

### View migration history
```bash
alembic history --verbose
```

### Rollback one revision
```bash
alembic downgrade -1
```

### Rollback to a specific revision
```bash
alembic downgrade <revision_id>
```

### Generate a new migration (after model changes)
```bash
alembic revision --autogenerate -m "add_column_foo_to_table_bar"
# Review the generated file in alembic/versions/ before applying!
alembic upgrade head
```

### Apply migration in CI/CD pipeline
```bash
DATABASE_URL=$DATABASE_URL alembic upgrade head
```

**Important**: Always run `alembic upgrade head` before starting the API in production deployments. The Kubernetes init container pattern is recommended:

```yaml
initContainers:
  - name: alembic-migrate
    image: lumenai/backend:latest
    command: ["alembic", "upgrade", "head"]
    envFrom:
      - secretRef:
          name: lumenai-secrets
```

---

## Backup Strategy

### Automated Backups (RDS / Cloud SQL)

| Type                    | Frequency       | Retention    |
|-------------------------|-----------------|--------------|
| RDS automated backups   | Daily           | 7 days       |
| RDS point-in-time       | Continuous      | 7 days       |
| pg_dump to S3           | Daily (cron)    | 90 days      |
| Weekly pg_dump snapshot | Weekly          | 7 years (HIPAA) |

### Manual pg_dump
```bash
# Full database dump (compressed)
pg_dump "$DATABASE_URL" -Fc -f lumenai_$(date +%Y%m%d_%H%M%S).dump

# Upload to S3
aws s3 cp lumenai_*.dump s3://lumenai-prod-db-backups/manual/
```

### Automated backup script (run via cron or Lambda)
```bash
#!/bin/bash
set -euo pipefail
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="/tmp/lumenai_${TIMESTAMP}.dump"
pg_dump "$DATABASE_URL" -Fc -f "$DUMP_FILE"
aws s3 cp "$DUMP_FILE" "s3://lumenai-prod-db-backups/daily/lumenai_${TIMESTAMP}.dump"
rm -f "$DUMP_FILE"
echo "Backup complete: lumenai_${TIMESTAMP}.dump"
```

---

## Restore Procedure

### From pg_dump file
```bash
# 1. Stop the application (prevent writes during restore)
kubectl scale deployment lumenai-backend --replicas=0 -n lumenai

# 2. Download backup
aws s3 cp s3://lumenai-prod-db-backups/daily/lumenai_<timestamp>.dump /tmp/restore.dump

# 3. Restore (this DROPS and recreates the database)
pg_restore -d "$DATABASE_URL" --clean --if-exists /tmp/restore.dump

# 4. Run migrations to ensure schema is current
DATABASE_URL=$DATABASE_URL alembic upgrade head

# 5. Restart application
kubectl scale deployment lumenai-backend --replicas=2 -n lumenai
```

### From RDS Point-in-Time Recovery
1. AWS Console → RDS → Select instance → Actions → Restore to point in time
2. Select target time
3. Launch new instance (do not overwrite production)
4. Verify data integrity on restored instance
5. Update `DATABASE_URL` secret to point to restored instance
6. Roll out application

---

## Connection Pooling Configuration

Configure SQLAlchemy engine for production (in `app/db/__init__.py` or `app/db/session.py`):

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./lumenai.db")

# For PostgreSQL production
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,           # Number of persistent connections
        max_overflow=20,        # Additional connections beyond pool_size
        pool_pre_ping=True,     # Verify connection health before use
        pool_recycle=3600,      # Recycle connections after 1 hour
        pool_timeout=30,        # Wait up to 30s for a connection
    )
else:
    # SQLite (local/test)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Recommended**: Use PgBouncer connection pooler in front of PostgreSQL when > 50 concurrent API workers.

---

## Health Check Query

The `/ready` endpoint executes this query to verify database connectivity:
```sql
SELECT 1
```

For deeper health check:
```sql
SELECT current_database(), now(), pg_is_in_recovery();
```
`pg_is_in_recovery()` returns `false` on primary (writable), `true` on replica.

---

## Database Maintenance

### Analyze (update query planner statistics)
```bash
psql "$DATABASE_URL" -c "ANALYZE VERBOSE;"
```

### Vacuum (reclaim dead tuple space)
```bash
psql "$DATABASE_URL" -c "VACUUM ANALYZE;"
```

### Check table sizes
```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check slow queries (requires pg_stat_statements extension)
```sql
SELECT query, calls, total_exec_time/calls AS avg_ms, rows
FROM pg_stat_statements
ORDER BY avg_ms DESC
LIMIT 20;
```
