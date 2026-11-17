# Stage 6C — Real Evidence Acquisition & First Scientific Benchmark

Status: **research-only.** Reuses all Stage 4–6B infrastructure (no new AI engine,
annotation database, dataset registry, or governance platform). Extends Stage 6B
(PR #168). No model promotion, no clinical recommendation, no prospective clinical
testing, no deployment.

## Stage 6C scientific-readiness decision

**`BLOCKED_REAL_IMAGE_BENCHMARK`** — no authorized, independently-reviewed real-image
cohort and no license-and-source-verified scientific checkpoint exist in this
environment. Per the stop condition, Stage 6C completes the **minimal safety fixes**
(§2) and publishes this blocker report. No random-weight or synthetic result is
presented as scientific performance.

## The four distinct states

| State | Stage 6C status |
|---|---|
| **Implemented software (tested)** | ✅ Authenticated scientific-approval resolution, authorization-gated acquisition workflow, traceable review records; benchmark gated on record-backed readiness. |
| **Executed model experiments** | ✅ PaDiM + PatchCore run through the governed localizer (coverage 1.0, deterministic) — **synthetic inputs / random-weight backbone: pipeline verification only.** |
| **Independent scientific validation** | ❌ None — `BLOCKED_REAL_IMAGE_BENCHMARK` (resolved checks below). |
| **Prospective clinical authorization** | ❌ None (Stage 6B: `NOT_READY_FOR_PROSPECTIVE_CLINICAL_VALIDATION`). |

## §2 — Authenticated scientific-approval controls (minimal safety fixes)

`scientific_authorization.py` resolves every approval against authoritative records,
**fail-closed** — no caller-supplied string/bool/dict is accepted as proof:

- **Approver** → `UserRoleAssignment` (authenticated identity + an allowed role).
- **License / source evidence, institutional data authorization, statistical protocol
  sign-off** → approved `GovernanceApproval` records whose reviewer is itself an
  authenticated approver.
- **Research-use permission** → granted, non-withdrawn `ConsentRecord` (a withdrawn
  consent fails).
- `register_scientific_checkpoint` resolves the approver + license + source records
  before registering; `assert_scientific_checkpoint` refuses random-weight /
  research-execution backbones and anything lacking resolved evidence.

Regression tests (`test_stage6c_authorization.py`): forged/unknown approver, wrong
role, nonexistent/unapproved evidence, approval reviewed by an unauthenticated
reviewer, withdrawn consent, unauthorized statistical reviewer, and the full
record-backed readiness assessment (blocked → resolved).

## §3 — Governed real-image acquisition workflow

`research_acquisition.acquire_research_cohort` gates on `verify_data_authorization`
first (institutional authorization + live consent), then validates each image against
the acquisition contract and reports data quality + cohort readiness. It **imports no
bytes here** and is the governed hand-off point to Project Canvas / LCID; without
resolved authorization it returns **`BLOCKED_ACQUISITION`**. No hospital data without
institutional authorization; no fabricated/relabeled images; research-only specimens
never return to clinical use. Required feasibility categories: verified-clean,
documented-corrosion, measured-pitting, confirmed/simulant-residue, benign-confounder,
borescope-lumen.

## §5 — Models

The governed PaDiM/PatchCore runner now additionally gates the real-image benchmark on
`assess_scientific_readiness`. In this environment all record-backed checks are BLOCKED:

- `data_authorization`: no approved institutional-authorization record / consent.
- `statistical_signoff`: no authenticated statistical reviewer + approved protocol.
- `scientific_checkpoint`: `smoke_stub` is explicitly **not** approved for scientific
  claims (random-weight / research-execution).

→ **`BLOCKED_REAL_IMAGE_BENCHMARK`** (`governed_benchmark_result.json`). The random-weight
execution (coverage 1.0, deterministic) is pipeline verification only.

## §6 — Scientific evidence & model review

`review_record.py` builds traceable records linking specimen · image · model prediction ·
spatial mask · laboratory evidence, keeps the four layers distinct (clinical disposition
never produced), and reports each prediction as **match / miss / conflict /
ground-truth-unavailable** against approved ground truth (a confirmed identity is carried
only when lab-confirmed; truth for an abnormal label is "unavailable" until lab-confirmed).
`summarize_outcomes` surfaces **false negatives (misses)** prominently and reports counts
only — never an accuracy claim. No diagnosis, severity, or instrument-release decision.

## Outstanding external approvals (what still prevents the benchmark)

1. **Institutional/ethics** authorization + data-use agreements for authorized real
   images (external + borescope); recorded as a `GovernanceApproval`.
2. **Research-use consent** recorded and not withdrawn.
3. **Laboratory** reference evidence per category (or documented reference simulants),
   independently reviewed with recorded reviewer agreement.
4. **Licensed pretrained checkpoint** with verified SHA-256 and `GovernanceApproval`
   license + source records (then `register_scientific_checkpoint`).
5. **Statistical reviewer** (authenticated role) + approved statistical protocol record.

## Acceptance

Stage 6C delivers the **authenticated safety fixes and the authorization-gated
integration points** for the first real research cohort, plus an **explicit,
evidence-based blocker report** naming the external approvals still required. It is
**not** scientific or clinical validation and is not validated by its passing tests.
