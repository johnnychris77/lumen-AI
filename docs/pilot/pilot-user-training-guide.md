# LumenAI Pilot User Training Guide

**Version:** 1.0  
**Effective Date:** 2026-06-21  
**Audience:** SPD Technicians, Educators, Managers, Vendor Representatives, QI Reviewers, Executives

---

## Quick Start (All Users — 5 Minutes)

### Step 1: Log In

1. Open your browser (Chrome or Edge recommended) and navigate to your LumenAI URL
2. Go to `/login`
3. Enter your work email and the temporary password provided by your coordinator
4. Click **Sign in**
5. You will be taken to the Dashboard

> **First login:** You will not be prompted to change your password in the pilot — contact your coordinator if you need a reset.

### Step 2: Understand Your Dashboard

The Dashboard shows:
- **Recent Inspections** — inspections logged by your facility
- **Quick Actions** — links to the most common tasks for your role
- **KPI Cards** — summary metrics updated daily

### Step 3: Know Your Role

| Role | What You Can Do |
|------|----------------|
| `viewer` (SPD Tech) | Submit inspections, view own submissions |
| `spd_manager` | All viewer actions + view all facility inspections, review findings |
| `admin` | All manager actions + user management (LumenAI staff only) |

---

## Role-Based Workflows

### SPD Technician Workflow

**Primary task:** Log instrument inspections after decontamination.

**How to submit an inspection:**

1. From the Dashboard, click **New Inspection** (or navigate to `/inspection/new`)
2. Fill in the **Instrument Details** section:
   - Select instrument type from the dropdown
   - Enter the GSIN (Global Surgical Instrument Number) if available
   - Enter lot/batch number
   - Select material type
3. Fill in **Inspection Findings**:
   - Select all detected issues (checkboxes — select everything observed):
     - Blood, Bone, Tissue, Debris, Corrosion, Crack, Insulation Damage, Other
   - Set **Stain Detected** (Yes/No)
   - Enter confidence score if prompted (0–100)
4. Fill in **Processing Details**:
   - Select decontamination method
   - Enter sterilization cycle number
   - Note any deviations
5. Upload images (optional but encouraged):
   - Click **Upload Images**
   - Select JPEG, PNG, or TIFF files (max 10 MB each)
   - Images are hashed and not stored as raw files
6. Review all fields, then click **Submit Inspection**
7. A green banner will show your inspection ID — record this for your log

**Common errors:**

| Error Message | What to Do |
|---------------|-----------|
| "File exceeds 10 MB limit" | Compress the image or take a lower-resolution photo |
| "Unsupported file type" | Use JPEG, PNG, WEBP, or TIFF only |
| "Session expired — please log in again" | Return to `/login` and sign in again |
| "Required field missing" | Red border appears on the field — fill it in and resubmit |

---

### SPD Educator Workflow

**Primary task:** Review submitted inspections for training opportunities.

1. From the Dashboard, navigate to **Findings Queue** (`/findings`)
2. Filter by date range and instrument type
3. Review flagged inspections (those with `stain_detected: true` or multiple findings)
4. Use findings to identify recurring training gaps
5. Document training actions in your facility's LMS (LumenAI does not manage training records in the pilot)

> Training recommendation: Run a weekly debrief using that week's flagged inspections. Do not identify individual technicians by name in group debrief sessions.

---

### SPD Manager Workflow

**Primary task:** Monitor facility quality metrics and review CAPA queue.

**Daily check (5 minutes):**

1. Dashboard → review KPI cards (inspections today, flags today)
2. Click **CAPA Queue** (`/capa`) — review any new items
3. For each CAPA item, mark action taken or assign to a team member

**Weekly review (30 minutes):**

1. Navigate to **Analytics** (`/analytics`)
2. Review:
   - Inspection volume trend (week over week)
   - Stain detection rate
   - Instrument type breakdown
   - Finding category distribution
3. Export summary for weekly leadership report (use browser print-to-PDF)

**Important:** Analytics show *potential associations* and *quality review candidates* — not confirmed defect causes. All findings require human review before any workflow change.

---

### Vendor Representative Workflow

**Primary task:** Submit baseline instrument data and reference images.

1. Navigate to **Vendor Intake** (`/vendor-intake`)
2. Fill in Vendor and Product Details:
   - Company name, contact email, instrument model
   - Manufacturing lot range
   - Material specifications
3. Upload baseline reference images:
   - High-resolution images of clean instrument in standard lighting
   - Accepted formats: JPEG, PNG, TIFF (max 10 MB each)
   - Label images clearly before uploading (e.g., `model-A-front-clean.jpg`)
4. Submit the intake form
5. You will receive a baseline submission ID — retain this for your records

> Vendors do not have access to inspection data from any hospital. Your submissions are used only to establish reference baselines for instrument quality assessment.

---

### Quality Improvement (QI) Reviewer Workflow

**Primary task:** Review intelligence signals and emerging risk flags.

1. Navigate to **Operations Dashboard** (`/operations`)
2. Review **Emerging Risk Signals** panel:
   - Signals indicate instruments with ≥3 quality events in 90 days
   - Signals are flagged as *potential associations* — not confirmed risks
   - `human_review_required: true` on all signals — your review is mandatory before action
3. For each signal:
   - Investigate the associated inspections
   - Determine if pattern warrants a CAPA, staff training, or vendor notification
   - Document your review decision
4. Escalate to site manager if a pattern suggests systemic issue

> Do not take corrective action based on a signal alone. Use signals as investigation candidates only.

---

### Executive Workflow

**Primary task:** Monitor facility quality posture at a strategic level.

1. Dashboard → review **Executive Summary** cards (top of page)
2. Navigate to **Analytics** (`/analytics`) for trend data
3. Key metrics to monitor:
   - Monthly inspection volume (is the team using the system?)
   - Stain detection rate trend (improving, stable, or worsening?)
   - Open CAPA items
4. Quality briefing data is available for export (browser print-to-PDF)

> Metrics shown represent *observed quality indicators* and should be reviewed alongside clinical outcomes data from your existing quality systems. LumenAI data alone does not constitute a clinical finding.

---

## Common Errors and Support

### I can't log in

1. Confirm you're using the correct URL (ask your coordinator)
2. Check your email address is entered exactly as provided
3. If error says "Invalid email or password" — contact your site coordinator for a password reset
4. If error says "Unable to reach the server" — check your network connection

### My submission shows an error

1. Check all required fields (marked with a red asterisk *)
2. Check image file size (must be under 10 MB per file)
3. If the error persists after correcting fields, note the error message and contact your coordinator

### I submitted an inspection with wrong data

Contact your site coordinator immediately. During the pilot, corrections require manual database intervention by LumenAI support. Do not submit a duplicate entry.

### I don't see my inspection in history

Inspections appear in history within 60 seconds of submission. If not visible after 2 minutes, note your submission ID from the confirmation banner and contact support.

---

## Support Process

| Issue | Who to Contact | Response Time |
|-------|---------------|---------------|
| Can't log in | Site coordinator | Same day |
| Data or submission error | Site coordinator | Same day |
| System down / 5xx error | Site coordinator → LumenAI CS | 1 hour |
| Training question | Site educator or coordinator | Same day |
| Privacy concern | Site privacy officer | 24 hours |

**Do not include patient names, MRN numbers, or any patient-identifying information in LumenAI.** The system is designed for instrument tracking only.

---

## Data Entry Standards (Quick Reference)

| Field | Required | Format | Notes |
|-------|----------|--------|-------|
| Instrument type | Yes | Dropdown | Select closest match |
| GSIN | Recommended | Alphanumeric | Leave blank if unknown |
| Material type | Yes | Dropdown | |
| Stain detected | Yes | Yes/No | |
| Findings | Yes | Multi-select | Select all that apply |
| Decontamination method | Yes | Dropdown | |
| Sterilization cycle # | Recommended | Number | From your autoclave log |
| Site name | Yes | Text | Your facility's name |
| Vendor name | Recommended | Text | Instrument manufacturer |

---

## Pilot Scope Reminder

This is a pilot program. During the pilot period:
- Data is used for quality improvement analysis only
- No clinical decisions should be made solely on LumenAI output
- All findings are *potential associations* requiring human review
- The system has not received FDA clearance for diagnostic use
