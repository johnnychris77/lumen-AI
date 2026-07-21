# LPR-DIR-027 — Clinical Workflow Readiness (Workstream 4)

Verification of clinical-workflow prerequisites for a controlled SPD (sterile processing)
pilot. Software features that *support* a workflow are distinguished from the real-world
engagement a pilot requires.

| Criterion | Software support in IRC-1 | Real-world status | Certification |
|---|---|---|---|
| **Pilot site selected** | n/a | ❌ **No site** identified or contracted | **NOT MET** — Pilot Blocking |
| **Clinical sponsor** | n/a | ❌ **No named clinical sponsor** | **NOT MET** — Pilot Blocking |
| **SPD workflow** | Inspection state machine, decision-support UI, supervisor review (`app/routes/inspections.py`, decision engine) present | ⚠️ Software workflow exists; **not validated with real SPD staff at a site** | **NOT MET** (software present, unproven) |
| **Equipment qualification** | Image ingestion + metadata validation present | ❌ **No imaging equipment qualified** for the site | **NOT MET** — Pilot Blocking |
| **Baseline availability** | Baseline image library + compatibility/resolution services present (`baseline_image_library_service.py`); legacy baselines marked `IMAGE_EVIDENCE_MISSING` | ⚠️ Framework present; **no site-specific qualified baselines loaded**; **zero real facility images** | **NOT MET** |
| **Digital Twins** | `digital_twin_engine.py` + twin timeline present | ⚠️ Engine present; **no real-instrument twins populated from a site** | **NOT MET** |
| **Operator training** | n/a | ❌ **No operators trained** | **NOT MET** — Pilot Blocking |
| **Competency** | n/a | ❌ **No competency assessment** completed | **NOT MET** — Pilot Blocking |
| **Escalation procedure** | `human_review_required: True` on every result; supervisor review + safety-fail-closed states in code | ⚠️ Software escalation exists; **no site-level clinical escalation/on-call defined** | **NOT MET** (software present, no site procedure) |

## Determination

**Clinical workflow readiness is NOT MET.** The software *supports* an SPD advisory
workflow (inspection flow, supervisor review, baseline/twin frameworks, mandatory human
review), but **every real-world clinical prerequisite is absent**: no site, no sponsor,
no qualified equipment, no site baselines, no populated twins, no trained/assessed
operators, and no site escalation procedure. These cannot be satisfied from a repository.
This workstream blocks pilot entry.

*No clinical claims are made. No causation is asserted. AI outputs remain advisory with
mandatory human review.*
