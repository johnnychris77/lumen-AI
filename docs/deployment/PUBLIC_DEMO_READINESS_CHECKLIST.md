# Public Demo Readiness Checklist

## Local Readiness

- API health returns OK
- Production readiness endpoint works
- Enterprise quality gate passes
- Demo seed script runs
- Dashboard shows non-zero data
- Governance packet exports generate DOCX/PPTX/PDF
- RBAC viewer write is denied
- RBAC operator write is allowed

## Static Demo

- Landing page opens locally
- README is polished
- Pitch deck exists
- Screenshot gallery exists
- Live demo links exist

## Cloud Readiness

- Secrets removed from repo
- Slack webhook rotated if exposed
- SMTP credentials removed
- Managed Postgres configured
- Managed Redis configured
- PUBLIC_BASE_URL updated
- ALLOWED_ORIGINS restricted
- Dev auth disabled or replaced
