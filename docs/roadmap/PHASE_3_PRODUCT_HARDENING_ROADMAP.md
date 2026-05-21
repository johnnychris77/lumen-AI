# LumenAI Phase 3 Product Hardening Roadmap

## Purpose

Phase 3 moves LumenAI from a working hosted enterprise demo into a pilot-ready healthcare operations platform.

The current product demonstrates the core evidence-to-action workflow:

- Enterprise intake
- Finding classification
- Risk scoring
- Human review
- Governance packet preview
- JSON and PDF packet export
- CAPA creation
- CAPA lifecycle status updates
- Audit trail
- Executive command center
- CAPA executive risk rollup

Phase 3 focuses on hardening the platform for hospital pilot readiness, investor diligence, and enterprise buyer evaluation.

---

## Current Product Status

LumenAI currently has a hosted frontend and backend with a working enterprise workflow. The system can convert a quality finding, such as retained debris inside a Frazier suction, into a structured workflow record with governance visibility.

Current completed capabilities:

1. Hosted React frontend
2. Hosted FastAPI backend
3. Enterprise inspection intake API
4. Enterprise workflow history
5. Governance packet preview
6. Governance packet JSON export
7. Governance packet PDF export
8. Human review workflow
9. CAPA workflow
10. CAPA status lifecycle
11. Enterprise audit trail
12. CAPA executive summary
13. Enterprise command center
14. Investor demo script and pitch

---

## Phase 3 Strategic Objective

The strategic objective of Phase 3 is to make LumenAI credible as a pilot-ready enterprise product for regulated healthcare operations.

Phase 3 should answer five questions:

1. Can the product securely handle real users?
2. Can the product store real enterprise data persistently?
3. Can the product accept real evidence such as images and documents?
4. Can the workflow support hospital governance, quality, IP, and vendor review?
5. Can the product produce executive-ready, audit-ready outputs?

---

## Phase 3 Workstreams

## 1. Production Database Hardening

### Current State

The hosted demo uses application-managed database bootstrapping and may rely on environment-specific database configuration.

### Target State

LumenAI should run on a persistent production-grade database.

### Required Capabilities

- PostgreSQL-backed production deployment
- Database migrations using Alembic
- Tenant-safe schema design
- Migration rollback strategy
- Demo seed separation from production data
- Backup and restore plan

### Milestone

**LumenAI PostgreSQL Production Migration v1**

### Success Criteria

- Hosted backend uses PostgreSQL
- Enterprise tables persist across deploys
- Migrations run safely
- Demo data is controlled and repeatable
- No data loss during redeploy

---

## 2. Authentication and RBAC Hardening

### Current State

The demo uses development headers such as:

- Authorization: Bearer dev-token
- X-LumenAI-Role
- X-LumenAI-Actor

### Target State

LumenAI should support secure enterprise authentication and role-based access control.

### Required Roles

- Admin
- Operator
- Quality Reviewer
- Infection Prevention Reviewer
- Auditor
- Executive Viewer
- Vendor Viewer

### Required Capabilities

- Real login flow
- JWT or session-based authentication
- Role-based API authorization
- Tenant-aware access control
- User identity in audit trail
- Vendor-limited visibility
- Executive read-only access

### Milestone

**LumenAI Enterprise Auth & RBAC Hardening v1**

### Success Criteria

- Demo headers are replaced or isolated from production mode
- Users authenticate securely
- API routes enforce role rules
- Audit trail captures real user identity
- Tenant context is protected

---

## 3. Evidence Upload and Attachment Workflow

### Current State

The workflow can create structured findings, but it does not yet attach real evidence files.

### Target State

Users should be able to upload and attach evidence to a finding.

### Evidence Types

- Borescope images
- Instrument photos
- Inspection images
- IFU documents
- Quality notes
- Vendor documents
- Audit-supporting PDFs

### Required Capabilities

- File upload endpoint
- Secure file storage
- Evidence metadata
- Link evidence to finding
- Link evidence to governance packet
- Evidence preview in frontend
- Audit event for evidence upload

### Milestone

**LumenAI Evidence Upload & Attachment Workflow v1**

### Success Criteria

- User uploads an image or document
- Evidence is linked to finding ID
- Evidence appears in governance packet preview
- Evidence appears in audit trail
- Evidence can be included in PDF packet

---

## 4. AI Evidence Classification

### Current State

The demo scenario uses structured input fields and predefined classification.

### Target State

LumenAI should assist with evidence classification using AI-supported analysis.

### Classification Targets

- Suspected bioburden
- Retained debris
- Instrument damage
- Corrosion
- Foreign object
- Wet tray concern
- Missing indicator
- Vendor-related defect
- Reprocessing concern

### Required Capabilities

- Evidence classification endpoint
- Confidence score
- Human override
- Reviewer approval
- AI decision audit logging
- Model performance tracking
- Feedback loop for retraining

### Milestone

**LumenAI AI Evidence Classification v1**

### Success Criteria

- Uploaded evidence receives suggested classification
- Human reviewer can accept or override
- Model output is not treated as final decision
- Audit trail captures AI recommendation and human decision
- Model performance dashboard reflects review outcomes

---

## 5. Executive Governance Packet PDF v2

### Current State

The product can generate a functional governance packet PDF.

### Target State

The PDF should look like an executive-ready governance document.

### Required Sections

- LumenAI header and case title
- Facility and department
- Vendor and instrument
- Evidence summary
- Risk score
- Human review decision
- CAPA status
- Audit trail excerpt
- Recommended action
- Survey-readiness statement
- Vendor accountability section
- Executive summary

### Milestone

**LumenAI Executive Governance Packet PDF v2**

### Success Criteria

- PDF includes evidence and workflow details
- PDF is suitable for executive review
- PDF is suitable for quality committee review
- PDF supports survey readiness
- PDF includes audit identifiers and timestamps

---

## 6. CAPA Workflow Hardening

### Current State

LumenAI can open CAPA, update CAPA status, and show executive CAPA metrics.

### Target State

CAPA should support full lifecycle governance.

### Required Capabilities

- CAPA owner assignment
- Due date tracking
- Overdue logic
- CAPA closure notes
- Effectiveness check
- CAPA history
- CAPA escalation rules
- CAPA export

### Milestone

**LumenAI Enterprise CAPA Lifecycle v2**

### Success Criteria

- CAPA owner is visible
- Due date and overdue state are calculated
- Closure requires a note
- Effectiveness check can be documented
- CAPA history is visible
- Audit trail captures every status change

---

## 7. Investor Demo Environment

### Current State

The demo can be seeded manually and presented live.

### Target State

The hosted demo should always have a polished investor scenario available.

### Required Capabilities

- Seed script
- Reset script
- Demo scenario data
- Screenshot-ready command center
- Stable demo user
- Stable demo tenant
- No broken empty states during presentation

### Milestone

**LumenAI Investor Demo Environment v1**

### Success Criteria

- Hosted app loads with meaningful scenario data
- Command center shows active workflow
- CAPA summary shows meaningful metrics
- Audit trail shows governance actions
- Investor can understand value in under 3 minutes

---

## 8. Pilot Proposal Package

### Target State

LumenAI should have a hospital pilot package that explains what the product does, what the pilot measures, and what outcomes matter.

### Required Documents

- Pilot overview
- Use case summary
- Implementation plan
- Data requirements
- Security assumptions
- Success metrics
- Executive one-pager
- Demo script
- Risk and compliance statement

### Milestone

**LumenAI Hospital Pilot Proposal Package v1**

### Success Criteria

- Pilot package is ready for a hospital executive
- Pilot metrics are clear
- Scope is narrow and realistic
- Value proposition is tied to patient safety, OR readiness, quality governance, vendor accountability, and survey readiness

---

## Recommended Phase 3 Build Order

1. Evidence Upload & Attachment Workflow
2. PostgreSQL Production Migration
3. Auth & RBAC Hardening
4. Executive Governance Packet PDF v2
5. AI Evidence Classification
6. CAPA Lifecycle v2
7. Investor Demo Environment
8. Hospital Pilot Proposal Package

---

## Phase 3 North Star

LumenAI should become the enterprise evidence-intelligence and governance layer that converts frontline healthcare quality findings into structured action, human review, CAPA, audit readiness, executive visibility, and vendor accountability.

