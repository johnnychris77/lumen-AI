# LumenAI Enterprise Data Model v1

## Purpose

This document defines the enterprise data backbone for LumenAI as it moves from public MVP to enterprise-ready healthcare quality intelligence platform.

## Core Workflow

Tenant
-> Facility
-> Department
-> User / Role
-> Inspection
-> Evidence
-> Finding
-> Risk Score
-> Disposition
-> Alert
-> QA Review
-> IP Review
-> CAPA
-> Audit Log
-> Governance Packet

## Enterprise Entities Added in SQLAlchemy v1

The first enterprise model layer introduces:

- EnterpriseFacility
- EnterpriseDepartment
- EnterpriseVendor
- EnterpriseInstrument
- EnterpriseEvidence
- EnterpriseFinding
- EnterpriseRiskScore
- EnterpriseDisposition
- EnterpriseCapa
- EnterpriseGovernancePacket

## Design Principles

1. Every enterprise record should be tenant-aware.
2. Evidence should link to inspection context.
3. Findings should connect instruments, vendors, and risk.
4. Risk scores should separate patient safety, regulatory, operational, and vendor risk.
5. Dispositions should preserve recommended and final action.
6. CAPA should connect findings, owners, vendors, and closure status.
7. Governance packets should support executive review, vendor escalation, infection prevention review, and survey readiness.
8. AI outputs should remain human-reviewable and auditable.
9. The live dashboard should remain stable while enterprise models are introduced.
10. Enterprise workflow endpoints should be added only after model import tests pass.

## MVP Enterprise Workflow

Create inspection
-> Upload evidence
-> Classify finding
-> Assign severity
-> Recommend disposition
-> Trigger alert
-> Create QA/IP review
-> Update vendor intelligence
-> Create audit log
-> Generate governance packet

## Version

Enterprise Data Model v1
