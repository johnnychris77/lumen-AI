# Reference Customer Program

**Version:** Phase 12  
**Date:** 2026-06-23  
**Audience:** LumenAI Account Management, Marketing, CS Leadership  
**Purpose:** Capture, manage, and leverage customer success stories for growth and credibility

---

## Program Overview

The LumenAI Reference Customer Program captures deployment success stories, ROI metrics, and lessons learned to:
1. Accelerate future sales cycles (peer validation)
2. Build LumenAI's clinical evidence base
3. Improve the deployment playbook with each customer

Participation is always opt-in and requires explicit written customer approval before any story is shared externally.

---

## Reference Tiers

| Tier | Customer Criteria | Commitment | Benefit |
|------|-------------------|------------|---------|
| Champion | Health Score ≥ 70, ≥200 inspections, ≥5 critical findings detected | Verbal reference on request | Priority roadmap input |
| Case Study | Champion + written story approved | Written case study on website | Co-marketing, conference mention |
| Speaking Reference | Case Study + agrees to present at event | Webinar or conference presentation | Travel covered, product credit |
| Research Partner | Willing to co-publish outcomes data | IRB-coordinated study | Custom analytics, dedicated CSM |

---

## Success Story Framework

Each success story must be reviewed by the customer and approved in writing before any external use.

### Required Elements

```
FACILITY: [Anonymized if not approved for naming — "Mid-size regional hospital, Southeast US"]
DEPLOYMENT DATE: [Month/Year]
INSTRUMENT FLEET: [Scope types, approximate fleet size — no patient data]
DEPLOYMENT SCOPE: [Departments, user roles]

── OUTCOMES ─────────────────────────────────────────────────────────────
Inspections Completed:       [N] in [period]
Critical Findings Detected:  [N] — [type, e.g., "crack in ureteroscope channel"]
Time Saved:                  [N] hours estimated
Cost Avoidance:              $[N] estimated
Baseline Coverage Achieved:  [N]%
Customer Health Score:       [Green/Yellow at Day 90]

── CUSTOMER QUOTE (written approval required) ───────────────────────────
"[Quote from SPD Director or C-suite sponsor]"
— [Title], [Anonymized facility or approved name]

── LESSONS LEARNED ──────────────────────────────────────────────────────
What accelerated adoption: [e.g., "Vendor submitted baselines in Week 1"]
What caused friction:      [e.g., "IT firewall delayed SMTP config by 3 days"]
What we would do differently: [e.g., "Schedule executive training on Day 1"]
```

---

## ROI Metrics Capture Template

Pull from `/value-realization` export at Day 30, 60, and 90.

| Metric | Day 30 | Day 60 | Day 90 |
|--------|--------|--------|--------|
| Inspections completed | | | |
| Critical findings detected | | | |
| Time saved (hrs) | | | |
| Labor value ($) | | | |
| Finding avoidance value ($) | | | |
| CAPA value ($) | | | |
| SSI risk reduction (%) | | | |
| Total estimated value ($) | | | |
| Customer Health Score | | | |
| Baseline coverage (%) | | | |

> All figures are estimates for business case purposes. Customer approves before external use. LumenAI makes no claim of clinical outcome guarantees or FDA clearance.

---

## Testimonial Collection Process

1. **Identify candidate** — CS Lead flags customer at Day 60 if Health Score ≥ Green and ≥1 critical finding detected
2. **Request permission** — CS Lead emails SPD Director with opt-in request and template
3. **Draft story** — CS Lead drafts using the framework above; no patient data, no PHI
4. **Customer review** — Customer reviews and approves in writing (email is sufficient)
5. **Marketing review** — LumenAI marketing reviews for compliance and branding
6. **Legal review** — LumenAI legal confirms no regulatory claims, no PHI
7. **Publish** — Only after all three approvals

**Timeline:** Allow 4–6 weeks from request to publication.

---

## Deployment Lessons Learned

Capture after every deployment, regardless of outcome. File in `#cs-lessons-learned` Slack channel and update the deployment playbook.

### Template

```
DEPLOYMENT: [Facility] — [Month Year]
CS LEAD: [Name]
HEALTH SCORE AT DAY 90: [Score / Band]

WHAT WENT WELL:
- 
- 
- 

WHAT CAUSED FRICTION:
- 
- 

WHAT WE CHANGED IN THE PLAYBOOK:
- 
- 

WOULD CUSTOMER BE REFERENCE? [Yes / Pending / No]
REASON: 
```

### Common Lessons (aggregated from pilot program)

| Category | Lesson | Playbook Update |
|----------|--------|----------------|
| Vendor | Vendors who receive an onboarding call in Week 1 submit 3× faster | Added Session 3 (Vendor Training) to standard schedule |
| IT | SMTP config blocked by firewall at 2 of 3 deployments | Added firewall pre-check to T–3 configuration checklist |
| Training | Technicians who practice 3+ test inspections in training make fewer errors in production | Increased practice time in Session 1 to 40 min |
| Baseline | SPD Managers who approve baselines in Week 1 see 40% higher inspection confidence by Week 4 | Added "first baseline approval" to Day 7 milestone |
| Engagement | Facilities where executive sponsor attends kick-off have 28% higher Day 90 health scores | Added executive sponsor attendance to kick-off agenda |

---

## Reference Customer Privacy Constraints

- **No PHI** — no patient identifiers, procedure names, or patient outcomes in any story
- **No facility identification without written approval** — use "regional hospital, X state" until approved
- **No causation claims** — "potential finding," "possible association," "quality review recommended"
- **No regulatory claims** — do not state or imply FDA clearance, AORN certification, or Joint Commission endorsement
- **Anonymize staff** — refer to "SPD Manager" or "Director of Sterile Processing," not names, unless approved
- **Customer owns the story** — if customer retracts consent, remove all external uses immediately

---

## Program Metrics

Track quarterly:

| Metric | Target |
|--------|--------|
| Customers eligible for reference (Health ≥ 70) | ≥ 50% of deployed base |
| Customers enrolled in program (any tier) | ≥ 25% of eligible |
| Active case studies published | ≥ 2 by Month 6 |
| Reference calls completed | ≥ 5 per quarter |
| New deployments citing reference as factor | ≥ 30% |

---

*LumenAI Account Management & Marketing — Internal Use Only*  
*All customer stories require written customer approval before external use.*  
*LumenAI makes no claim of FDA clearance, regulatory approval, or clinical outcome guarantees.*
