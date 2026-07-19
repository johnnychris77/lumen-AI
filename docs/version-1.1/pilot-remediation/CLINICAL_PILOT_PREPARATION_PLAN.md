# LPR-DIR-028 — Clinical Pilot Preparation Plan (Workstream 3)

Preparation plan for the clinical/SPD dimensions of a controlled pilot. **Plan only.** Every
item below is currently NOT MET (LPR-DIR-027). Several depend on external parties and cannot
be scheduled from engineering.

| Item | Current state | Preparation work | Owner | Objective evidence to close |
|---|---|---|---|---|
| **Pilot hospital** | none | Identify + contract a site; scope + protocol | CMTO / Business Dev | Signed site agreement + scope |
| **Clinical sponsor** | none | Named sponsor accountable for the pilot at the site | Clinical Operations Director | Sponsor appointment letter |
| **SPD workflow** | software supports it; unvalidated on-site | Map site's real SPD flow to the app; identify gaps; site SOP | Clinical Operations Director | Site-validated workflow map + SOP sign-off |
| **Equipment qualification** | none | Qualify imaging device(s) (IQ/OQ/PQ analog); capture settings | CMTO + site biomed | Equipment qualification record |
| **Image acquisition workflow** | ingestion + metadata validation in code; zero real images | Define capture SOP (lighting, angle, device); privacy (no PHI in image/metadata) | Clinical Operations Director | Capture SOP + sample acquisitions passing validation |
| **Baseline creation** | baseline library + compatibility services; no site baselines | Acquire + review + activate site-specific qualified baselines | Clinical Operations Director + Quality | Activated baseline set with review sign-off |
| **Digital Twin initialization** | `digital_twin_engine` present; twins empty | Initialize twins for in-scope instruments from qualified baselines | AI Governance Director + Clinical Ops | Populated twins linked to instruments |
| **Operator competency** | none | Train operators; competency assessment; record | Clinical Operations Director | Competency sign-offs per operator |
| **Escalation procedures** | `human_review_required: True` + supervisor review in code | Define site clinical escalation + on-call for safety events; align to fail-closed states | Clinical Operations Director + CMTO | Site escalation SOP acknowledged |

## Data governance & privacy tie-in
- Real images require a signed data agreement + confirmation of **no PHI in image content or
  metadata** (CLAUDE.md constraint) before acquisition.
- AI outputs remain **advisory only** with **mandatory human review**; no diagnostic or
  causation claims; contamination-safety remains fail-closed.

## Honest caveat
This is preparation planning. **No clinical prerequisite is satisfied by this document.** The
pilot hospital, sponsor, equipment qualification, real baselines, and operator competency are
real-world artifacts that must be produced and countersigned; until then GATE-RW remains OPEN
and no pilot may be authorized.
