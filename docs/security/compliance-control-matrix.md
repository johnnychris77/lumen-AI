# LumenAI Compliance Control Matrix

## Purpose

This document maps LumenAI enterprise security, audit, evidence governance, and operational controls to common healthcare and SaaS trust expectations.

This is a readiness matrix, not a certification report. It is intended to support investor review, enterprise customer due diligence, SOC 2 readiness, HIPAA-aligned security planning, and internal engineering prioritization.

## Control Status Definitions

| Status | Meaning |
|---|---|
| Implemented | Control exists in code and has regression coverage |
| Partially Implemented | Control exists but needs broader coverage, production hardening, or documentation |
| Planned | Control is identified but not yet implemented |
| Evidence Available | Test, code, workflow, or document exists to support review |

## Executive Summary

LumenAI has implemented foundational controls for:

- Role-based access control for governance packet and vendor baseline workflows
- Tenant isolation helper and regression testing
- Tamper-evident packet hash verification
- Governance export history tracking
- Centralized audit event service
- Audit event integrity hashing
- Audit chain verification
- Evidence retention policy evaluation
- Legal hold deletion blocking
- Dependency vulnerability scanning
- Blocking lint and compliance test gates in CI

Remaining production-readiness work includes replacing demo-token authentication with OIDC/JWT, expanding tenant isolation across all routes, adding database migrations for audit hash columns, and completing incident response and operational runbooks.

---

# 1. Access Control

| Control | Description | Status | Evidence |
|---|---|---|---|
| Enterprise role enforcement | Governance packet export, hash verification, export history, vendor baseline approval, audit, and library routes require hospital or enterprise admin role | Implemented | `test_governance_packet_access_control.py`, `test_vendor_baseline_access_control.py`, `test_vendor_baseline_audit_access_control.py`, `test_vendor_baseline_library_access_control.py` |
| Vendor self-approval prevention | Vendors can submit baseline evidence but cannot approve their own submitted baselines | Implemented | `test_vendor_baseline_access_control.py` |
| Tenant membership helper | Tenant access requires enabled tenant membership | Implemented | `test_tenant_isolation.py` |
| Tenant role dependency | Tenant route dependency checks allowed roles | Implemented | `test_tenant_isolation.py` |
| Centralized enterprise auth helper | Common helper for role-based enterprise authorization | Partially Implemented | `app/enterprise_auth.py`, `test_enterprise_auth.py` |
| Production identity provider | Replace demo token/header auth with OIDC/JWT provider | Planned | Roadmap item |

---

# 2. Tenant Isolation

| Control | Description | Status | Evidence |
|---|---|---|---|
| Missing user denied | Tenant authorization denies missing user identity | Implemented | `test_tenant_isolation.py` |
| Missing membership denied | User without tenant membership is denied | Implemented | `test_tenant_isolation.py` |
| Disabled membership denied | Disabled tenant membership cannot access tenant resources | Implemented | `test_tenant_isolation.py` |
| Cross-tenant access denied | User with access to Tenant A is denied access to Tenant B | Implemented | `test_tenant_isolation.py` |
| API-level tenant boundary testing | Protected API routes validate tenant boundaries through TestClient | Partially Implemented | `test_tenant_api_boundaries.py` |
| Full route-by-route tenant enforcement | All tenant-scoped routes require tenant filtering | Planned | Future route coverage expansion |

---

# 3. Audit Logging and Immutability

| Control | Description | Status | Evidence |
|---|---|---|---|
| Persistent workflow audit events | Vendor baseline workflow records submission, approval, and scoring-use audit events | Implemented | `test_vendor_baseline_persistent_workflow.py` |
| Audit immutability regression | Existing audit events remain stable after repeated workflow actions | Implemented | `test_audit_immutability.py` |
| Centralized audit service | Common append-only audit writer exists for enterprise audit events | Implemented | `app/services/enterprise_audit_service.py`, `test_enterprise_audit_service.py` |
| Audit event integrity hash | Centralized audit events include SHA-256 integrity hashes | Implemented | `test_enterprise_audit_integrity_hash.py` |
| Previous-event hash linking | Audit events can link to previous event hash for same resource chain | Implemented | `test_enterprise_audit_integrity_hash.py` |
| Audit chain verification service | Audit chains can be verified and tamper detection can identify broken event | Implemented | `app/services/audit_chain_verification_service.py`, `test_audit_chain_verification.py` |
| Dedicated audit hash columns | Promote event hash fields from serialized details to DB columns | Planned | Future migration |

---

# 4. Evidence Integrity and Tamper Evidence

| Control | Description | Status | Evidence |
|---|---|---|---|
| Governance PDF packet export | Governance packet can be exported as PDF | Implemented | `test_governance_packet_hash_workflow.py` |
| Packet hash generation | Exported packet creates SHA-256 hash record | Implemented | `test_packet_hash_tamper_evidence.py` |
| Packet hash verification | Stored packet hash can be verified through API | Implemented | `test_packet_hash_tamper_evidence.py` |
| Tampered hash rejected | Unknown or altered hash returns not verified | Implemented | `test_packet_hash_tamper_evidence.py` |
| Export history immutability | Later exports append records while prior latest export remains stable | Implemented | `test_governance_export_history_immutability.py` |
| Centralized packet export audit | Governance packet export writes centralized audit event | Implemented | `test_governance_packet_centralized_audit.py` |
| Evidence certificate | Human-readable export certificate for customer proof | Planned | Future evidence certificate milestone |

---

# 5. Vendor Accountability

| Control | Description | Status | Evidence |
|---|---|---|---|
| Vendor baseline submission | Vendor can submit baseline instrument evidence | Implemented | `test_vendor_baseline_persistent_workflow.py`, `test_vendor_baseline_access_control.py` |
| Hospital approval workflow | Hospital admin approves vendor baseline before scoring use | Implemented | `test_vendor_baseline_persistent_workflow.py` |
| Vendor self-approval blocked | Vendor role cannot approve baseline | Implemented | `test_vendor_baseline_access_control.py` |
| Protected vendor baseline audit trail | Vendor cannot view protected hospital approval audit trail | Implemented | `test_vendor_baseline_audit_access_control.py` |
| Protected vendor baseline library | Vendor cannot view full protected baseline library | Implemented | `test_vendor_baseline_library_access_control.py` |
| Vendor-facing limited audit view | Separate filtered vendor-safe audit endpoint | Planned | Future product decision |

---

# 6. Retention and Legal Hold

| Control | Description | Status | Evidence |
|---|---|---|---|
| Retention expiration calculation | Evidence expiration date calculated from created date and retention days | Implemented | `test_evidence_retention_service.py` |
| Deletion allowed after expiration | Expired evidence without legal hold can be eligible for deletion | Implemented | `test_evidence_retention_service.py` |
| Legal hold blocks deletion | Expired evidence with legal hold cannot be deleted | Implemented | `test_evidence_retention_service.py` |
| Retention decision audit | Retention decision records centralized audit event | Implemented | `test_evidence_retention_service.py` |
| Production deletion workflow | Actual deletion queue and approval workflow | Planned | Future retention execution milestone |

---

# 7. Secure Engineering and CI/CD

| Control | Description | Status | Evidence |
|---|---|---|---|
| Ruff lint blocking | Backend Ruff linting is blocking in CI | Implemented | `.github/workflows/security-baseline.yml`, `.github/workflows/ci.yml` |
| Backend compliance tests blocking | Critical backend compliance tests are blocking in CI | Implemented | `.github/workflows/backend-compliance-tests.yml` |
| Core CI blocking | Legacy CI no longer bypasses pytest/flake8 failures | Implemented | `.github/workflows/ci.yml` |
| Python dependency audit | `pip-audit` remediated and made blocking | Implemented | `backend/requirements.txt`, security workflow |
| Frontend dependency audit | `npm audit --audit-level=high` remediated and made blocking | Implemented | `frontend/package.json`, `frontend/package-lock.json`, security workflow |
| Node runtime standardized | Frontend standardized on Node 20.19+ | Implemented | `.nvmrc`, `frontend/package.json` |
| Bandit medium/high scan | Static security scan triaged and hardened | Partially Implemented | `docs/security/bandit-triage.md` |

---

# 8. HIPAA-Aligned Security Considerations

| HIPAA-Aligned Area | LumenAI Control | Status |
|---|---|---|
| Access control | Enterprise role guards, tenant membership checks, route access-control tests | Partially Implemented |
| Audit controls | Persistent audit logs, centralized audit service, audit hash chain | Implemented |
| Integrity | Packet hash verification, audit event hashing, export history immutability | Implemented |
| Person/entity authentication | Demo token currently used; OIDC/JWT planned | Planned |
| Transmission security | Requires production TLS and secure deployment controls | Planned |
| Retention | Retention policy evaluation and legal hold blocking | Partially Implemented |
| Business associate readiness | Requires policies, BAAs, deployment controls, incident response | Planned |

---

# 9. SOC 2 Readiness Mapping

| SOC 2 Trust Service Category | Relevant LumenAI Controls | Status |
|---|---|---|
| Security | RBAC, tenant isolation, protected governance exports, dependency scans, CI gates | Partially Implemented |
| Availability | CI validation and workflow testing exist; production SLO/monitoring needed | Planned |
| Processing Integrity | Audit trails, hash verification, export history, CAPA and baseline workflows | Partially Implemented |
| Confidentiality | Access-control tests protect sensitive governance evidence | Partially Implemented |
| Privacy | Requires data inventory, retention rules, privacy workflows | Planned |

---

# 10. Open Enterprise Readiness Gaps

| Gap | Risk | Recommended Next Action |
|---|---|---|
| Demo-token authentication | Not production-grade authentication | Replace with OIDC/JWT |
| Header-based role trust | Roles can be spoofed in non-production mode | Validate roles from signed claims |
| SQLite local persistence | Not production-grade for enterprise multi-tenant workloads | Use managed PostgreSQL with migrations |
| Audit hash stored in details | Harder to query and enforce | Add DB columns for `event_hash` and `previous_event_hash` |
| Partial tenant route coverage | Some routes may lack tenant guards | Expand API-level tenant boundary tests |
| Limited operational runbooks | Customer due diligence expects documented operations | Add incident response, backup, recovery, key management docs |
| No formal threat model | Security architecture needs abuse-case review | Add threat model document |

---

# 11. Priority Roadmap

1. Replace demo-token auth with centralized OIDC/JWT-compatible auth layer.
2. Add database migrations for tenant membership and audit hash columns.
3. Expand tenant boundary tests across all tenant-scoped APIs.
4. Add evidence packet certificate.
5. Add incident response and operational security runbooks.
6. Add backup/recovery and data retention execution workflows.
7. Prepare SOC 2 readiness evidence folder.

