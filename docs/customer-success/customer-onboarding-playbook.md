# Customer Onboarding Playbook

**Version:** Phase 11  
**Date:** 2026-06-23  
**Audience:** LumenAI Customer Success, Implementation Team, Hospital IT  
**Applies To:** Hospital Tier and Enterprise Tier deployments

---

## Overview

This playbook covers the standard LumenAI onboarding process from contract signature to go-live. A typical pilot deployment completes in 4–6 weeks. Full production onboarding for a single facility takes 6–8 weeks.

---

## Phase 1 — Pre-Onboarding (Week 0)

### Deliverables
- [ ] Signed contract and BAA executed
- [ ] Tenant provisioned in LumenAI production environment
- [ ] Admin credentials delivered via secure channel
- [ ] Kickoff call scheduled

### CS Team Actions
1. Create tenant record with facility name, tenant ID, and SMTP settings
2. Provision admin user account (SHA-256 hashed token, never readable again)
3. Send secure onboarding welcome email with login URL and Quick Start guide
4. Schedule kickoff call with SPD Director and IT lead

### Customer IT Actions
1. Whitelist `lumenai.com` and API endpoint in network firewall
2. Configure Zebra USB HID scanner driver (if using barcode scanning)
3. Identify SPD Manager and Technician user list for account creation

---

## Phase 2 — Facility Setup (Week 1)

### Deliverables
- [ ] Facility name and departments configured
- [ ] Admin and SPD Manager accounts created
- [ ] RBAC roles assigned

### Steps
1. **Facility Setup:** Log in as admin → Settings → configure facility name, site codes, departments
2. **User Creation:** Settings → Users → create SPD Manager accounts → assign `spd_manager` role
3. **Technician Accounts:** Create accounts for each technician → assign `spd_technician` role
4. **Role Verification:** Settings → Roles → confirm role assignments match job titles

### Validation
- All SPD Managers can log in and access Review Queue
- All Technicians can log in and access New Inspection form
- Admins can access Users, Roles, and Settings pages

---

## Phase 3 — Vendor & Manufacturer Onboarding (Weeks 2–3)

### Deliverables
- [ ] Primary reprocessing vendor registered
- [ ] At least 5 baseline image submissions received
- [ ] At least 1 baseline approved

### Steps
1. **Vendor Registration:** Infrastructure → add vendor with contact information
2. **Vendor Portal Access:** Share vendor portal URL (`/vendor-baseline-portal`) with vendor contact
3. **Baseline Submission Training:** Walk vendor through image capture guidelines
4. **Manufacturer Baselines:** Contact instrument manufacturers for approved baseline images
5. **Baseline Review:** SPD Manager reviews and approves/rejects submissions via Baseline Reviews

### Image Capture Requirements
- Format: JPEG or PNG
- Minimum resolution: 1080p (4K preferred for borescope)
- Maximum file size: 20 MB per image
- Required angles: full instrument, lumen entry, distal tip (3 minimum for borescopes)
- PHI: no patient labels, stickers, or identifiers in frame
- Lighting: white LED, no flash flare, no shadows obscuring lumen

### Validation
- Vendor can submit via portal without admin assistance
- At least one baseline in `approved` status per active instrument type

---

## Phase 4 — Instrument Registry (Week 3)

### Deliverables
- [ ] Pilot fleet registered (all lumened scopes)
- [ ] Barcodes / UDIs captured for all instruments
- [ ] Instrument Passports accessible

### Steps
1. **Fleet Entry:** Infrastructure → Instrument Registry → add each instrument with internal ID, type, manufacturer, model
2. **Barcode Capture:** Enter barcode or UDI from instrument label or manufacturer documentation
3. **Passport Verification:** Navigate to `/instrument-passport?instrument=[ID]` to confirm passport loads

### Priority Instrument Types
1. Flexible Ureteroscope
2. Bronchoscope
3. Colonoscope
4. Cystoscope
5. Hysteroscope
6. Laparoscope

---

## Phase 5 — Training (Week 4)

### Deliverables
- [ ] All technicians complete Quick Start guide
- [ ] All SPD Managers complete Review Queue and CAPA workflows
- [ ] First live inspection submitted and reviewed

### Training Sequence
1. **Technicians:** Training Center → SPD Technician Track (5 modules, ~20 minutes total)
2. **SPD Managers:** Training Center → SPD Manager Track (6 modules, ~25 minutes total)
3. **Supervised Practice:** Manager observes first 5 technician submissions
4. **Live Inspection:** First real instrument inspected, submitted, reviewed, and closed

### Success Criteria
- Technician can complete an inspection end-to-end in under 60 seconds
- Manager can review, approve/reject findings, and create a CAPA without assistance
- At least one inspection with a finding has been reviewed and closed

---

## Phase 6 — Go-Live (Week 5–6)

### Deliverables
- [ ] Deployment Readiness Dashboard shows ≥ 80% readiness score
- [ ] All checks passing (API, Auth, Instruments, Baselines, Inspections)
- [ ] SPD Director has accessed Executive Command Center
- [ ] CS kickoff review call completed

### Go-Live Checklist
- [ ] Deployment Readiness: `/deployment-readiness` score ≥ 80%
- [ ] Baselines: at least 10 approved baselines across fleet
- [ ] Inspections: at least 20 live inspections submitted
- [ ] Users: all active staff have logged in at least once
- [ ] Executive: SPD Director has seen Command Center and Surgical Readiness dashboards

### Post Go-Live (Week 6+)
- Weekly CS check-in for first 30 days
- Customer Success Dashboard review at Day 30
- ROI report generated at Day 60
- Renewal conversation initiated at Day 75

---

## Escalation Matrix

| Issue | Owner | SLA |
|-------|-------|-----|
| User cannot log in | CS Team | 2h |
| Baseline submission rejected without explanation | CS Team | 4h |
| Risk score appears incorrect | CS → Engineering | 24h |
| Data not persisting | Engineering | 4h |
| Security concern / data exposure | Security → Engineering | 1h |

---

## Success Metrics at 90 Days

| Metric | Target |
|--------|--------|
| Inspections completed | ≥ 100 |
| Baseline coverage | ≥ 75% |
| Adoption rate | ≥ 70% |
| Review turnaround | ≤ 8 hours |
| Customer Health Score | Green |

---

*LumenAI Customer Success — Internal Use Only*  
*All AI outputs require qualified human review before clinical action.*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*
