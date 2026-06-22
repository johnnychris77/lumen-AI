# Surgical Readiness Index

**Version:** 1.0 | **Classification:** Methodology | **Status:** Active

**Important:** The Surgical Readiness Index is a decision-support tool. All outputs require human review before clinical or operational decisions are made. Scores do not constitute clinical assessments or regulatory findings.

---

## Overview

The Surgical Readiness Index (SRI) provides a composite 0–100 score reflecting the quality readiness of surgical instruments at facility, tray, or enterprise scope. It aggregates five operational quality dimensions into a single actionable tier, supported by blocking issues and advisory warnings.

---

## Scoring Components

| # | Component | Weight | Description |
|---|-----------|--------|-------------|
| 1 | Instrument Availability | 25% | Proportion of instruments in active status vs. quarantined/in_maintenance |
| 2 | Contamination Status | 25% | Contamination-free rate based on recent inspection outcomes |
| 3 | Inspection Compliance | 20% | Scheduled inspections completed within required windows |
| 4 | CAPA Backlog Health | 15% | Ratio of closed to open corrective and preventive actions |
| 5 | Sterilization Cycle Compliance | 15% | Instruments within manufacturer-rated cycle limits |

**Formula:**
```
SRI = (availability × 0.25) + (contamination × 0.25) + 
      (inspection × 0.20) + (capa × 0.15) + (sterilization × 0.15)
```

Each component is expressed as a 0–100 sub-score before weighting.

---

## Readiness Tiers

| Tier | Score Range | Color Code | Interpretation |
|------|-------------|------------|----------------|
| Green | 90–100 | #16a34a | Optimal readiness — standard monitoring applies |
| Yellow | 75–89 | #ca8a04 | Acceptable — review warnings and schedule improvements |
| Amber | 60–74 | #ea580c | Needs attention — address blocking issues within 5 business days |
| Red | 0–59 | #dc2626 | Critical — immediate review required |

---

## Scope Levels

**Facility scope** — aggregates all instruments under a single tenant facility. Primary use: daily operational readiness check.

**Tray scope** — evaluates a defined instrument set (e.g., laparoscopy tray). Use: pre-procedure quality verification.

**Enterprise scope** — aggregates across all facilities in a health system tenant. Use: executive reporting, network benchmarking.

---

## Blocking Issues vs. Warnings

**Blocking issues** — conditions that automatically pull a score toward Red and require resolution before the score can improve:
- More than 20% of instruments in quarantine
- Active uninvestigated contamination finding (severity: critical)
- CAPA backlog exceeding 30 days overdue

**Warnings** — advisory conditions that affect the score but do not require immediate escalation:
- Instruments approaching maximum cycle count (within 10% of limit)
- Inspection due within 3 days
- Identity verification status = false for more than 15% of instruments

---

## Score Interpretation Guidelines

- A **Green** score does not imply that instruments are clinically safe for use — that determination requires clinical staff review
- A **Red** score is a signal that quality review is warranted; it is not a finding of contamination or defect
- Scores are point-in-time assessments; they reflect data available at the time of computation
- Trend analysis over multiple score snapshots is more meaningful than any single reading

---

## API Usage

```
POST /api/infrastructure/readiness
{
  "scope": "facility" | "tray" | "enterprise",
  "reference_id": "<optional_tray_or_facility_id>"
}
```

Response includes:
- `readiness_score`: 0–100 numeric
- `readiness_tier`: green | yellow | amber | red
- `component_scores`: per-dimension breakdown
- `blocking_issues`: array of issue descriptions
- `warnings`: array of advisory messages
- `human_review_required`: always `true`
- `disclaimer`: standard quality-support disclaimer

---

## Limitations

- The SRI does not replace clinical sterilization validation protocols
- Scores are computed from data entered into Lumen AI; missing data reduces accuracy
- Network comparison requires k-anonymity ≥ 5 contributing facilities
- Predictive confidence intervals widen with smaller instrument populations
