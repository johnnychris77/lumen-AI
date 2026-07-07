# Implementation Timeline

A single-page view of the full implementation lifecycle, consolidating
`docs/customer/30-day-go-live-plan.md`, `60-day-optimization-plan.md`,
and `90-day-value-realization-plan.md`.

```
Day 0            Day 7            Day 14           Day 21           Day 30
  │                │                │                │                │
  ▼                ▼                ▼                ▼                ▼
Contract      Provisioning     Baseline &       Supervised        Go-Live
Signed &      & Access         Config           Pilot             Readiness
Kickoff       (Week 1)         (Week 2)         Inspections       Review
                                                (Week 3)

Day 30           Day 45           Day 60
  │                │                │
  ▼                ▼                ▼
Go-Live       Adoption Depth    Data Quality &
              Review            Feedback Loop
              (Weeks 5-6)       (Weeks 7-8)
                                        │
                                        ▼
                                  Day 60 Checkpoint

Day 60           Day 75           Day 90
  │                │                │
  ▼                ▼                ▼
Optimization  Value Data        Executive Value
Complete      Collection        Review
              (Weeks 9-10)      (Weeks 11-12)
                                        │
                                        ▼
                                  Day 90 Exit / Ongoing Success
```

## Milestone owners

| Milestone | Primary owner | Reviewer |
|---|---|---|
| Kickoff | LumenAI implementation lead | Executive Sponsor |
| Provisioning & config | LumenAI implementation lead | SPD Champion |
| Training | SPD Champion | LumenAI implementation lead |
| Go-live readiness | SPD Champion | Executive Sponsor |
| Optimization | SPD Champion | LumenAI implementation lead |
| Value realization | LumenAI implementation lead | Executive Sponsor |
| Ongoing success | Customer Success (LumenAI) | Executive Sponsor + SPD Champion |

## Dependencies to plan around

- Baseline availability from manufacturers/vendors can be the
  longest-lead-time item — start requesting baselines in Week 1, not
  Week 2, if the vendor relationship is new.
- Staff training schedules (shift coverage) often determine how fast
  Week 1–2 activities can actually happen — build slack into the plan
  for a 24/7 SPD operation vs. a single-shift department.
- A site with an existing Phase 18 pilot cohort already underway may
  compress the 30-day timeline since baseline/training work is already
  done — see `docs/validation/pilot-validation-protocol.md`.

## Variance handling

This timeline is a target, not a guarantee. If a site is tracking behind
(e.g., baseline loading incomplete by Day 14), extend the relevant phase
rather than compressing training or supervised-pilot time to hit an
artificial date — an SPD team pushed live before they're ready produces
worse adoption data and a worse Day 90 value story than a two-week delay
would.
