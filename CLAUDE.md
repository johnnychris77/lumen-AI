# LumenAI — Claude Code Configuration

## Project Structure

- **Backend:** `backend/` — FastAPI + SQLAlchemy (Python)
- **Frontend:** `frontend/` — React + TypeScript + Vite
- **Tests:** `backend/tests/` — pytest suite (~2059 tests)
- **Branch:** `claude/tender-johnson-mww1wi`

---

## Testing

**Always run pytest from the `backend/` directory**, not the project root.

```bash
# Correct
cd /home/user/lumen-AI/backend && python -m pytest tests/ -q

# Wrong — causes 48+ spurious collection errors ("No module named 'app'")
python -m pytest backend/tests/ -q
```

Before running any tests, confirm the working directory is `backend/`. If it is not, `cd` there first. Do not treat collection errors from the wrong directory as real test failures — they are an environment issue, not a code defect.

Frontend build check:
```bash
npm --prefix /home/user/lumen-AI/frontend run build
```

Linting:
```bash
ruff check /home/user/lumen-AI/backend/app /home/user/lumen-AI/backend/tests
```

---

## Git / Commit Workflow

Commits require an **external signing server** (`/tmp/code-sign`). This server occasionally returns `503`.

- If `git commit` fails with `signing server returned status 503`, **do not change any code**. The failure is infrastructure, not a code problem.
- Retry with exponential backoff: wait 4s, then 8s, then 16s between attempts.
- If the signing server is still down after 4 retries, report the outage clearly and stop — do not attempt workarounds like disabling signing.

Push pattern:
```bash
git push -u origin claude/tender-johnson-mww1wi
```

After pushing, create a draft PR if one does not already exist.

---

## Security Constraints (Non-Negotiable)

- Do not reintroduce hardcoded `Bearer dev-token` or weaken auth/security backend.
- Tenant data isolation must be enforced — tenants can never see each other's raw data.
- Every intelligence-sharing action must create an audit event.
- Hospital identities in cross-hospital intelligence must be anonymized.
- Never claim causation — always "potential association", "possible contributing factor", "quality review recommended".
- All correlation outputs must include `human_review_required: true`.
- Do NOT claim FDA clearance or regulatory approval anywhere in any document.
- Secret API keys: issued once via `secrets.token_urlsafe(40)`, stored as SHA-256 hash only, never retrievable again.
- No PHI in demo data or image metadata.
