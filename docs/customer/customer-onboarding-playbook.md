# LumenAI Customer Onboarding Playbook
Version 1.0 | Customer Success — CONFIDENTIAL

## Overview
This playbook guides the Customer Success Manager (CSM) and customer technical
team through a structured 4-week onboarding process from contract signature to
go-live. The goal: every customer is live, trained, and generating value within
30 days of contract signature.

---

## Week 0 — Pre-Kickoff (Days -7 to 0)

**Trigger**: Contract signed, HIPAA BAA executed.

### CSM Actions
- [ ] Send welcome email with kickoff agenda and pre-work list
- [ ] Schedule kickoff call (60 minutes) with all stakeholders
- [ ] Create customer Slack/Teams channel (if applicable)
- [ ] Open CRM record; record contract tier, facility count, and go-live target date
- [ ] Assign customer to CSM queue and set 30/60/90-day milestone reminders

### Customer Pre-Work
- [ ] Identify technical contacts: IT lead, SPD Director, Infection Prevention lead
- [ ] Confirm network/firewall team availability for Week 1
- [ ] Gather instrument catalog (CSV or CMMS export) for baseline import
- [ ] Identify SSO provider (Azure AD / Okta / Epic / none)
- [ ] Confirm HIPAA BAA is countersigned and on file

### LumenAI Engineering Actions
- [ ] Provision tenant: create tenant_id, assign facility_id(s), set data_tier to contract tier
- [ ] Configure subdomain: `{customer}.app.lumenai.com`
- [ ] Set audit log retention to tier-appropriate value (1/3/7/10 years)
- [ ] Enable feature flags matching purchased tier
- [ ] Confirm `/health` and `/ready` endpoints responding for new tenant

---

## Week 1 — Technical Setup (Days 1–7)

### SSO/OIDC Configuration

**Azure Active Directory**
```
1. Register app in Azure AD portal: "LumenAI SPD Platform"
2. Set Redirect URI: https://{customer}.app.lumenai.com/auth/callback
3. Configure groups claim for role mapping
4. Provide to LumenAI:
   - Tenant ID (Directory ID)
   - Client ID
   - Client Secret (store in Vault)
5. LumenAI sets:
   JWKS_URL = https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys
   OIDC_ISSUER_URL = https://login.microsoftonline.com/{tenant}/v2.0
   OIDC_AUDIENCE = {client_id}
```

**Okta**
```
1. Create OIDC app in Okta admin console
2. Discovery URL: https://{okta-domain}/.well-known/openid-configuration
3. Client ID: lumenai-{tenant_id}
4. Redirect URI: https://{customer}.app.lumenai.com/auth/callback
5. Scopes: openid profile email groups
6. Claim mapping: sub → user_id, email → actor, groups → role
```

**Epic (SMART on FHIR — Staff Login Only)**
```
1. Register via Epic on FHIR / SMART on FHIR developer portal
2. Scope: launch/patient openid profile
3. Note: Epic SSO is for staff login only; LumenAI does NOT access patient data
4. Redirect URI: https://{customer}.app.lumenai.com/auth/epic/callback
```

**No SSO (Starter Tier)**
```
- LumenAI provisions email/password accounts for each user
- Temporary passwords issued via secure email
- Users prompted to change on first login
```

### Checklist — Week 1
- [ ] SSO configured and tested with at least one admin account
- [ ] All planned users provisioned with correct roles:
  - `technician` — SPD floor staff
  - `educator` — Senior SPD technicians / trainers
  - `manager` — SPD Director / Supervisor
  - `infection_prevention` — IP specialist
  - `admin` — IT/tenant admin
- [ ] Network connectivity validated: API reachability from facility network
- [ ] Firewall rules confirmed (if IP allowlisting required)
- [ ] Customer can reach `/health` endpoint from internal network

---

## Week 2 — Data Migration (Days 8–14)

### Instrument Catalog Import
```
1. Download CSV template from: https://docs.lumenai.com/import/instruments-template.csv
2. Populate fields: instrument_id, name, manufacturer, model, serial_number,
   ifu_reference, inspection_category, sterilization_method
3. Upload via: POST /api/baselines/import (Enterprise+) or send to CSM
4. Validate: confirm row count matches catalog size
5. Review any import errors with CSM
```

### Manufacturer Baseline Import
- LumenAI ships with baselines for 200+ common instrument types
- Customer-specific baselines: submit manufacturer IFU PDFs to CSM
- CSM coordinates with LumenAI engineering for custom baseline creation (5-day SLA)

### Vendor Baseline Import (Professional+)
- Export vendor catalog from CMMS or Materials Management system
- Map vendor_id, vendor_name, contract_id fields
- Upload via vendor baseline API or CSM-assisted import

### Historical Inspection Data (Optional)
- Last 6 months recommended for trend analysis and benchmarking
- Format: CSV with inspection_date, instrument_id, technician_id, findings, disposition
- CSM provides import template and validates data format before upload

### Barcode/UDI/QR Catalog Setup
- Provide list of barcode formats in use (Code128, QR, UDI-DI)
- LumenAI configures barcode parsing rules for your catalog
- Test with 10 sample instruments before full catalog go-live

### Checklist — Week 2
- [ ] Instrument catalog imported and validated (row count confirmed)
- [ ] Baseline coverage >= 80% of catalog (target for pilot success)
- [ ] Manufacturer baselines available for top 50 instruments by volume
- [ ] Barcode/UDI parsing tested and confirmed
- [ ] Historical data imported (if applicable)

---

## Week 3 — Training (Days 15–21)

### SPD Technician Training (2 hours)
**Format**: Hands-on with demo instruments (or live instruments in test mode)
**Topics**:
1. Login and navigation (15 min)
2. Starting an inspection session (15 min)
3. Submitting instrument images (20 min)
4. Reviewing AI findings and confidence scores (20 min)
5. Accepting vs. overriding AI findings (15 min)
6. Escalation workflow — critical finding → supervisor notification (15 min)
7. Q&A (20 min)

**Deliverable**: Each technician completes 5 practice inspections before go-live.

### SPD Educator/Manager Training (1 hour)
**Topics**:
1. Dashboard overview — inspection volume, finding trends (20 min)
2. Priority queue and ranking engine (15 min)
3. Override rate monitoring (10 min)
4. PDF report generation (10 min)
5. Q&A (5 min)

### Infection Prevention Training (30 minutes)
**Topics**:
1. Contamination trend dashboard (10 min)
2. Critical finding escalation alerts (10 min)
3. JC/AAMI readiness score overview (10 min)

### Admin Training (30 minutes)
**Topics**:
1. User management — add/remove/role changes (10 min)
2. Audit log access (5 min)
3. Tier and entitlement overview (5 min)
4. Support ticket submission (10 min)

### Train-the-Trainer Materials
- CSM delivers training slides and video recordings
- Customer designates internal trainer for future staff onboarding
- LumenAI provides trainer certification (optional; available for Enterprise+)

### Checklist — Week 3
- [ ] All SPD technicians trained and practice-inspection complete
- [ ] SPD Manager/Educator trained on dashboard
- [ ] IP specialist trained on contamination view
- [ ] Admin trained on user management
- [ ] Train-the-trainer materials delivered
- [ ] Training completion logged in CRM

---

## Week 4 — Go-Live (Days 22–30)

### Go-Live Checklist
- [ ] SSO login working for all users
- [ ] First inspection session completed successfully
- [ ] AI findings displaying with correct confidence scores
- [ ] PDF export generating correctly for all report types
- [ ] Audit log entries appearing for all inspection events
- [ ] `/health` and `/ready` endpoints confirmed responding
- [ ] Escalation path tested: critical finding → supervisor notification received
- [ ] Override workflow tested and override recorded in audit log
- [ ] HIPAA BAA confirmed on file
- [ ] Support contact and ticket submission confirmed by customer
- [ ] Executive dashboard access verified (if Enterprise+)
- [ ] 30-day check-in call scheduled

### Shadowed First Inspection
- CSM joins live for first inspection session (video call or on-site)
- Reviews first 10 AI findings with SPD technician in real time
- Confirms finding categories, confidence scores, and escalation thresholds look correct

### Baseline Data Validation
- First 50 inspections reviewed jointly: CSM + SPD Educator
- Compare AI findings against manual technician assessment
- Document agreement rate (target: >= 85%)
- Flag any systematic disagreements for engineering review

### Escalation Path Confirmation
- Verify escalation notification reaches correct supervisor
- Confirm escalation SLA: critical finding acknowledged within 15 minutes
- Test after-hours escalation path (if configured)

---

## Tier-Specific Onboarding Notes

### Starter
- No SSO required; email/password provisioned
- Baseline import limited to 500 instruments
- Go-live expected in 2 weeks (abbreviated process)

### Professional
- SSO strongly recommended
- Named CSM assigned; weekly check-ins through Day 90
- Vendor baseline import included

### Enterprise
- SSO required
- API integration scoping call in Week 1
- CMMS integration project plan created in Week 2
- Executive dashboard configured by Week 3
- Dedicated CSM; 4-hour support SLA active at go-live

### Health System
- Multi-facility rollout: stagger by facility; 1 facility/week recommended
- SSO mandatory (Azure AD / Okta)
- Executive sponsor call at kickoff and monthly thereafter
- Professional services team leads implementation
