# Executive Demo Walkthrough

**Version:** Phase 10 — Pilot-to-Production Release  
**Date:** 2026-06-23  
**Audience:** SPD Directors · C-Suite · Investors · Infection Prevention · Quality Leaders  
**Duration:** 15–20 minutes (full) · 8 minutes (C-suite condensed)

---

## Pre-Demo Setup

1. Log in as `spd_manager` or `admin` at `/login`
2. Navigate to `/executive-command-center` — confirm KPIs are loading
3. Confirm at least one inspection exists (run seed if needed)
4. Browser: 1080p or larger, full-screen, dark sidebar preferred

---

## Demo Narrative: "What LumenAI Does in 10 Slides"

> **Opening line:** "Every contaminated surgical scope that reaches the OR is a near-miss. LumenAI makes contamination visible, measurable, and preventable — starting at the point of reprocessing."

---

## Stop 1 — Dashboard (`/`)

**Time:** ~2 minutes

**What to show:**
- Contamination KPI grid (7 categories: blood, bone, tissue, debris, corrosion, crack, insulation damage)
- Pilot KPIs: total inspections, high-risk instruments, open findings
- Baseline Coverage section: % approved, awaiting approval

**Key message:**
> "This is a real-time view of instrument health across your SPD. Every category here represents a finding type that, if missed, could reach a patient."

**Talk track:**
- Point to the red/amber KPIs first — these drive urgency
- Baseline Coverage < 80% → "This is a gap we're actively closing with your vendor"
- "All scores are AI-assisted. Every flagged finding requires a qualified human review before action."

---

## Stop 2 — Executive Command Center (`/executive-command-center`)

**Time:** ~3 minutes

**What to show:**
- Operational: Total Inspections, High Risk Instruments, Open Findings, Open CAPAs
- Contamination breakdown: Blood / Bone / Tissue / Debris
- Instrument Health: Corrosion, Crack, Baseline Coverage, Passport Coverage
- Pilot Metrics: Images Collected, Baselines Approved, Vendor Submissions, Review Backlog

**Key message:**
> "This is the view a Quality Director, CNO, or CFO would see first thing in the morning. Every number links to the underlying workflow."

**Talk track for investors:**
- "Four KPI grids, 16 metrics, one screen. This is what differentiates LumenAI from spreadsheet-based SPD tracking."
- Click a KPI card — navigate to the underlying workflow
- "The review backlog is the commercial signal — every pending baseline is a touchpoint with a vendor or manufacturer."

---

## Stop 3 — New Inspection (`/inspection/new`)

**Time:** ~2 minutes

**What to show:**
- Lumened scope types appear first in the instrument type dropdown
- Barcode field → scan → "✓ Scanned" indicator
- Finding category checkboxes with `?` tooltip definitions
- Select "Crack / Fracture" at 95% confidence → submit
- Success state: Risk Score badge (red / Critical) appears immediately
- "Human review required" label

**Key message:**
> "A SPD technician can complete an inspection in under 60 seconds. They get an immediate risk signal. They don't need to navigate to another screen."

**Talking points:**
- "The finding categories reflect clinical significance — crack and insulation damage score higher than debris because the clinical consequence is higher."
- "Every submission is tenant-isolated and audit-logged."

---

## Stop 4 — Instrument Registry (`/infrastructure`)

**Time:** ~2 minutes

**What to show:**
- Registry tab: list of instruments with barcode, UDI, manufacturer, model
- Click a row — show detail panel
- Navigate: `/infrastructure?tab=passport&instrument=FURO-001`

**Key message:**
> "Every instrument in your fleet has a digital identity. Barcode, UDI, KeyDot, QR — we support all identification modalities used in modern SPD."

---

## Stop 5 — Instrument Passport V2 (`/instrument-passport?instrument=FURO-001`)

**Time:** ~3 minutes

**What to show:**
- Identity panel: Internal ID, Manufacturer, Model, Barcode, UDI, KeyDot
- Risk Intelligence: current score with trend arrow, recommended actions
- Findings Summary: contamination badges with counts
- Inspection Timeline: chronological history with risk scores and status
- Baseline History: approved/pending/rejected

**Key message:**
> "This is the full lifecycle record of a single instrument. One screen tells you: what it is, what's been found on it, how its risk is trending, and what to do next."

**For Quality Leaders:**
- "This is your audit trail. Every inspection, every finding, every approval is timestamped and immutable."
- "Joint Commission asks for documentation of your reprocessing outcomes. This is it."

**For Infection Prevention:**
- "If a patient event occurs, you can pull the passport of every instrument in that tray in 30 seconds."

---

## Stop 6 — Baseline Library (`/baseline-library`)

**Time:** ~1 minute

**What to show:**
- List of approved baselines by instrument category
- Status badges: approved / pending / rejected
- Link to upload page

**Key message:**
> "Baselines are the reference images AI compares against during inspection. More approved baselines = more accurate risk scores."

---

## Stop 7 — Global Registry (`/global-registry`)

**Time:** ~1 minute

**What to show:**
- Summary stats: Instruments, Manufacturers, Vendors, Baselines, Inspections, Passport Records
- Search + risk filter
- Phase 20–26 preview card

**Key message:**
> "This is the foundation of our network intelligence roadmap. Today it tracks your fleet. In Phase 20, it compares your contamination rates anonymously against peer hospitals."

**For investors:**
> "Network effects. The more facilities that onboard, the more accurate the benchmarks, the more valuable the platform becomes to every facility on it."

---

## Stop 8 — Surgical Readiness (`/surgical-readiness`)

**Time:** ~2 minutes

**What to show:**
- Overall Readiness Score (composite %)
- Five dimensions with color-coded meters: Facility, Instrument, Tray, Inspection Completion, Baseline Coverage
- Tray Readiness table: TRAY-UROLOGY-01 → Ready, TRAY-ENDO-01 → Caution

**Key message:**
> "Before a tray goes to the OR, you should know its readiness score. Not from memory, not from a paper log — from a system that integrates inspection history, contamination findings, and baseline coverage into a single number."

**For SPD Directors:**
- "Caution trays trigger a review protocol. Ready trays proceed. This replaces the subjective visual check."

---

## Stop 9 — CAPA Workflow (`/capa`)

**Time:** ~1 minute

**What to show:**
- Open CAPA queue
- Status: open / in-progress / closed
- Link from finding to CAPA

**Key message:**
> "When a critical finding is confirmed, LumenAI automatically creates a CAPA record. Your Quality team has a documented corrective action with audit trail — not a sticky note."

---

## Stop 10 — Executive Outcomes

**Close with these three statements:**

### For Hospital Executives
> "LumenAI gives your SPD Director and Infection Prevention team a shared language — risk scores, not opinions. That shared language is what prevents contamination events from becoming never-events."

### For Quality Leaders
> "Every inspection is documented, every finding is traceable, every corrective action is logged. Your next Joint Commission survey has an answer to 'show me your reprocessing outcomes.'"

### For Investors
> "We're building the operating system for surgical instrument safety. Bon Secours is the pilot. The architecture is designed for 100 facilities. Network effects are baked in from day one."

---

## Condensed C-Suite Version (8 minutes)

| Stop | Page | Time |
|------|------|------|
| 1 | Dashboard | 1 min |
| 2 | Executive Command Center | 2 min |
| 3 | New Inspection (demo submission) | 1.5 min |
| 5 | Instrument Passport V2 | 1.5 min |
| 8 | Surgical Readiness | 1 min |
| 10 | Outcomes close | 1 min |

---

## Objection Handling

| Objection | Response |
|-----------|----------|
| "How is this different from our current paper log?" | "Paper logs don't give you a risk score. They don't tell you a crack was found on that scope last week. They don't connect to your CAPA workflow. LumenAI does all three." |
| "Is this FDA cleared?" | "LumenAI is a quality management and decision-support platform. It assists clinically trained staff — it does not replace their judgment. All AI outputs require human review before clinical action." |
| "What happens with our data?" | "Your data is tenant-isolated. No raw inspection records are shared with other facilities. Network benchmarking uses anonymized aggregate statistics only." |
| "What does implementation look like?" | "Pilot was live in 6 weeks at Bon Secours. Phase 1 is baseline image collection and staff onboarding. First inspections run in week 2." |
| "How do we know the AI is accurate?" | "Baseline images establish the reference. Confidence scores are shown on every finding. Low-confidence findings surface for human review. The system gets more accurate as more baselines are approved." |

---

## Demo Data Reference

| Item | Value |
|------|-------|
| Pilot Facility | Bon Secours (demo tenant) |
| Demo Instrument | FURO-001 (Flexible Ureteroscope) |
| Passport URL | `/instrument-passport?instrument=FURO-001` |
| Registry Deep Link | `/infrastructure?tab=passport&instrument=FURO-001` |
| Total Demo Inspections | ~2,847 (seeded) |
| Demo Baselines Approved | 34 |
| Demo Images | 120 (pilot library) |

---

*LumenAI — Internal Use Only*  
*All AI outputs require qualified human review before clinical action.*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*
