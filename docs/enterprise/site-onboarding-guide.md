# LumenAI Site Onboarding Guide

> **Audience:** Facility deployment coordinators, IT administrators, and SPD/quality leadership onboarding a new hospital or ASC to LumenAI.

---

## Overview

Each new LumenAI site goes through an 8-step onboarding workflow tracked in the system. This guide walks through each step, what is required, and how to verify completion.

---

## Prerequisites

Before starting the onboarding workflow for a new facility, confirm:

- [ ] Health System exists in LumenAI (`GET /api/enterprise/health-systems/{system_id}`)
- [ ] Market and Region created under the Health System
- [ ] Facility record created: `POST /api/enterprise/facilities`
- [ ] Signed deployment agreement on file
- [ ] IT environment survey completed (network, device inventory)
- [ ] Key contacts identified: SPD Manager, IT Lead, Quality Officer

---

## Step-by-Step Onboarding

### Step 1 — Initiate Workflow

**API:** `POST /api/enterprise/onboarding/start`

```json
{
  "workflow_type": "site",
  "target_id": "<facility_id>",
  "system_id": "<health_system_id>",
  "initiated_by": "deployment-coordinator@health-system.example"
}
```

The workflow is assigned a unique `workflow_id`. Record this for tracking all subsequent steps.

**Checklist:**
- [ ] Kickoff meeting scheduled with facility leadership
- [ ] Deployment timeline agreed upon
- [ ] Workflow ID recorded

---

### Step 2 — Documents Collected (`documents_collected`)

**Advance via:** `POST /api/enterprise/onboarding/{workflow_id}/advance`

**Required documents:**
- Master Service Agreement (signed)
- Business Associate Agreement (signed, if applicable)
- Facility network topology diagram
- Instrument inventory list (tray types, vendor list)
- Key personnel list with roles and email addresses

**Checklist:**
- [ ] All documents received and filed
- [ ] No outstanding legal blockers

---

### Step 3 — Tenant Provisioned (`tenant_provisioned`)

**Responsible:** LumenAI Platform Team

**Activities:**
- Create tenant record in LumenAI with the facility's `tenant_id`
- Provision database namespace
- Set `TenantMembership` records for initial admin users
- Confirm tenant isolation is active

**Checklist:**
- [ ] Tenant `tenant_id` confirmed and documented
- [ ] Admin user login credentials delivered securely
- [ ] Tenant data isolation verified

---

### Step 4 — Users Invited (`users_invited`)

**Activities:**
- Create accounts for all required personnel roles:
  - SPD Manager (role: `qa_manager`)
  - Quality Officer (role: `qa_manager`)
  - IT Administrator (role: `admin`)
  - Inspection Staff (role: `inspector`)
  - Executive Viewer (role: `viewer`)
- Send secure credential emails
- Confirm first-login completion for admin account

**Checklist:**
- [ ] All required roles populated
- [ ] All initial users have accepted invite and logged in
- [ ] No shared accounts (each user has individual credentials)

---

### Step 5 — Baseline Assigned (`baseline_assigned`)

**Activities:**
- Upload instrument baselines for all tray types in use at this facility
- Submit baselines for QA review: `POST /api/enterprise/baselines`
- Approve baselines via authorized reviewer: `POST /api/enterprise/baselines/{id}/approve`
- Publish baselines to this facility: `POST /api/enterprise/baselines/{id}/publish`

**Baseline coverage target:** ≥ 80% of active tray types before go-live

**Checklist:**
- [ ] All tray type baselines uploaded
- [ ] QA review completed for all baselines
- [ ] At least 80% of baselines approved and published
- [ ] Baseline coverage score confirmed in readiness dashboard

---

### Step 6 — Training Complete (`training_complete`)

**Required training modules:**

| Module | Audience | Duration |
|--------|----------|----------|
| LumenAI Inspection Basics | All inspection staff | 45 min |
| Quality Review Workflow | SPD Managers, Quality Officers | 60 min |
| Alert Response Protocol | SPD Managers, Quality Officers | 30 min |
| Executive Dashboard Overview | Facility leadership | 20 min |
| Admin & User Management | IT Administrators | 30 min |

**Checklist:**
- [ ] 100% of inspection staff completed Inspection Basics
- [ ] 100% of managers completed Quality Review Workflow
- [ ] Competency assessments passed (≥ 80% score)
- [ ] Training records documented

---

### Step 7 — Go Live (`go_live`)

**Pre-Go-Live Checklist:**
- [ ] Readiness score ≥ 80 confirmed: `GET /api/enterprise/dashboards/readiness`
- [ ] Test inspection submitted and reviewed successfully
- [ ] Alert notification pathway tested (alerts reach correct personnel)
- [ ] On-call support escalation path confirmed
- [ ] Hypercare support period scheduled (first 30 days)

**Activation:**
- Confirm facility `onboarding_status` updated to `go_live`
- Set `go_live_date` in facility record
- Notify all users that system is live

---

### Step 8 — Completed (`completed`)

**30-Day Post-Go-Live Review:**
- [ ] ≥ 50 inspections submitted
- [ ] No unresolved critical alerts
- [ ] CAPA resolution rate ≥ 75%
- [ ] User satisfaction survey submitted
- [ ] Readiness score sustained ≥ 70

**Handoff:**
- Transfer from Deployment Team to Customer Success
- Schedule 90-day check-in
- Confirm facility is eligible for quarterly executive review

---

## Monitoring During Onboarding

Use these endpoints to track progress:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/enterprise/onboarding/{workflow_id}` | Current step and status |
| `GET /api/enterprise/onboarding?system_id=<id>` | All workflows for a health system |
| `GET /api/enterprise/dashboards/readiness` | Facility readiness scores |

---

## Common Issues and Resolutions

| Issue | Resolution |
|-------|-----------|
| Workflow advance fails with 422 | Steps must be advanced in order; check current step |
| Baseline publish fails | Baseline must have `approval_status: "approved"` before publishing |
| Readiness score below 60 | Review dimension breakdown; training and adoption are highest-weight dimensions |
| User cannot log in | Verify `TenantMembership` record exists and `is_enabled: true` |
| Inspections not appearing | Confirm `tenant_id` on submission matches facility's assigned `tenant_id` |

---

## Support Contacts

- **Technical Issues:** Contact your LumenAI Customer Success Manager
- **Baseline Questions:** Quality Team lead at your health system
- **Training Issues:** LumenAI Training Team

---

*LumenAI does not claim FDA clearance. All inspection results and quality signals require human review. This guide is for operational use only.*
