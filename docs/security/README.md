# LumenAI Security and Compliance Documentation

This folder contains enterprise security, compliance readiness, and trust-layer documentation.

## Documents

| Document | Purpose |
|---|---|
| `security-risk-register.md` | Tracks known security risks, remediation status, and accepted risk |
| `bandit-triage.md` | Tracks Bandit static-analysis findings and decisions |
| `compliance-control-matrix.md` | Maps LumenAI controls to SOC 2 / HIPAA-aligned readiness categories |

## Current Implemented Trust Controls

- Blocking backend lint checks
- Blocking backend compliance tests
- Blocking dependency vulnerability scans
- Tenant isolation regression tests
- Enterprise role access-control tests
- Vendor baseline approval/audit/library access-control tests
- Governance packet access-control tests
- Tamper-evident packet hash verification
- Governance export history immutability tests
- Centralized enterprise audit service
- Audit event integrity hash chain
- Audit chain verification service
- Evidence retention and legal hold policy service

## Important Note

These documents support readiness and due diligence. They do not represent formal SOC 2, HIPAA, ISO 27001, or third-party certification.
