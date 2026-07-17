# Clinical Pilot Program — Phase 1, Sprint 1: Readiness Assessment

**This is the honest center of the sprint.** It states, per mission
section, what is genuinely ready, what has been prepared as material for
the pilot, and what cannot exist until a real site and managed
infrastructure are engaged. Nothing below claims an event that has not
occurred: **no pilot site has been selected, no clinical users exist, no
managed environment is deployed, and no real facility image has ever
been processed.**

## Section-by-section status

| Mission section | Status | Reality |
|---|---|---|
| 1. Pilot site selection | REQUIRES REAL ENGAGEMENT | No hospital, sponsor, or named contact exists. `PILOT_SITE_SELECTION.md` provides the selection criteria and the record to be filled by real people — it is deliberately unfilled. |
| 2. Infrastructure readiness | SOFTWARE READY / DEPLOYMENT PENDING | Foundation Sprint 1 verified PostgreSQL end-to-end, built governed object storage, executed backup/restore/DR, and shipped monitoring with truthful alerting (`docs/foundation/`). Provisioning managed PostgreSQL, durable storage, TLS, and an alert destination is a real-infrastructure action documented in `PILOT_SITE_GUIDE.md` — it cannot be performed from this repository. |
| 3. Equipment readiness | CHECKLIST PREPARED | No physical borescope, workstation, or network exists here. `PILOT_SITE_GUIDE.md` §Equipment carries the validation checklist to execute on site. |
| 4. Clinical workflow validation | WORKFLOW EXISTS IN SOFTWARE; OBSERVATION PENDING | Every step of the mission's flow (scan → capture → upload → baseline retrieval → inference → advisory display → technician decision → supervisor review → Ground Truth → Digital Twin) is implemented and regression-tested. Real-workflow observation and timing require the site; capture forms are in `PILOT_OBSERVATION_FORMS.md`. |
| 5. Human factors assessment | FORMS PREPARED | No users yet; assessment instruments prepared (`PILOT_OBSERVATION_FORMS.md`, building on `docs/advisory-pilot/USER_FEEDBACK_PLAN.md`). |
| 6. AI performance observation | INSTRUMENTED; OBSERVE-ONLY AFFIRMED | Inference logging, confidence, unknown-finding routing, baseline-retrieval outcomes and error states are all recorded by existing services. No performance claims are made — and none could be: the only registered model is `Experimental`, trained solely on declared synthetic data. |
| 7. Safety monitoring | MECHANISMS READY | Safety events, contradictions, image-identity mismatch, missing-baseline and integrity failures are detected and audited by existing services; the pilot record forms are prepared. |
| 8. Clinical evidence collection | PIPELINE READY | Canvas ingestion → LCID → annotation → double-blind review → Ground Truth → dataset growth is implemented and tested; it has only ever carried synthetic/test data. |
| 9. Governance verification | VERIFIED | See `GOVERNANCE_VERIFICATION.md` — every item maps to enforcing code and passing tests, re-verified this sprint on SQLite and PostgreSQL. |
| 10. Success metrics | DEFINED | `PILOT_PROTOCOL.md` §Metrics, with measurement sources and the `insufficient_data` rule. |
| 11. Exit criteria | DEFINED | `PILOT_PROTOCOL.md` §Exit — evaluated only against real pilot evidence, never against templates. |
| 12. Documentation | DELIVERED (with 3 explicit templates) | All ten artifacts exist. `WORKFLOW_TIMING_REPORT.md`, `PILOT_LESSONS_LEARNED.md`, and `PILOT_COMPLETION_REPORT.md` are **templates with prominent status banners** — filling them before a pilot runs would be fabricated evidence. |

## Definition of Done — honest verdict

| DoD item | Met? |
|---|---|
| Pilot environment deployed | **NO** — requires managed infrastructure (user/organization action; runbook ready) |
| Clinical users trained | **NO** — no users exist; training manual and curriculum ready |
| First real images successfully processed | **NO** — zero real facility images have ever entered the platform |
| Advisory AI functioning | SOFTWARE YES — advisory display, human-decision capture, and safe unavailable states are tested; the model itself is Experimental/synthetic and is presented accordingly |
| Ground Truth workflow operational | SOFTWARE YES — implemented and tested; never yet exercised with real clinical images |
| Digital Twin updated | SOFTWARE YES — same qualification |
| Governance verified | **YES** — `GOVERNANCE_VERIFICATION.md` |
| Pilot evidence collected | **NO** — no pilot has run; collection instruments ready |

**The sprint's completion statement cannot be issued as written.** The
accurate statement is:

> LumenAI has completed the software-side and documentation readiness
> activities for a controlled clinical pilot. Beginning supervised
> real-world evaluation additionally requires: a signed pilot site with
> named clinical roles, a provisioned managed environment (PostgreSQL,
> durable object storage, TLS, alert destination), validated on-site
> equipment, and trained users — all real-world actions this repository
> can prepare for but cannot perform.

This preserves the program's standing constraints: LumenAI is advisory
only; no clinical decision is made solely by AI; no performance claims;
no claim of FDA clearance or regulatory approval; and the standing
release decisions (`docs/general-availability/`,
`docs/controlled-production/`) are unchanged.

## The critical safety disclosure for any Phase-1 pilot

The only model ever trained in this program is registered
`candidate_stage="Experimental"` and was trained exclusively on declared
synthetic images. The promotion ladder (`MIN_STAGE_FOR_LIVE_SERVING`,
`candidate_promotion.py`) and the result contract's disclosure fields
enforce how it may be presented. A Phase-1 pilot therefore runs the AI
channel in **observe-only** terms (mission Section 6): outputs are
recorded and disclosed as experimental, technicians retain full manual
workflow, and no workflow step is gated on AI output. The risk
assessment (`PILOT_RISK_ASSESSMENT.md`) treats this as the pilot's
first-order risk and control.
