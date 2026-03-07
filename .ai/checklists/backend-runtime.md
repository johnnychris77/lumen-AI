# Backend Runtime Checklist

- [ ] API container boots
- [ ] worker container boots
- [ ] DATABASE_URL present
- [ ] REDIS_URL present
- [ ] engine URL consistent across API and worker
- [ ] no sqlite fallback in shared runtime
- [ ] no Base import from session.py
