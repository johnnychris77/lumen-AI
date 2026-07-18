# LPZ-DIR-004 — Borescope Selection Scorecard (vendor-neutral)

**Purpose:** a repeatable, weighted, evidence-based framework to compare
candidate borescopes. **No product is recommended or purchased on the basis of
brand.** A device is eligible only after (a) meeting every MUST in
`BORESCOPE_HARDWARE_REQUIREMENTS.md`, and (b) being scored here with documented
evidence for each criterion.

Example vendors that MAY be evaluated (illustrative, not endorsements, not an
exhaustive or preferred list): Olympus / IPLEX, KARL STORZ, Stryker, Gradient
Lens (Hawkeye), ViZaar, and others. Inclusion here is **not** a recommendation.

## Gate before scoring

| Gate | Pass condition |
|---|---|
| MUST requirements | All MUST items in `BORESCOPE_HARDWARE_REQUIREMENTS.md` satisfied |
| Disqualifying conditions | None present |
| Evidence | Vendor datasheet + a hands-on/loaner capture sample available |

A device that fails the gate is **not scored** — it is recorded as
DISQUALIFIED with the reason.

## Weighted criteria

Each criterion is scored **0–5** (0 = unacceptable, 5 = excellent) against the
rubric below, then multiplied by its weight. Weights sum to 100.

| # | Criterion | Weight | What "5" looks like |
|---|---|---:|---|
| 1 | Image quality | 20 | Meets/exceeds resolution target; sharp across DoF; low noise; repeatable exposure |
| 2 | Probe compatibility | 12 | Diameter/length/articulation cover all in-scope bench targets |
| 3 | Export capability | 14 | Original-quality lossless export via open path; batch export |
| 4 | Metadata support | 12 | Rich, machine-readable capture metadata; no forced PHI fields |
| 5 | Software integration | 12 | Documented SDK/API or clean removable-media/network ingestion |
| 6 | Reliability | 10 | Documented MTBF/cycle life; stable across a full session; no focus/WB drift |
| 7 | Cost of ownership | 8 | Transparent total cost (device + probes + consumables + service) |
| 8 | Serviceability | 6 | Replacement probes/tips available; documented repair turnaround |
| 9 | Future scalability | 6 | Second unit/additional probes obtainable; export scales to dataset volumes |
| — | **Total** | **100** | — |

## Scoring rubric (per criterion)

| Score | Meaning |
|---|---|
| 5 | Fully meets intent with documented evidence; no reservations |
| 4 | Meets intent with minor, documented caveats |
| 3 | Acceptable; workable with a documented mitigation |
| 2 | Marginal; significant reservation |
| 1 | Poor; only usable with major workaround |
| 0 | Unacceptable for this criterion |

## Weighted-score computation

```
weighted_total = Σ (criterion_score × criterion_weight) / 5
```

(Dividing by 5 normalizes the maximum to 100.) Record the raw score, the
weight, and the **evidence source** for every criterion — a score without cited
evidence is invalid.

## Scorecard template (one per candidate)

| Field | Value |
|---|---|
| Candidate device | _(model)_ |
| Evaluator | _(name/role)_ |
| Date | _(YYYY-MM-DD)_ |
| MUST gate | PASS / DISQUALIFIED (reason) |

| # | Criterion | Weight | Score (0–5) | Weighted | Evidence source |
|---|---|---:|---:|---:|---|
| 1 | Image quality | 20 | | | |
| 2 | Probe compatibility | 12 | | | |
| 3 | Export capability | 14 | | | |
| 4 | Metadata support | 12 | | | |
| 5 | Software integration | 12 | | | |
| 6 | Reliability | 10 | | | |
| 7 | Cost of ownership | 8 | | | |
| 8 | Serviceability | 6 | | | |
| 9 | Future scalability | 6 | | | |
| — | **Weighted total (/100)** | | | | |

## Decision rule

* **≥ 80** and all MUST met → *eligible* for qualification (IQ/OQ/PQ). Eligible
  ≠ purchased: procurement occurs only after qualification passes on a loaner
  or on the acquired unit, per program governance.
* **65–79** → conditionally eligible; requires a documented mitigation plan for
  each criterion scored ≤ 2.
* **< 65** → not eligible.

## Governance

* At least two candidates SHOULD be scored before any selection, to keep the
  process vendor-neutral.
* No brand preference, incumbent relationship, or price alone may override the
  evidence-based score.
* All completed scorecards are archived as evidence (see
  `PILOT_ZERO_LAB_DESIGN.md` §Evidence Archiving).

No purchasing recommendation is made in this document; it defines **how** a
future selection will be justified.
