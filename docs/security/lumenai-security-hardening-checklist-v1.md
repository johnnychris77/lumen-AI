# LumenAI Security Hardening Checklist v1

## Status

Ready for engineering execution.

## Immediate Priorities

- [ ] Remove dev-token dependency from public dashboard
- [ ] Add `/api/public/module-status/vendor`
- [ ] Add `/api/public/module-status/capa`
- [ ] Add `/api/public/module-status/audit`
- [ ] Add `/api/public/module-status/evidence`
- [ ] Lock production CORS to `https://lumen-ai-1.onrender.com`
- [ ] Confirm `render.yaml` has one top-level `services:` block
- [ ] Confirm `render.yaml` has one top-level `databases:` block
- [ ] Expand route validation to content validation

## Authentication and Authorization

- [ ] Define production roles
- [ ] Remove trust in frontend role headers
- [ ] Require JWT claims for enterprise access
- [ ] Add RBAC matrix
- [ ] Add authorization tests for protected endpoints

## Tenant Isolation

- [ ] Add tenant isolation tests
- [ ] Prevent cross-tenant access by object ID
- [ ] Validate tenant context server-side
- [ ] Add audit logs for denied cross-tenant attempts

## Evidence Bundle Security

- [ ] Require authorization for evidence downloads
- [ ] Tenant-scope all evidence bundles
- [ ] Verify manifest hash behavior
- [ ] Verify audit chain behavior
- [ ] Add evidence export audit logs

## Public Demo Safety

- [ ] Public dashboard uses only public-safe status endpoints
- [ ] Public pages expose no secrets
- [ ] Public pages expose no PHI
- [ ] Public pages expose no tenant records
- [ ] Protected modules show safe protected status

## Deployment and Reliability

- [ ] Validate public landing route
- [ ] Validate dashboard route
- [ ] Validate portfolio index
- [ ] Validate all portfolio pages
- [ ] Keep static dashboard fallback until Render rewrites are reliable

## Final Hardening Goal

LumenAI should be safe for public review, credible for investor review, reliable for customer demos, and structured for enterprise-production readiness.
