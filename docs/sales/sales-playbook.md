# LumenAI Sales Playbook
Version 1.0 | Sales — CONFIDENTIAL

## Positioning

**Category**: AI-Powered Surgical Instrument Intelligence
**Primary message**: "Catch what human eyes miss. Prevent what data predicts."
**One-sentence pitch**: LumenAI is the only SPD-purpose AI platform that detects
contamination, predicts instrument failure, and generates regulatory-ready audit
packages — before a single patient is at risk.

---

## Target Personas

| Persona | Title | Primary Pain | LumenAI Value |
|---------|-------|-------------|---------------|
| SPD Director | Director/Manager of Sterile Processing | Staff shortages, inspection quality, JC surveys | AI assists technicians; priority queue; audit readiness |
| VP Surgical Services | VP/Director of Surgical Services | OR delays from instrument failures, contamination events | Predictive analytics; throughput improvement |
| Infection Prevention | Infection Preventionist, IP Director | SSI rates, contamination tracking, regulatory compliance | Contamination detection; trend alerts; CAPA integration |
| COO | Chief Operating Officer | SPD throughput, cost reduction, OR efficiency | Digital twin; labor savings; bottleneck identification |
| CFO | Chief Financial Officer | ROI, cost justification, capital vs. opex | ROI model; 3-year payback; avoided event value |
| CIO/IT Director | CIO, VP IT, IS Director | Security, integration, compliance | SSO/OIDC, K8s, HIPAA BAA, API documentation |
| CNO | Chief Nursing Officer | Patient safety, staff competency, accreditation | AI copilot; compliance dashboards; RN trust |

---

## Competitive Landscape

| Competitor Category | Examples | LumenAI Advantage |
|--------------------|----------|------------------|
| Instrument tracking only | Censitrac, Censis, Meditrax | LumenAI adds CV detection, AI findings, predictive analytics |
| General clinical AI | Various | SPD-specific; faster ROI; lower deployment complexity |
| Manual audit tools | Spreadsheets, paper binders | Full automation, audit trail, peer benchmarking |
| CMMS suites | IBM Maximo, ServiceMax, TDSi | SPD-first focus; faster deployment; lower total cost |
| Quality management systems | MasterControl, Veeva Vault | SPD-specific; AI detection built in; no custom config required |

### Competitive Response Framework
**If prospect mentions Censitrac/Censis**:
"Those are excellent instrument tracking solutions. Tracking tells you where
instruments are — LumenAI tells you whether they're safe. We integrate with
tracking systems so you get location plus AI inspection intelligence."

**If prospect mentions AI from their EHR vendor**:
"General-purpose clinical AI is powerful but not trained on SPD instrument images.
LumenAI's CV model is purpose-trained on 12 contamination and defect categories
specific to surgical instrument inspection — it's not a general image classifier."

---

## Objection Handling

| Objection | Response |
|-----------|----------|
| "We already have an instrument tracking system" | "Tracking tells you where instruments are. LumenAI tells you whether they're safe. We integrate with your existing tracking system so you get both." |
| "Our SPD staff won't trust AI" | "AI assists, never replaces. Technicians keep final authority — they accept or override every AI finding. The 90-day pilot proves value before commitment, and the override log gives managers full visibility." |
| "We can't afford it" | "ROI is typically positive by Year 2 for regional medical centers. We can start with a $0 pilot — you pay nothing until we've proven value at your facility." |
| "We're worried about HIPAA" | "LumenAI processes instrument images only — no patient data is ever collected or stored. HIPAA BAA is included in all contracts." |
| "What about FDA clearance?" | "LumenAI is decision support software used by trained SPD professionals as one input in their inspection workflow. Our regulatory pathway is under active assessment. Hospitals routinely use quality management and decision support software of this type." |
| "Our IT team will block this" | "LumenAI is cloud-native, SSO-ready (Azure AD, Okta, Epic), and deployed on Kubernetes. We have a full IT security review package — firewall rules, OIDC config, HIPAA controls, penetration test schedule." |
| "We tried a vendor before and it didn't stick" | "We've built the pilot to be low-risk by design — $0 upfront, success criteria agreed before day 1, CSM on every weekly call. If it doesn't deliver, there's no obligation. We're confident because we've structured the pilot to prove value, not just demo features." |
| "Show me a reference customer" | "We're in early commercialization and protect customer confidentiality during pilots. We can connect you with an advisor who has evaluated the clinical accuracy data, or share our validation methodology and mock performance benchmarks." |
| "We need JCI / Magnet / DNV-specific compliance" | "Our regulatory module covers JC, AAMI ST79, CMS Conditions of Participation, FDA 21 CFR Part 820, and ISO 13485. We can scope a DNV/Magnet-specific report as a custom deliverable for Enterprise customers." |

---

## Discovery Questions

### SPD Director Discovery
1. "How do you currently prioritize which instruments get the most thorough inspection?"
2. "What's your most common finding when an instrument is returned from the OR with a complaint?"
3. "When a JC survey happens, how much manual work goes into pulling inspection records?"
4. "How many instruments per day does your team inspect? How long does each one take?"
5. "Have you ever had an instrument-related SSI event or near-miss? What was the root cause?"

### CFO/COO Discovery
1. "What's your annual instrument repair and replacement budget?"
2. "How many SPD FTEs do you have, and what's the average hourly loaded cost?"
3. "Have you quantified the cost of a single instrument-attributable SSI event?"
4. "Are you under pressure to reduce OR delays? What percentage are instrument-related?"
5. "What's your current accreditation prep cost in staff hours per survey cycle?"

### IP/Quality Discovery
1. "How do you currently track contamination events back to specific instruments?"
2. "What's your SSI rate trend over the last 24 months?"
3. "How confident are you in the completeness of your current inspection records?"
4. "When JC or CMS asks for instrument inspection documentation, how long does it take to pull?"

---

## Demo Flow (45 Minutes)

### 1. SPD Challenge Framing (5 min)
Open with the customer's specific pain — use discovery data.
- "You mentioned JC surveys are manual and stressful. Let me show you what that looks like with LumenAI."
- "You told me instrument-related OR delays cost you 2–3 cases a month. Here's how we address that."

### 2. CV Inspection Demo (10 min)
- Upload a demo instrument image (blood/tissue finding)
- Show AI confidence score and finding category
- Show priority queue: flagged instruments ranked by risk
- Demonstrate override workflow: technician accepts or overrides with reason

### 3. Ranking Engine (5 min)
- Show priority queue output for 20 instruments
- Explain ranking logic: contamination probability × instrument criticality × recurrence risk
- Highlight that AI does pre-triage so technicians focus effort on highest-risk items

### 4. Regulatory Readiness (5 min)
- Show JC readiness score dashboard
- Generate a sample audit package PDF in under 30 seconds
- "This is what used to take your team 80–200 hours before a survey."

### 5. Predictive Analytics (5 min)
- Show repair ROI: instruments flagged for early maintenance vs. emergency replacement cost
- Show contamination recurrence: instruments with recurring findings flagged for root cause

### 6. Digital Twin (5 min)
- Show throughput dashboard: inspections per hour by station
- Identify bottleneck station
- "With this visibility, your SPD Director can reassign staff in real time."

### 7. ROI Calculator (5 min)
- Enter customer's numbers live: FTE count, hourly rate, inspection volume
- Show 3-year ROI projection
- "At your volume, the model shows payback by Month 18."

### 8. Q&A + Pilot Proposal (5 min)
- "Based on what you've seen today, what would success look like in 90 days for your team?"
- Present pilot framework
- Offer to schedule technical kickoff within 2 weeks of LOI signature

---

## Pilot-to-Contract Conversion

### Conversion Tactics
- **Success data before proposal**: Always present KPI data before the commercial proposal. Data leads, price follows.
- **Reference customer intro**: Offer to connect to a peer hospital (when available) for hesitant prospects.
- **Multi-year discount as close lever**: 10% for 2-year, 15% for 3-year. Frame as "locking in current pricing."
- **CFO-level ROI report**: Generate from the executive dashboard. Present to CFO, not SPD Director.
- **Anchor at list price**: All commercial conversations start at list. Discounting requires VP Sales or CPO approval.

### Expansion-First Mindset
Every initial contract is a beachhead. Close the smallest deal needed to get a customer live, then expand.

---

## Health System Land-and-Expand Strategy

### Phase 1: Land
- Target: Single facility pilot (Starter or Professional)
- Champion: SPD Director or VP Surgical Services
- Duration: 90-day pilot
- Goal: Prove value at one facility; get internal sponsor

### Phase 2: Expand
- Trigger: Successful pilot; champion gains internal credibility
- Target: 2–4 additional facilities (Enterprise tier)
- Champion: Now includes COO or VP Supply Chain
- Timeline: 3–6 months post-pilot conversion

### Phase 3: Enterprise Deal
- Trigger: Network-level value visible (cross-facility benchmarking, vendor scorecards)
- Target: Full health system at network pricing
- Champion: C-suite (COO, CFO, CIO)
- Timeline: 12–18 months post-initial pilot

### Phase 4: Lock-In
- EHR integration deployed (Epic SMART on FHIR)
- SSO across all facilities (Azure AD)
- Network benchmarking active (switching cost: lose years of comparative data)
- Manufacturer portal subscriptions generating secondary revenue

### Phase 5: Upsell
- Manufacturer portal subscriptions: $500/month per manufacturer
- RWE program participation: 5% discount in exchange for clinical data rights
- Custom baseline training: Health System add-on
- White-label UI: Custom branding for network identity

---

## Sales Process and Stage Definitions

| Stage | Definition | Exit Criteria |
|-------|-----------|---------------|
| 0 - Prospecting | Identified target; initial outreach | Response received |
| 1 - Discovery | Discovery call completed | Pain confirmed; stakeholders mapped |
| 2 - Demo | Demo delivered | Positive reaction; pilot interest |
| 3 - Pilot/LOI | LOI signed or pilot started | Technical kickoff scheduled |
| 4 - Commercial | Pilot underway; commercial conversation active | Proposal delivered |
| 5 - Negotiation | Contract in legal review | Redlines received or approved |
| 6 - Closed Won | Contract signed | HIPAA BAA executed; CSM assigned |
| 6 - Closed Lost | Explicit no or 90-day no-response | Reason documented in CRM |

---

## Ideal Customer Profile (ICP)

### Tier 1 ICP (Highest priority)
- Community or regional hospital, 100–400 beds
- SPD team of 5–25 FTEs
- Recent JC survey with instrument-related deficiencies
- Active interest in reducing OR delays or SSI rates
- Budget authority at SPD Director or VP Surgical Services level

### Tier 2 ICP
- Academic medical center, 400–800 beds
- Multi-OR facility, high instrument volume
- Quality department actively tracking SSI metrics
- CIO/IT team familiar with cloud SaaS onboarding

### Tier 3 ICP (Health System — strategic)
- IDN or multi-hospital system, 3–20 facilities
- Centralized SPD or distributed SPD with network governance
- GPO membership (Premier, Vizient, HPG) for contract vehicle
- CFO-driven cost reduction initiative underway

### Exclusion Criteria (Not a fit now)
- Single-specialty clinics (ASCs) with < 200 instruments/month
- Facilities with no IT resources for SSO/cloud onboarding
- Organizations under active M&A (budget freeze risk)
- International facilities (not supported in V1; roadmap item)
