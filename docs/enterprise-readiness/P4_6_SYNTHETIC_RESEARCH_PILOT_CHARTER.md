# P4.6 — Internal Synthetic Research Pilot Charter

**Program:** LumenAI Enterprise AI Governance — Research Assurance
**Prepared by (role):** Enterprise AI Governance Program Lead / Research Assurance Coordinator
**Date:** 2026-11-17
**Status:** **DRAFT CHARTER — not authorized.** This charter defines the *proposed* scope of an
internal synthetic-only research pilot. It does **not** authorize the pilot. Pilot authorization
requires the documented approvals in `P4_6_RELEASE_AUTHORIZATION_RECORD.md` and the prerequisite
decisions recorded in `P4_5_DECISION_TRACKING_REGISTER.md`. **HOLD remains in effect** until those
are authentically recorded.

**Relationship to prior work.** This charter adapts the P4.5 assurance package
(`P4_5_*`, PR #179) for a *narrower* context — LumenAI-owned, synthetic-data-only research — **without
weakening** any security or scientific-governance requirement. Where a P4.5 requirement is a
prerequisite for *institution-sponsored* research on real data, it stays open and is **not** waived
by narrowing scope (see `P4_6_GOVERNANCE_APPLICABILITY_MATRIX.md`).

**Reviewed integration content:** combined code `7c0f679` (via #178 `8574a2a`, all 7 CI jobs green
incl. PostgreSQL 16); PR #176 `fdaee8e`, #177 `b35e552`; `main` `0f2ec588` (unchanged). No code is
changed by P4.6; this is a documentation-only governance package.

---

## 1. Purpose and principle

Establish a **controlled, internal, synthetic-data-only** research pilot environment in which the
Stage 5–6 research/benchmarking pipeline can be exercised **for engineering and research-method
validation only** — never for clinical or production use — under the same fail-closed security and
scientific-integrity controls validated in #176/#177/#178.

**Governing principle:** narrowing the *data* to LumenAI-owned synthetic material reduces
**data-rights / institutional-authorization** exposure. It does **not** reduce the need for
tenant isolation, authentication, audit durability, benchmark integrity, independent security
review, or scientific-methodology sign-off. Engineering completion is **not** governance
authorization.

## 2. Scope — synthetic-only

### 2.1 In scope (permitted)
- **Data:** only **synthetic images and labels generated or owned by LumenAI** for research, with a
  completed entry in `P4_6_SYNTHETIC_DATASET_MANIFEST.md` (provenance, classification, labeling
  method, permitted use, retention, verification evidence) **before** use.
- **Activities:** exercising the research pipeline end-to-end on synthetic data —
  cohort-readiness checks, anomaly-localization research methods (PaDiM/PatchCore research
  adapters), metric computation (Dice/IoU/AP), calibration, reproducibility/determinism checks,
  artifact-store round-trips, and audit-trail verification.
- **Tenancy:** LumenAI-owned research tenant(s) only; cross-tenant access must remain impossible
  and is a stop condition if observed.
- **Outputs:** research-method findings labelled **research-only / not clinically validated**.

### 2.2 Out of scope (prohibited — hard stops)
- **No real patient data, no institution-controlled research data, no PHI**, in images, labels,
  metadata, filenames, or derived artifacts. Any such data entering the environment is a **stop
  condition**.
- **No clinical use, no clinical validation claims, no diagnostic or triage output** presented as
  actionable.
- **No production deployment**, no hospital research, no external/institution-sponsored research.
- **No regulatory/FDA clearance claim** anywhere.
- **No publication of performance as validated** — all real-benchmark paths remain BLOCKED pending
  the governance prerequisites; synthetic results are method checks, not performance evidence.
- **No weakening** of authentication, authorization, tenant isolation, audit, or the artifact-store
  hex-encoding (RGI-04). No reintroduction of `Bearer dev-token` or any auth bypass.

### 2.3 Permitted datasets (enumerated gate)
A dataset is permitted **only if all** hold: (a) generated or owned by LumenAI; (b) verifiably
synthetic — no real-image derivation, no PHI; (c) a complete manifest entry exists; (d) classified
**synthetic-research**; (e) licensing/use-rights are LumenAI-internal-research; (f) retention and
disposal terms recorded. Absence of any ⇒ **not permitted** (fail-closed).

### 2.4 Prohibited data (explicit)
Real patient images; de-identified-but-real clinical images; institution-owned datasets; any
third-party dataset whose license does not permit LumenAI internal research use; any data of
uncertain provenance; any data whose synthetic status is **asserted but not evidenced**.

## 3. Intended research activities and research-only restrictions
- The pipeline runs under `research_execution_only` / `require_scientific` gating; synthetic/
  non-scientific checkpoints force `scientifically_valid = False` and metrics are **not** published
  as scientific evidence (RGI-03).
- Every output carries a research-only marker and `human_review_required: true` where correlation
  outputs are produced; **no causal language** — only "potential association", "possible
  contributing factor", "quality review recommended".
- Scientific pixel-metric publication stays **BLOCKED** until RGI-02 reviewer framework and RGI-10
  convention are authoritatively decided (see the respective records).
- Real-data benchmarking stays **BLOCKED** (RK-08) by design.

## 4. Pilot stop conditions (immediate HOLD / halt)
The pilot **must halt** and escalate to the Release Authority and the Governance Program Lead if any
of the following is observed:
1. Any real/PHI/institution-controlled data present in the environment (§2.2).
2. Any cross-tenant read or write, or any tenant-isolation control failing.
3. Any authentication/authorization bypass (incl. reappearance of `dev-token`), or any
   out-of-gate image-byte read reachable from a request path (relates to SEC-174-02).
4. Any audit-log gap: a denial or access decision not durably recorded (SEC-174-01 chain broken).
5. Any synthetic dataset used **without** a complete, verified manifest entry, or whose synthetic
   status cannot be evidenced.
6. Any scientific metric or performance figure presented as validated/clinical, or any causal/FDA
   claim.
7. Any artifact-store behavior that resolves a non-hex/legacy reference or permits path traversal
   (RGI-04 / C-09 / C-10).
8. Discovery of a new release-blocking security finding during independent review.
9. Any attempt to expand scope to real/institutional data or production without the full
   institution-sponsored prerequisite set (applicability matrix).

A stop condition is a governance event: record it, halt the affected activity, and do not resume
until the condition is remediated and the resumption is authorized.

## 5. Authorization gate (what must be true to start)
This charter is actionable **only after** all are recorded authentically:
- **P4.6 release authorization** signed by the LumenAI Release Authority
  (`P4_6_RELEASE_AUTHORIZATION_RECORD.md`).
- **RGI-01 (synthetic)** LumenAI data-provenance/ownership/licensing decision recorded.
- **RGI-02** internal reviewer framework decision recorded (if any metric is to be reported).
- **RGI-10** scientific-methodology decision recorded (if pixel metrics are to be reported).
- **SEC-174-02 + SEC-175-01** independent non-author security disposition recorded (OPEN until a
  qualified non-author reviewer records them — the author/CI/Codex cannot).
- **Readiness checklist** (`P4_6_SYNTHETIC_PILOT_READINESS_CHECKLIST.md`) fully passed with
  evidence.

Until all are recorded: **HOLD — the synthetic pilot is NOT authorized.**

---

*No approval, waiver, or closure is issued by this charter. It is a proposal to the designated
LumenAI Release Authority and the relevant review authorities. The AI workflow that drafted it does
not and cannot authorize the pilot or approve any security/scientific gate.*
